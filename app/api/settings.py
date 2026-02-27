from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.setting import Setting
from app.models.user import User
from app.utils.decorators import admin_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/', methods=['GET'], strict_slashes=False)
def get_settings():
    """Get all public settings (e.g., global contact number)"""
    try:
        settings = Setting.query.all()
        # Return as key-value pairs
        settings_dict = {s.key: s.value for s in settings}
        return jsonify({'settings': settings_dict}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch settings', 'error': str(e)}), 500

@settings_bp.route('/', methods=['PUT'], strict_slashes=False)
@jwt_required()
@admin_required
def update_settings():
    """Update settings (Super Admin only for certain settings, but Admin allowed generally)"""
    try:
        # Require Super Admin to change the global contact number
        current_user = User.query.get(int(get_jwt_identity()))
        if not current_user or not current_user.is_super_admin():
            return jsonify({'message': 'Only Super Admins can update global settings'}), 403

        data = request.get_json()
        
        for key, value in data.items():
            setting = Setting.query.filter_by(key=key).first()
            if not setting:
                setting = Setting(key=key, value=str(value))
                db.session.add(setting)
            else:
                setting.value = str(value)
                
        db.session.commit()
        
        # Return updated settings
        settings = Setting.query.all()
        settings_dict = {s.key: s.value for s in settings}
        
        return jsonify({
            'message': 'Settings updated successfully',
            'settings': settings_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update settings', 'error': str(e)}), 500
