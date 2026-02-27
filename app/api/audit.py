from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.decorators import admin_required

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('/', methods=['GET'], strict_slashes=False)
@jwt_required()
@admin_required
def get_audit_logs():
    """Admin endpoint to fetch audit logs with optional filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action_filter = request.args.get('action')
        
        query = AuditLog.query
        
        if action_filter and action_filter != 'all':
            query = query.filter_by(action=action_filter)
            
        logs = query.order_by(AuditLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        results = []
        for log in logs.items:
            log_dict = log.to_dict()
            # Enrich with user name
            if log.user_id:
                user = User.query.get(log.user_id)
                log_dict['user_name'] = user.name if user else 'Unknown'
                log_dict['user_email'] = user.email if user else None
            else:
                log_dict['user_name'] = 'System'
                log_dict['user_email'] = None
            results.append(log_dict)
        
        return jsonify({
            'logs': results,
            'total': logs.total,
            'page': logs.page,
            'pages': logs.pages
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch audit logs', 'error': str(e)}), 500
