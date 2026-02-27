from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.payment import Payment
from app.models.property import Property
from app.models.user import User
from app.services.mpesa import MpesaService
from app.utils.sms import send_otp_sms
from app.utils.email import send_payment_notification_email
from app.models.setting import Setting
import os

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/initiate', methods=['POST'])
@jwt_required()
def initiate_payment():
    """Initiate M-Pesa STK Push payment"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        amount = data.get('amount')
        phone_number = data.get('phone_number')
        payment_type = data.get('payment_type')
        property_id = data.get('property_id')
        description = data.get('description', '')
        
        # Validation
        if not amount or amount <= 0:
            return jsonify({'message': 'Valid amount is required'}), 400
        
        if not phone_number:
            return jsonify({'message': 'Phone number is required'}), 400
        
        if not payment_type:
            return jsonify({'message': 'Payment type is required'}), 400
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            amount=amount,
            payment_type=payment_type,
            property_id=property_id,
            phone_number=phone_number,
            description=description,
            status='pending'
        )
        
        db.session.add(payment)
        db.session.commit()
        
        # Initiate M-Pesa STK Push
        mpesa = MpesaService()
        result = mpesa.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=f'VS{payment.id}',
            transaction_desc=description or f'Payment for {payment_type}'
        )
        
        if result.get('success'):
            payment.mpesa_checkout_request_id = result.get('checkout_request_id')
            payment.process()
            db.session.commit()
            
            return jsonify({
                'message': 'Payment initiated. Please check your phone to complete the transaction.',
                'payment': payment.to_dict(),
                'checkout_request_id': result.get('checkout_request_id')
            }), 200
        else:
            payment.fail(result.get('error', 'Failed to initiate payment'))
            db.session.commit()
            
            return jsonify({
                'message': 'Failed to initiate payment',
                'error': result.get('error')
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Payment initiation failed', 'error': str(e)}), 500


@payments_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa callback"""
    try:
        data = request.get_json()
        
        # Extract callback data
        callback_data = data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = callback_data.get('CheckoutRequestID')
        result_code = callback_data.get('ResultCode')
        result_desc = callback_data.get('ResultDesc')
        
        # Find payment by checkout request ID
        payment = Payment.query.filter_by(mpesa_checkout_request_id=checkout_request_id).first()
        
        if not payment:
            return jsonify({'message': 'Payment not found'}), 404
        
        if result_code == 0:
            # Payment successful
            callback_metadata = callback_data.get('CallbackMetadata', {}).get('Item', [])
            receipt_number = None
            
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    receipt_number = item.get('Value')
                    break
            
            payment.complete(receipt_number)
            
            # Link property for context
            property_title = "N/A"
            if payment.property_id:
                prop = Property.query.get(payment.property_id)
                if prop:
                    property_title = prop.title

            # Notify Admin
            admin_email_setting = Setting.query.filter_by(key='primary_admin_email').first()
            if admin_email_setting and admin_email_setting.value:
                send_payment_notification_email(admin_email_setting.value, {
                    'payment_type': payment.payment_type.replace('_', ' ').capitalize(),
                    'amount': str(payment.amount),
                    'tenant_name': payment.user.name if payment.user else 'Unknown',
                    'phone': payment.phone_number,
                    'property_title': property_title,
                    'receipt_number': receipt_number
                })

            # Notify Tenant via SMS
            sms_message = f"Payment of KES {payment.amount} for {payment.payment_type.replace('_', ' ')} received successfully. Ref: {receipt_number}. Thank you!"
            send_otp_sms(payment.phone_number, sms_message)

            db.session.commit()
            
            return jsonify({'message': 'Payment completed successfully'}), 200
        else:
            # Payment failed
            payment.fail(result_desc)
            db.session.commit()
            
            return jsonify({'message': 'Payment failed', 'error': result_desc}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Callback processing failed', 'error': str(e)}), 500


@payments_bp.route('/status/<int:payment_id>', methods=['GET'])
@jwt_required()
def check_payment_status(payment_id):
    """Check payment status"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        payment = Payment.query.get_or_404(payment_id)
        
        # Check permissions
        if not user.is_admin() and payment.user_id != user_id:
            return jsonify({'message': 'Permission denied'}), 403
        
        return jsonify({'payment': payment.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to check payment status', 'error': str(e)}), 500


@payments_bp.route('/my-payments', methods=['GET'])
@jwt_required()
def get_my_payments():
    """Get current user's payments"""
    try:
        user_id = get_jwt_identity()
        
        payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
        
        return jsonify({
            'payments': [p.to_dict() for p in payments]
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch payments', 'error': str(e)}), 500


@payments_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_payments():
    """Get all payments (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user.is_admin():
            return jsonify({'message': 'Permission denied'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', '').strip()
        
        query = Payment.query
        
        if status:
            query = query.filter_by(status=status)
        
        pagination = query.order_by(Payment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'payments': [p.to_dict(include_user=True) for p in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch payments', 'error': str(e)}), 500
