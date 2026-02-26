from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from app import db
from app.models.property import Property
from app.models.user import User
from app.utils.decorators import admin_required, landlord_required
from app.utils.sanitizers import sanitize_string

properties_bp = Blueprint('properties', __name__)


@properties_bp.route('/', methods=['GET'], strict_slashes=False)
def get_properties():
    """Get all properties with filters"""
    try:
        # Query parameters
        search = request.args.get('search', '').strip()
        city = request.args.get('city', '').strip()
        property_type = request.args.get('type', '').strip()
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        bedrooms = request.args.get('bedrooms', type=int)
        status = request.args.get('status', 'active')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Base query - only show active properties for public
        query = Property.query
        
        if status:
            query = query.filter_by(status=status)
        
        # Apply filters
        if search:
            search_filter = or_(
                Property.title.ilike(f'%{search}%'),
                Property.description.ilike(f'%{search}%'),
                Property.city.ilike(f'%{search}%'),
                Property.address.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        if city:
            query = query.filter(Property.city.ilike(f'%{city}%'))
        
        if property_type:
            query = query.filter_by(property_type=property_type)
        
        if min_price is not None:
            query = query.filter(Property.price >= min_price)
        
        if max_price is not None:
            query = query.filter(Property.price <= max_price)
        
        if bedrooms is not None:
            query = query.filter(Property.bedrooms >= bedrooms)
        
        # Order by newest first
        query = query.order_by(Property.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        properties = pagination.items
        
        return jsonify({
            'properties': [p.to_dict() for p in properties],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch properties', 'error': str(e)}), 500


@properties_bp.route('/<int:property_id>', methods=['GET'])
def get_property(property_id):
    """Get a single property by ID"""
    try:
        property = Property.query.get_or_404(property_id)
        
        # Increment view count
        property.increment_views()
        db.session.commit()
        
        return jsonify({'property': property.to_dict(include_landlord=True)}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch property', 'error': str(e)}), 500


@properties_bp.route('/', methods=['POST'], strict_slashes=False)
@jwt_required()
@landlord_required
def create_property():
    """Create a new property listing"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Sanitize inputs
        title = sanitize_string(data.get('title', '')).strip()
        description = sanitize_string(data.get('description', '')).strip()
        
        # Create property
        property = Property(
            title=title,
            description=description,
            property_type=data.get('propertyType') or data.get('property_type'),
            city=sanitize_string(data.get('city', '')).strip(),
            address=sanitize_string(data.get('address', '')).strip(),
            location_description=sanitize_string(data.get('locationDescription', '')).strip(),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            
            # Legacy flat fields (falling back to unit derived data if absent)
            price=data.get('price'),
            deposit=data.get('deposit'),
            bedrooms=data.get('bedrooms'),
            bathrooms=data.get('bathrooms'),
            area=data.get('area'),
            
            # New multi-unit / advanced fields
            units=data.get('units', []),
            tenant_agreement_fee=data.get('tenantAgreementFee') or data.get('tenant_agreement_fee'),
            
            amenities=data.get('amenities', []),
            images=data.get('images', []),
            available_from=data.get('available_from'),
            minimum_lease_months=data.get('minimum_lease_months', 12),
            landlord_id=user_id,
            status='pending_review',
            is_partner_property=True
        )
        
        db.session.add(property)
        db.session.commit()
        
        return jsonify({
            'message': 'Property submitted successfully. It will be reviewed shortly.',
            'property': property.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create property', 'error': str(e)}), 500


@properties_bp.route('/<int:property_id>', methods=['PUT'])
@jwt_required()
def update_property(property_id):
    """Update a property listing"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        property = Property.query.get_or_404(property_id)
        
        # Check permissions
        if not property.can_be_edited_by(user):
            return jsonify({'message': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            property.title = sanitize_string(data['title']).strip()
        if 'description' in data:
            property.description = sanitize_string(data['description']).strip()
        if 'price' in data:
            property.price = data['price']
        if 'amenities' in data:
            property.amenities = data['amenities']
        if 'images' in data:
            property.images = data['images']
        
        # Admin-only fields
        if user.is_admin():
            if 'admin_edited_title' in data:
                property.admin_edited_title = sanitize_string(data['admin_edited_title']).strip()
            if 'admin_edited_description' in data:
                property.admin_edited_description = sanitize_string(data['admin_edited_description']).strip()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Property updated successfully',
            'property': property.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update property', 'error': str(e)}), 500


@properties_bp.route('/<int:property_id>', methods=['DELETE'])
@jwt_required()
def delete_property(property_id):
    """Delete a property listing"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        property = Property.query.get_or_404(property_id)
        
        # Check permissions
        if not user.is_admin() and property.landlord_id != user_id:
            return jsonify({'message': 'Permission denied'}), 403
        
        db.session.delete(property)
        db.session.commit()
        
        return jsonify({'message': 'Property deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete property', 'error': str(e)}), 500


@properties_bp.route('/pending', methods=['GET'])
@jwt_required()
@admin_required
def get_pending_properties():
    """Get all pending properties (admin only)"""
    try:
        properties = Property.query.filter(
            Property.status.in_(['pending_review', 'fee_pending'])
        ).order_by(Property.created_at.desc()).all()
        
        return jsonify({
            'properties': [p.to_dict(include_landlord=True) for p in properties]
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch pending properties', 'error': str(e)}), 500


@properties_bp.route('/<int:property_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_property(property_id):
    """Approve a property listing"""
    try:
        user_id = get_jwt_identity()
        property = Property.query.get_or_404(property_id)
        
        if property.status not in ['pending_review', 'fee_pending']:
            return jsonify({'message': 'Property cannot be approved'}), 400
        
        property.approve(user_id)
        db.session.commit()
        
        return jsonify({
            'message': 'Property approved successfully',
            'property': property.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to approve property', 'error': str(e)}), 500


@properties_bp.route('/<int:property_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_property(property_id):
    """Reject a property listing"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        reason = data.get('reason', '')
        
        property = Property.query.get_or_404(property_id)
        
        if property.status not in ['pending_review', 'fee_pending']:
            return jsonify({'message': 'Property cannot be rejected'}), 400
        
        property.reject(user_id, reason)
        db.session.commit()
        
        return jsonify({
            'message': 'Property rejected',
            'property': property.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to reject property', 'error': str(e)}), 500


@properties_bp.route('/<int:property_id>/set-fee', methods=['POST'])
@jwt_required()
@admin_required
def set_partnership_fee(property_id):
    """Set partnership fee for a property"""
    try:
        data = request.get_json()
        fee_amount = data.get('fee_amount')
        
        if not fee_amount or fee_amount <= 0:
            return jsonify({'message': 'Valid fee amount is required'}), 400
        
        property = Property.query.get_or_404(property_id)
        
        if property.status != 'pending_review':
            return jsonify({'message': 'Fee can only be set for pending properties'}), 400
        
        property.set_partnership_fee(fee_amount)
        db.session.commit()
        
        return jsonify({
            'message': f'Partnership fee set to KES {fee_amount}',
            'property': property.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to set fee', 'error': str(e)}), 500


@properties_bp.route('/my-properties', methods=['GET'])
@jwt_required()
@landlord_required
def get_my_properties():
    """Get properties for the current landlord"""
    try:
        user_id = get_jwt_identity()
        
        properties = Property.query.filter_by(landlord_id=user_id).order_by(Property.created_at.desc()).all()
        
        return jsonify({
            'properties': [p.to_dict() for p in properties]
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch properties', 'error': str(e)}), 500
