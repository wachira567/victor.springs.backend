from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.decorators import admin_required
from datetime import datetime

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('/', methods=['GET'], strict_slashes=False)
@jwt_required()
@admin_required
def get_audit_logs():
    """Admin endpoint to fetch audit logs with filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action_filter = request.args.get('action')
        resource_type_filter = request.args.get('resource_type')
        user_id_filter = request.args.get('user_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        query = AuditLog.query
        
        if action_filter and action_filter != 'all':
            query = query.filter(AuditLog.action == action_filter)
        if resource_type_filter and resource_type_filter != 'all':
            query = query.filter(AuditLog.resource_type == resource_type_filter)
        if user_id_filter:
            query = query.filter(AuditLog.user_id == user_id_filter)
        if date_from:
            try:
                dt_from = datetime.fromisoformat(date_from)
                query = query.filter(AuditLog.created_at >= dt_from)
            except ValueError:
                pass
        if date_to:
            try:
                dt_to = datetime.fromisoformat(date_to)
                query = query.filter(AuditLog.created_at <= dt_to)
            except ValueError:
                pass
            
        logs = query.order_by(AuditLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Collect unique user IDs to batch-fetch names
        user_ids = set(l.user_id for l in logs.items if l.user_id)
        users_map = {}
        if user_ids:
            users = User.query.filter(User.id.in_(user_ids)).all()
            users_map = {u.id: u for u in users}
        
        results = []
        for log in logs.items:
            log_dict = log.to_dict()
            user = users_map.get(log.user_id)
            log_dict['user_name'] = user.name if user else ('System' if not log.user_id else 'Unknown')
            log_dict['user_email'] = user.email if user else None
            results.append(log_dict)

        # Get distinct action types for filter dropdown
        distinct_actions = [r[0] for r in AuditLog.query.with_entities(AuditLog.action).distinct().all()]
        
        return jsonify({
            'logs': results,
            'total': logs.total,
            'page': logs.page,
            'pages': logs.pages,
            'distinct_actions': distinct_actions
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch audit logs', 'error': str(e)}), 500

@audit_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_audit_logs():
    """Endpoint for regular users to fetch their own activity/notifications"""
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = int(get_jwt_identity())
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # We only want to show relevant "notification-style" logs to the user
        # e.g. status changes, payment confirmations, etc.
        query = AuditLog.query.filter(AuditLog.user_id == user_id)
        
        logs = query.order_by(AuditLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'logs': [log.to_dict() for log in logs.items],
            'total': logs.total,
            'page': logs.page,
            'pages': logs.pages
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch your activity', 'error': str(e)}), 500
