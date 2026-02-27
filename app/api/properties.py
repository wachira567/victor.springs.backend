from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import or_, and_
from app import db
from app.models.property import Property
from app.models.user import User
from app.models.property_like import PropertyLike
from app.services.cloudinary_service import CloudinaryService
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
        
        
        # Check if user is admin to allow fetching specific statuses other than active
        is_admin = False
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                user = User.query.get(identity)
                if user and user.is_admin():
                    is_admin = True
        except:
            pass
            
        if status and status != 'all':
            if status != 'active' and not is_admin:
                return jsonify({'message': 'Permission denied: non-admins can only view active properties'}), 403
            query = query.filter_by(status=status)
        elif not status:
            query = query.filter_by(status='active')
        
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
        user = User.query.get(user_id)
        
        if user and not user.is_super_admin() and not user.is_landlord_verified:
            return jsonify({'message': 'You must complete Landlord Identity Verification (KYC) before listing properties.'}), 403
            
        import json
        
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            # Parse stringified lists from FormData
            for field in ['units', 'amenities', 'images']:
                if field in data and isinstance(data[field], str):
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        data[field] = []
        
        # Sanitize inputs
        title = sanitize_string(data.get('title', '')).strip()
        description = sanitize_string(data.get('description', '')).strip()
        
        from datetime import datetime
        
        def safe_float(val):
            try:
                return float(val) if val and str(val).strip() != "" else None
            except:
                return None
        
        def safe_int(val, default=None):
            try:
                return int(val) if val and str(val).strip() != "" else default
            except:
                return default
                
        def safe_date(val):
            if not val or str(val).strip() == "":
                return datetime.utcnow().date()
            try:
                if isinstance(val, str):
                    return datetime.strptime(val.split('T')[0], '%Y-%m-%d').date()
                return val
            except:
                return datetime.utcnow().date()

        # Create property
        property = Property(
            title=title,
            description=description,
            property_type=data.get('propertyType') or data.get('property_type'),
            city=sanitize_string(data.get('city', '')).strip(),
            address=sanitize_string(data.get('address', '')).strip(),
            location_description=sanitize_string(data.get('locationDescription', '')).strip(),
            latitude=safe_float(data.get('latitude')),
            longitude=safe_float(data.get('longitude')),
            
            # Legacy flat fields
            price=safe_float(data.get('price')),
            deposit=safe_float(data.get('deposit')),
            bedrooms=safe_int(data.get('bedrooms')),
            bathrooms=safe_int(data.get('bathrooms')),
            area=safe_int(data.get('area')),
            
            # New multi-unit / advanced fields
            units=data.get('units', []),
            tenant_agreement_fee=safe_float(data.get('tenantAgreementFee') or data.get('tenant_agreement_fee')),
            
            amenities=data.get('amenities', []),
            images=data.get('images', []),
            available_from=safe_date(data.get('available_from')),
            minimum_lease_months=safe_int(data.get('minimum_lease_months'), 12),
            landlord_id=user_id,
            status='pending_review',
            is_partner_property=True
        )
        
        # Handle Tenant Agreement Upload
        cloudinary = CloudinaryService()
        tenant_agreement = request.files.get('tenant_agreement_file')
        if tenant_agreement:
            url = cloudinary.upload_document(tenant_agreement, folder='tenant_agreements')
            if url:
                property.tenant_agreement_url = url
                
        # Handle Property Image Uploads
        image_files = request.files.getlist('images')
        uploaded_image_urls = []
        if image_files:
            for image_file in image_files:
                if image_file.filename != '':
                    img_url = cloudinary.upload_image(image_file, folder='property_images')
                    if img_url:
                        uploaded_image_urls.append(img_url)
        
        # Merge with existing images if any came from JSON 
        property.images = property.images + uploaded_image_urls if property.images else uploaded_image_urls

        # Auto-approve if created by admin/super_admin
        if user and user.is_admin():
            property.approve(user_id)
                
        db.session.add(property)
        db.session.commit()
        
        status_msg = 'Property created and published successfully.' if user and user.is_admin() else 'Property submitted successfully. It will be reviewed shortly.'
        
        return jsonify({
            'message': status_msg,
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
        
        if property.status not in ['pending_review', 'fee_pending', 'inactive']:
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

@properties_bp.route('/<int:property_id>/status', methods=['PUT'])
@jwt_required()
@admin_required
def update_property_status(property_id):
    """Admin toggle property status to inactive/active/approved"""
    try:
        property = Property.query.get_or_404(property_id)
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['active', 'inactive', 'approved', 'rejected', 'pending_review']:
            return jsonify({'message': 'Invalid status'}), 400
            
        property.status = new_status
        db.session.commit()
        
        return jsonify({
            'message': f'Property status updated to {new_status}',
            'property': property.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update property status', 'error': str(e)}), 500


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

@properties_bp.route('/<int:property_id>/like', methods=['POST'])
@jwt_required()
def toggle_property_like(property_id):
    """Toggle a like on a property for the current user"""
    try:
        user_id = get_jwt_identity()
        property = Property.query.get_or_404(property_id)
        
        # Prevent liking multiple times
        existing_like = PropertyLike.query.filter_by(user_id=user_id, property_id=property_id).first()
        
        if existing_like:
            # Unlike
            db.session.delete(existing_like)
            property.like_count = max(0, property.like_count - 1)
            db.session.commit()
            return jsonify({'message': 'Property unliked', 'liked': False, 'like_count': property.like_count}), 200
        else:
            # Like
            new_like = PropertyLike(user_id=user_id, property_id=property_id)
            db.session.add(new_like)
            property.like_count += 1
            db.session.commit()
            return jsonify({'message': 'Property liked', 'liked': True, 'like_count': property.like_count}), 200
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error processing like', 'error': str(e)}), 500

@properties_bp.route('/<int:property_id>/interact', methods=['POST'])
def record_property_interaction(property_id):
    """Record a user interaction (whatsapp, call, map) without requiring auth"""
    try:
        data = request.get_json() or {}
        interaction_type = data.get('type')
        
        if interaction_type not in ['whatsapp', 'call', 'map']:
            return jsonify({'message': 'Invalid interaction type'}), 400
            
        property = Property.query.get_or_404(property_id)
        
        if interaction_type == 'whatsapp':
            property.whatsapp_clicks += 1
        elif interaction_type == 'call':
            property.call_clicks += 1
        elif interaction_type == 'map':
            property.map_clicks += 1
            
        db.session.commit()
        
        return jsonify({
            'message': f'{interaction_type} interaction recorded successfully',
            'stats': {
                'whatsapp_clicks': property.whatsapp_clicks,
                'call_clicks': property.call_clicks,
                'map_clicks': property.map_clicks
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to record interaction', 'error': str(e)}), 500
