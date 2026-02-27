from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.utils.decorators import admin_required
from app.utils.sanitizers import sanitize_string

users_bp = Blueprint('users', __name__)


@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update the current user's profile information"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get_or_404(user_id)
        
        data = request.get_json()
        if 'name' in data and data['name'].strip():
            user.name = sanitize_string(data['name'].strip())
            
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update profile', 'error': str(e)}), 500


@users_bp.route('/', methods=['GET'], strict_slashes=False)
@jwt_required()
@admin_required
def get_users():
    """Get all users (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        role = request.args.get('role', '').strip()
        search = request.args.get('search', '').strip()
        
        query = User.query
        
        if role:
            query = query.filter_by(role=role)
        
        if search:
            query = query.filter(
                db.or_(
                    User.name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items
        
        return jsonify({
            'users': [u.to_dict() for u in users],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch users', 'error': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_user(user_id):
    """Get a single user by ID (admin only)"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify({'user': user.to_dict(include_sensitive=True)}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch user', 'error': str(e)}), 500


@users_bp.route('/<int:user_id>/role', methods=['PUT'])
@jwt_required()
@admin_required
def update_user_role(user_id):
    """Update a user's role (super_admin only ideally)"""
    try:
        current_admin = User.query.get(int(get_jwt_identity()))
        if not current_admin or not current_admin.is_super_admin():
            return jsonify({'message': 'Only Super Admins can change roles'}), 403
            
        user = User.query.get_or_404(user_id)
        if user.is_super_admin() and current_admin.id != user.id:
            return jsonify({'message': 'Cannot demote other Super Admins'}), 403

        data = request.get_json()
        if 'role' in data and data['role'] in ['super_admin', 'admin', 'landlord', 'tenant']:
            user.role = data['role']
            db.session.commit()
            return jsonify({'message': 'User role updated successfully', 'user': user.to_dict()}), 200
            
        return jsonify({'message': 'Invalid role provided'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update user role', 'error': str(e)}), 500


@users_bp.route('/<int:user_id>/status', methods=['PUT'])
@jwt_required()
@admin_required
def update_user_status(user_id):
    """Ban or unban a user by toggling is_active"""
    try:
        user = User.query.get_or_404(user_id)
        current_admin = User.query.get(get_jwt_identity())
        
        if user.is_super_admin() and current_admin.id != user.id:
            return jsonify({'message': 'Cannot ban a Super Admin'}), 403

        data = request.get_json()
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
            db.session.commit()
            return jsonify({'message': 'User status updated successfully', 'user': user.to_dict()}), 200
            
        return jsonify({'message': 'is_active flag missing'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update user status', 'error': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        current_user_id = int(get_jwt_identity())
        
        if user_id == current_user_id:
            return jsonify({'message': 'Cannot delete yourself'}), 400
        
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting super admins
        if user.is_super_admin():
            return jsonify({'message': 'Cannot delete super admin'}), 403
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete user', 'error': str(e)}), 500

@users_bp.route('/kyc/pending', methods=['GET'])
@jwt_required()
@admin_required
def get_pending_kyc():
    """Get all pending KYC verification requests (admin only)"""
    try:
        from app.models.document import Document
        pending_users = User.query.filter(User.verification_status == 'pending', User.role == 'landlord').all()
        results = []
        for user in pending_users:
            docs = Document.query.filter_by(user_id=user.id, status='pending').all()
            if docs:
                results.append({
                    'user': user.to_dict(include_sensitive=True),
                    'documents': [d.to_dict(include_file_url=True) for d in docs]
                })
                
        return jsonify({'requests': results}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch KYC requests', 'error': str(e)}), 500

@users_bp.route('/kyc/all', methods=['GET'])
@jwt_required()
@admin_required
def get_all_kyc():
    """Get all KYC verification requests (admin only)"""
    try:
        from app.models.document import Document
        # Only fetch landlords who have at least started KYC (status not pending, or have documents)
        kyc_users = User.query.filter(User.role == 'landlord', User.id_number.isnot(None)).all()
        results = []
        for user in kyc_users:
            docs = Document.query.filter_by(user_id=user.id).filter(Document.document_type.in_(['id_document', 'legal_document'])).all()
            if docs:
                results.append({
                    'user': user.to_dict(include_sensitive=True),
                    'documents': [d.to_dict(include_file_url=True) for d in docs]
                })
                
        return jsonify({'requests': results}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch all KYC data', 'error': str(e)}), 500


@users_bp.route('/kyc/<int:user_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_kyc(user_id):
    """Approve a KYC verification request (admin only)"""
    try:
        from app.models.document import Document
        admin_id = int(get_jwt_identity())
        user = User.query.get_or_404(user_id)
        
        docs = Document.query.filter_by(user_id=user.id, status='pending').all()
        if not docs:
            return jsonify({'message': 'No pending documents found for this user'}), 400
            
        for doc in docs:
            doc.verify(admin_user_id=admin_id, notes="Approved by Admin")
            
        user.verification_status = 'verified'
        user.is_landlord_verified = True
            
        db.session.commit()
        return jsonify({'message': 'KYC request approved successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to approve KYC', 'error': str(e)}), 500

@users_bp.route('/kyc/<int:user_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_kyc(user_id):
    """Reject a KYC verification request (admin only)"""
    try:
        from app.models.document import Document
        admin_id = int(get_jwt_identity())
        data = request.get_json() or {}
        reason = data.get('reason', 'Rejected by Admin')
        
        user = User.query.get_or_404(user_id)
        
        docs = Document.query.filter_by(user_id=user.id, status='pending').all()
        if not docs:
            return jsonify({'message': 'No pending documents found for this user'}), 400
            
        for doc in docs:
            doc.reject(admin_user_id=admin_id, notes=reason)
            
        user.verification_status = 'rejected'
        user.is_landlord_verified = False
            
        db.session.commit()
        return jsonify({'message': 'KYC request rejected'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to reject KYC', 'error': str(e)}), 500
