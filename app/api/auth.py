import os
import bleach
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from itsdangerous import URLSafeTimedSerializer
from app import db
from app.models.user import User
from app.models.identity import Identity
from app.utils.validators import validate_email, validate_phone, validate_password
from app.utils.sanitizers import sanitize_string
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.sms import generate_otp, generate_otp_token, verify_otp_token, send_otp_sms
from app.utils.signature import generate_signature_request
from app.models.document import Document
from werkzeug.utils import secure_filename
import uuid

auth_bp = Blueprint('auth', __name__)

def get_token_serializer():
    """Return URLSafeTimedSerializer using the app's config secret."""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Handle Google Sign-In"""
    try:
        data = request.get_json()
        token = data.get('credential')
        
        if not token:
            return jsonify({'message': 'No Google token provided'}), 400
            
        # Verify the Google token
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        try:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
        except ValueError as e:
            return jsonify({'message': 'Invalid Google token', 'error': str(e)}), 401
            
        email = idinfo.get('email')
        name = idinfo.get('name')
        google_id = idinfo.get('sub')
        picture = idinfo.get('picture')
        
        if not email:
            return jsonify({'message': 'Email not provided by Google'}), 400
            
        # 1. Check if the user already exists (by email)  
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create a brand new user
            user = User(
                email=email,
                name=name,
                phone='Not Provided', # Google doesn't easily provide phone number, set default
                role=data.get('role', 'tenant'),  # Extract role passed from frontend, default tenant
                is_verified=True, 
                email_verified_at=db.func.now(),
                avatar_url=picture
            )
            # No password is set!
            db.session.add(user)
            db.session.flush() # Get user ID
            
        # 2. Check if the Identity link exists
        identity = Identity.query.filter_by(user_id=user.id, provider='google').first()
        
        if not identity:
            # Create the link (either for the new user or old local user)
            new_identity = Identity(
                user_id=user.id,
                provider='google',
                provider_id=google_id
            )
            db.session.add(new_identity)
            
        db.session.commit()
        
        # 3. Log them in!
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Google Login successful',
            'token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Google Authentication failed', 'error': str(e)}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Sanitize inputs
        email = sanitize_string(data.get('email', '')).lower().strip()
        password = data.get('password', '')
        name = sanitize_string(data.get('name', '')).strip()
        phone = sanitize_string(data.get('phone', '')).strip()
        role = data.get('role', 'tenant')
        
        # Validation
        if not email or not password or not name or not phone:
            return jsonify({'message': 'All fields are required'}), 400
        
        if not validate_email(email):
            return jsonify({'message': 'Invalid email format'}), 400
        
        if not validate_phone(phone):
            return jsonify({'message': 'Invalid phone number format'}), 400
        
        if not validate_password(password):
            return jsonify({'message': 'Password must be at least 8 characters long'}), 400
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already registered'}), 409
        
        # Check if phone exists
        if User.query.filter_by(phone=phone).first():
            return jsonify({'message': 'Phone number already registered'}), 409
        
        # Validate role
        valid_roles = ['tenant', 'landlord']
        if role not in valid_roles:
            role = 'tenant'
        
        # Create user
        user = User(
            email=email,
            name=name,
            phone=phone,
            role=role,
            is_verified=False  # Requires email verification
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Dispatch magic link
        serializer = get_token_serializer()
        token = serializer.dumps(user.email, salt='email-verification')
        
        send_verification_email(user.email, token)
        
        return jsonify({
            'message': 'Registration successful. Please check your email to verify your account.',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        email = sanitize_string(data.get('email', '')).lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'message': 'Email and password are required'}), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'message': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'message': 'Account is deactivated'}), 403
            
        if not user.is_verified:
            return jsonify({'message': 'Email address not verified. Please check your inbox for the verification link.'}), 403
        
        # Update last login
        from datetime import datetime
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        
        # Generate token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Login successful',
            'token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Login failed', 'error': str(e)}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user details"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get user', 'error': str(e)}), 500


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user():
    """Update current user details"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'name' in data:
            user.name = sanitize_string(data['name']).strip()
        if 'phone' in data:
            phone = sanitize_string(data['phone']).strip()
            if validate_phone(phone):
                user.phone = phone
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Update failed', 'error': str(e)}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'message': 'Current and new password are required'}), 400
        
        if not user.check_password(current_password):
            return jsonify({'message': 'Current password is incorrect'}), 401
        
        if not validate_password(new_password):
            return jsonify({'message': 'New password must be at least 8 characters'}), 400
        
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Password change failed', 'error': str(e)}), 500

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify email via magic link token."""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'message': 'Missing verification token'}), 400
            
        serializer = get_token_serializer()
        try:
            # Token expires after 24 hours
            email = serializer.loads(token, salt='email-verification', max_age=86400)
        except Exception:
            return jsonify({'message': 'The verification link is invalid or has expired.'}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        if user.is_verified:
            return jsonify({'message': 'Email is already verified. You can login.'}), 200
            
        user.is_verified = True
        user.email_verified_at = db.func.now()
        db.session.commit()
        
        # Auto login the user upon verification success
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Email verified successfully.',
            'token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Verification failed', 'error': str(e)}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Generate a password reset token and send magic link."""
    try:
        data = request.get_json()
        email = sanitize_string(data.get('email', '')).lower().strip()
        
        if not email:
            return jsonify({'message': 'Email is required'}), 400
            
        user = User.query.filter_by(email=email).first()
        if user:
            # We don't want to confirm to malicious actors if an email exists or not
            # If the user exists, we send the email asynchronously. 
            serializer = get_token_serializer()
            token = serializer.dumps(user.email, salt='password-reset')
            send_password_reset_email(user.email, token)
            
        return jsonify({
            'message': 'If an account matches that email address, a password reset link has been sent.'
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to process password reset request.'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Consume reset token and update password."""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('password')
        
        if not token or not new_password:
            return jsonify({'message': 'Missing token or new password'}), 400
            
        if not validate_password(new_password):
            return jsonify({'message': 'Password must be at least 8 characters long'}), 400
            
        serializer = get_token_serializer()
        try:
            # Token expires after 1 hour (3600 seconds)
            email = serializer.loads(token, salt='password-reset', max_age=3600)
        except Exception:
            return jsonify({'message': 'The password reset link is invalid or has expired.'}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        user.set_password(new_password)
        
        # Auto-verify email just in case they were pending
        if not user.is_verified:
            user.is_verified = True
            user.email_verified_at = db.func.now()
            
        db.session.commit()
        
        return jsonify({'message': 'Password has been successfully reset.'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Something went wrong resetting the password.'}), 500

# Constants for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth_bp.route('/kyc/send-otp', methods=['POST'])
@jwt_required()
def send_kyc_otp():
    """Request an OTP for KYC phone verification."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_landlord():
            return jsonify({'message': 'Only landlords can request KYC OTPs.'}), 403
            
        data = request.get_json()
        phone = data.get('phone', '').strip()
        
        if not phone or not validate_phone(phone):
            return jsonify({'message': 'Valid phone number required.'}), 400
            
        otp = generate_otp()
        success, info = send_otp_sms(phone, otp)
        
        # We always return the token so the frontend flow can proceed,
        # even if trial Twilio block prevents the SMS from arriving (dev fallback).
        token = generate_otp_token(phone, otp)
        
        return jsonify({
            'message': 'OTP sent successfully (Check console if trial account).' if success else 'SMS skipped. See console.',
            'otp_token': token
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to send OTP', 'error': str(e)}), 500

@auth_bp.route('/kyc/submit', methods=['POST'])
@jwt_required()
def submit_kyc():
    """Submit Landlord KYC verification details and ID document."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        if not user.is_landlord():
            return jsonify({'message': 'Only landlords can submit KYC verification.'}), 403
            
        if user.verification_status == 'verified':
            return jsonify({'message': 'You are already verified.'}), 400
            
        # Parse text fields
        first_name = request.form.get('first_name', '').strip()
        middle_name = request.form.get('middle_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        id_number = request.form.get('id_number', '').strip()
        phone = request.form.get('phone', '').strip()
        digital_consent = request.form.get('digital_consent', 'false').lower() == 'true'
        
        if not first_name or not last_name or not id_number or not phone:
            return jsonify({'message': 'First name, last name, ID number, and phone are required.'}), 400
            
        if not validate_phone(phone):
            return jsonify({'message': 'Invalid phone number format.'}), 400
            
        if not digital_consent:
            return jsonify({'message': 'You must agree to the digital consent terms.'}), 400
            
        # Verify OTP
        otp = request.form.get('otp', '').strip()
        otp_token = request.form.get('otp_token', '').strip()
        
        if not otp or not otp_token:
            return jsonify({'message': 'Phone verification OTP is required.'}), 400
            
        if not verify_otp_token(otp_token, phone, otp):
            return jsonify({'message': 'Invalid or expired OTP code.'}), 400
            
        full_name = f"{first_name} {middle_name} {last_name}".replace('  ', ' ')
        user.name = full_name
        user.id_number = id_number
        user.phone = phone
        user.verification_status = 'pending'
            
        import cloudinary.uploader
        
        # 1. Validate and prep ID Documents
        if 'id_document_front' not in request.files or 'id_document_back' not in request.files:
            return jsonify({'message': 'Both front and back ID documents are required.'}), 400
            
        id_front = request.files['id_document_front']
        id_back = request.files['id_document_back']
        
        if id_front.filename == '' or not allowed_file(id_front.filename):
            return jsonify({'message': 'No selected Front ID file or invalid format.'}), 400
        if id_back.filename == '' or not allowed_file(id_back.filename):
            return jsonify({'message': 'No selected Back ID file or invalid format.'}), 400
            
        id_front_data = id_front.read()
        id_back_data = id_back.read()
        
        if len(id_front_data) > MAX_FILE_SIZE or len(id_back_data) > MAX_FILE_SIZE:
            return jsonify({'message': 'ID Files exceed maximum 5MB size limit.'}), 400
            
        id_front.seek(0)
        id_back.seek(0)
        
        # 2. Upload ID Documents to Cloudinary
        try:
            front_upload = cloudinary.uploader.upload(
                id_front, folder="victorsprings/kyc_documents", resource_type="auto"
            )
            back_upload = cloudinary.uploader.upload(
                id_back, folder="victorsprings/kyc_documents", resource_type="auto"
            )
            id_front_url = front_upload.get("secure_url")
            id_back_url = back_upload.get("secure_url")
        except Exception as e:
            return jsonify({'message': 'Failed to upload ID documents to cloud storage.', 'error': str(e)}), 500
            
        # Create Document logs for ID Front and Back
        doc_front = Document(
            user_id=user.id,
            name=f"National ID/Passport (Front) - {user.email}",
            document_type='id_document',
            file_url=id_front_url,
            file_size=len(id_front_data),
            mime_type=id_front.content_type,
            status='pending',
            is_accessible=True
        )
        doc_back = Document(
            user_id=user.id,
            name=f"National ID/Passport (Back) - {user.email}",
            document_type='id_document',
            file_url=id_back_url,
            file_size=len(id_back_data),
            mime_type=id_back.content_type,
            status='pending',
            is_accessible=True
        )
        db.session.add(doc_front)
        db.session.add(doc_back)
        
        # 4. Generate Legal Clickwrap Consent Document Log
        try:
            from datetime import datetime
            import io
            
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            user_agent = request.headers.get('User-Agent', 'Unknown Device')
            
            consent_text = f"""
LANDLORD REPRESENTATION & CONSENT AGREEMENT
-----------------------------------------
Name: {full_name}
ID Number: {id_number}
Phone: {phone}
Email: {user.email}
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Consent Method: Verified Digital Clickwrap (OTP Verified Phone Session)

--- FORENSIC AUDIT TRAIL ---
IP Address: {ip_address}
Device Fingerprint: {user_agent}
----------------------------

Terms Consented To:
1. Representation of Ownership or Authority
2. Accuracy of Information
3. Anti-Fraud & Legal Liability
4. Data Processing Consent

The user has explicitly checked "I Consent" to these terms under penalty of perjury.
"""
            consent_file_data = consent_text.encode('utf-8')
            consent_file = io.BytesIO(consent_file_data)
            
            consent_upload_result = cloudinary.uploader.upload(
                consent_file,
                folder="victorsprings/kyc_documents",
                resource_type="raw",
                public_id=f"consent_{user.id}_{int(datetime.utcnow().timestamp())}.txt"
            )
            consent_file_url = consent_upload_result.get("secure_url")
        except Exception as e:
            return jsonify({'message': 'Failed to generate and upload digital consent log.', 'error': str(e)}), 500
            
        doc_consent = Document(
            user_id=user.id,
            name=f"Digital Consent Log - {user.email}",
            document_type='legal_document',
            file_url=consent_file_url,
            file_size=len(consent_file_data),
            mime_type='text/plain',
            status='pending',
            is_accessible=True
        )
        db.session.add(doc_consent)
            
        # Update User attributes
        user.id_document_url = f"{id_front_url},{id_back_url}"
        
        db.session.commit()
        
        msg = 'Verification request submitted. Our team will review it shortly.'
        
        return jsonify({
            'message': msg
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal Server Error', 'error': str(e)}), 500
