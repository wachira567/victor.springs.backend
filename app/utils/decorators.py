from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.user import User

def admin_required(fn):
    """Decorator to require admin or super_admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if not user.is_admin():
            return jsonify({'message': 'Admin access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper

def super_admin_required(fn):
    """Decorator to require super_admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if not user.is_super_admin():
            return jsonify({'message': 'Super admin access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper

def landlord_required(fn):
    """Decorator to require landlord or admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if not (user.is_landlord() or user.is_admin()):
            return jsonify({'message': 'Landlord access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper

def tenant_required(fn):
    """Decorator to require tenant or admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if not (user.is_tenant() or user.is_admin()):
            return jsonify({'message': 'Tenant access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper
