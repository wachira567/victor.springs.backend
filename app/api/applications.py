from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.tenant_application import TenantApplication
from app.models.property import Property
from app.models.user import User
from app.models.payment import Payment
from app.services.cloudinary_service import CloudinaryService
from app.utils.decorators import admin_required
from datetime import datetime

applications_bp = Blueprint('applications', __name__)

@applications_bp.route('/', methods=['POST'], strict_slashes=False)
@jwt_required()
def submit_application():
    """Submit a tenant application (with signed document and IDs)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        # In a real system, verify OTP here or assume verified by middleware/flow
        if request.form.get('digital_consent') != 'true':
            return jsonify({'message': 'Legal digital consent is required'}), 400
            
        property_id = request.form.get('property_id')
        property = Property.query.get_or_404(property_id)
        
        # Verify Payment if required
        if property.tenant_agreement_fee and property.tenant_agreement_fee > 0:
            payment_id = request.form.get('payment_id')
            if not payment_id:
                return jsonify({'message': 'Payment reference is required for this property'}), 400
            payment = Payment.query.get(payment_id)
            if not payment or payment.status != 'completed' or payment.property_id != property.id or payment.user_id != user.id:
                return jsonify({'message': 'Valid completed payment not found'}), 400
        else:
            payment_id = None
            
        # File uploads
        cloudinary = CloudinaryService()
        id_front = request.files.get('id_document_front')
        id_back = request.files.get('id_document_back')
        signed_agreement = request.files.get('signed_agreement')
        
        if not all([id_front, id_back, signed_agreement]):
            return jsonify({'message': 'ID (front and back) and Signed Agreement are required'}), 400
            
        front_url = cloudinary.upload_image(id_front, folder='tenant_kyc')
        back_url = cloudinary.upload_image(id_back, folder='tenant_kyc')
        agreement_url = cloudinary.upload_document(signed_agreement, folder='tenant_agreements')
        
        if not all([front_url, back_url, agreement_url]):
            return jsonify({'message': 'Failed to upload documents'}), 500
            
        app_record = TenantApplication(
            user_id=user.id,
            property_id=property.id,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            phone=request.form.get('phone'),
            id_number=request.form.get('id_number'),
            id_document_front=front_url,
            id_document_back=back_url,
            signed_agreement_url=agreement_url,
            digital_consent=True,
            digital_consent_ip=request.remote_addr,
            payment_id=payment_id
        )
        
        db.session.add(app_record)
        db.session.commit()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application': app_record.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to submit application', 'error': str(e)}), 500

@applications_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_applications():
    """Get all applications submitted by current user"""
    try:
        user_id = get_jwt_identity()
        apps = TenantApplication.query.filter_by(user_id=user_id).order_by(TenantApplication.created_at.desc()).all()
        return jsonify({'applications': [a.to_dict() for a in apps]}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch applications', 'error': str(e)}), 500

@applications_bp.route('/admin', methods=['GET'])
@jwt_required()
@admin_required
def get_admin_applications():
    """Admin endpoint to fetch ALL applications or filter by status"""
    try:
        status = request.args.get('status')
        query = TenantApplication.query
        
        if status and status != 'all':
            query = query.filter_by(status=status)
            
        apps = query.order_by(TenantApplication.created_at.desc()).all()
        return jsonify({'applications': [a.to_dict() for a in apps]}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch applications', 'error': str(e)}), 500

@applications_bp.route('/<int:app_id>/status', methods=['PUT'])
@jwt_required()
@admin_required
def update_application_status(app_id):
    """Admin endpoint to approve or reject an application"""
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        new_status = data.get('status')
        assigned_unit = data.get('assigned_unit')
        
        if new_status not in ['approved', 'rejected']:
            return jsonify({'message': 'Invalid status'}), 400
            
        app_record = TenantApplication.query.get_or_404(app_id)
        
        if new_status == 'approved':
            if not assigned_unit:
                return jsonify({'message': 'Assigned unit is required for approval'}), 400
            app_record.assigned_unit = assigned_unit
            # TODO: Decrease available unit count on Property model representation
        else:
            app_record.rejection_reason = data.get('reason', '')
            
        app_record.status = new_status
        app_record.reviewed_by = admin_id
        app_record.reviewed_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({
            'message': f'Application has been {new_status}',
            'application': app_record.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update application', 'error': str(e)}), 500
