from flask import Blueprint, request, jsonify
from app.utils.sms import generate_otp, send_otp_sms, generate_otp_token, verify_otp_token
from app.models.audit_log import AuditLog
import logging

otp_bp = Blueprint('otp', __name__)
logger = logging.getLogger(__name__)

@otp_bp.route('/send', methods=['POST'])
def send_otp():
    """Send OTP to a phone number and return a session token"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return jsonify({'message': 'Phone number is required'}), 400
            
        otp = generate_otp()
        success, info = send_otp_sms(phone, otp)
        
        # Generate a stateless token to be sent back to client
        # Client will send this back with the OTP code to verify
        verification_token = generate_otp_token(phone, otp)
        
        # Log the attempt
        AuditLog.log(
            action='otp_request',
            details={'phone': phone, 'success': success, 'info': info}
        )
        
        if success:
            return jsonify({
                'message': 'OTP sent successfully',
                'verification_token': verification_token
            }), 200
        else:
            # Still return token in dev fallback if success is false but info is present
            return jsonify({
                'message': 'Failed to send SMS via provider, but code is generated (check server logs)',
                'verification_token': verification_token,
                'error': info
            }), 200 # Return 200 to allow dev flow even if Twilio fails
            
    except Exception as e:
        logger.error(f"OTP send error: {str(e)}")
        return jsonify({'message': 'Error sending OTP', 'error': str(e)}), 500

@otp_bp.route('/verify', methods=['POST'])
def verify_otp():
    """Verify OTP using the token and code"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        otp = data.get('otp')
        token = data.get('token')
        
        if not all([phone, otp, token]):
            return jsonify({'message': 'Phone, OTP, and Token are required'}), 400
            
        is_valid = verify_otp_token(token, phone, otp)
        
        if is_valid:
            AuditLog.log(
                action='otp_verify_success',
                details={'phone': phone}
            )
            return jsonify({'message': 'OTP verified successfully', 'verified': True}), 200
        else:
            AuditLog.log(
                action='otp_verify_failed',
                details={'phone': phone}
            )
            return jsonify({'message': 'Invalid or expired OTP', 'verified': False}), 400
            
    except Exception as e:
        logger.error(f"OTP verify error: {str(e)}")
        return jsonify({'message': 'Error verifying OTP', 'error': str(e)}), 500
