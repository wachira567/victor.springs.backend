from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.visit import Visit
from app.models.property import Property
from app.models.user import User

visits_bp = Blueprint('visits', __name__)


@visits_bp.route('/', methods=['GET'])
@jwt_required()
def get_visits():
    """Get visits for the current user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.is_landlord():
            # Get visits for landlord's properties
            visits = Visit.query.join(Property).filter(Property.landlord_id == user_id).all()
        else:
            # Get tenant's visits
            visits = Visit.query.filter_by(tenant_id=user_id).all()
        
        return jsonify({
            'visits': [v.to_dict(include_property=True, include_tenant=user.is_landlord()) for v in visits]
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch visits', 'error': str(e)}), 500


@visits_bp.route('/', methods=['POST'])
@jwt_required()
def create_visit():
    """Schedule a new visit"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        property_id = data.get('property_id')
        visit_date = data.get('visit_date')
        visit_time = data.get('visit_time')
        notes = data.get('notes', '')
        
        # Validation
        if not property_id or not visit_date or not visit_time:
            return jsonify({'message': 'Property, date, and time are required'}), 400
        
        # Check if property exists
        property = Property.query.get(property_id)
        if not property:
            return jsonify({'message': 'Property not found'}), 404
        
        # Create visit
        visit = Visit(
            property_id=property_id,
            tenant_id=user_id,
            visit_date=visit_date,
            visit_time=visit_time,
            notes=notes,
            status='pending'
        )
        
        db.session.add(visit)
        
        # Increment property inquiry count
        property.increment_inquiries()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Visit scheduled successfully',
            'visit': visit.to_dict(include_property=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to schedule visit', 'error': str(e)}), 500


@visits_bp.route('/<int:visit_id>', methods=['GET'])
@jwt_required()
def get_visit(visit_id):
    """Get a single visit by ID"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        visit = Visit.query.get_or_404(visit_id)
        
        # Check permissions
        if not user.is_admin():
            if user.is_landlord():
                property = Property.query.get(visit.property_id)
                if property.landlord_id != user_id:
                    return jsonify({'message': 'Permission denied'}), 403
            elif visit.tenant_id != user_id:
                return jsonify({'message': 'Permission denied'}), 403
        
        return jsonify({
            'visit': visit.to_dict(include_property=True, include_tenant=True)
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch visit', 'error': str(e)}), 500


@visits_bp.route('/<int:visit_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_visit(visit_id):
    """Confirm a visit (landlord only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        visit = Visit.query.get_or_404(visit_id)
        
        # Check if user is the landlord
        property = Property.query.get(visit.property_id)
        if not user.is_admin() and property.landlord_id != user_id:
            return jsonify({'message': 'Permission denied'}), 403
        
        if visit.status != 'pending':
            return jsonify({'message': 'Visit cannot be confirmed'}), 400
        
        visit.confirm()
        db.session.commit()
        
        return jsonify({
            'message': 'Visit confirmed successfully',
            'visit': visit.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to confirm visit', 'error': str(e)}), 500


@visits_bp.route('/<int:visit_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_visit(visit_id):
    """Cancel a visit"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        visit = Visit.query.get_or_404(visit_id)
        
        # Check permissions
        if not user.is_admin():
            if user.is_landlord():
                property = Property.query.get(visit.property_id)
                if property.landlord_id != user_id:
                    return jsonify({'message': 'Permission denied'}), 403
            elif visit.tenant_id != user_id:
                return jsonify({'message': 'Permission denied'}), 403
        
        if visit.status in ['completed', 'cancelled']:
            return jsonify({'message': 'Visit cannot be cancelled'}), 400
        
        visit.cancel(user_id)
        db.session.commit()
        
        return jsonify({
            'message': 'Visit cancelled successfully',
            'visit': visit.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to cancel visit', 'error': str(e)}), 500


@visits_bp.route('/<int:visit_id>/complete', methods=['POST'])
@jwt_required()
def complete_visit(visit_id):
    """Mark visit as completed (landlord only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        visit = Visit.query.get_or_404(visit_id)
        
        # Check if user is the landlord
        property = Property.query.get(visit.property_id)
        if not user.is_admin() and property.landlord_id != user_id:
            return jsonify({'message': 'Permission denied'}), 403
        
        if visit.status != 'confirmed':
            return jsonify({'message': 'Visit must be confirmed before completion'}), 400
        
        visit.complete()
        db.session.commit()
        
        return jsonify({
            'message': 'Visit marked as completed',
            'visit': visit.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to complete visit', 'error': str(e)}), 500


@visits_bp.route('/<int:visit_id>/notes', methods=['PUT'])
@jwt_required()
def update_visit_notes(visit_id):
    """Update landlord notes for a visit"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        visit = Visit.query.get_or_404(visit_id)
        data = request.get_json()
        
        # Check if user is the landlord
        property = Property.query.get(visit.property_id)
        if not user.is_admin() and property.landlord_id != user_id:
            return jsonify({'message': 'Permission denied'}), 403
        
        visit.landlord_notes = data.get('notes', '')
        db.session.commit()
        
        return jsonify({
            'message': 'Notes updated successfully',
            'visit': visit.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update notes', 'error': str(e)}), 500
