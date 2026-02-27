from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.payment import Payment
from app.models.tenant_application import TenantApplication
from app import db
from sqlalchemy import func

admin_reports_bp = Blueprint('admin_reports', __name__)

@admin_reports_bp.route('/', methods=['GET'], strict_slashes=False)
@jwt_required()
def get_admin_reports():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if not user or user.role not in ['admin', 'super_admin']:
        return jsonify({'message': 'Unauthorized access'}), 403

    # Total Payments
    total_payments_result = db.session.query(func.sum(Payment.amount)).scalar()
    total_payments = float(total_payments_result) if total_payments_result else 0.0

    # Active Landlords
    active_landlords_count = User.query.filter_by(role='landlord', verification_status='verified').count()

    # Agreement Conversions
    approved_tenants_count = TenantApplication.query.filter_by(status='approved').count()

    # Recent Transactions
    recent_transactions_query = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
    recent_transactions = [
        {
            'id': p.id,
            'amount': float(p.amount),
            'status': p.status,
            'transaction_id': p.transaction_id,
            'created_at': p.created_at.isoformat() if p.created_at else None
        } for p in recent_transactions_query
    ]

    return jsonify({
        'totalPayments': total_payments,
        'activeLandlords': active_landlords_count,
        'agreementConversions': approved_tenants_count,
        'recentTransactions': recent_transactions,
        'monthlyGrowth': 0  # Placeholder, could calculate real growth if needed
    }), 200
