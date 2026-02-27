from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from app import db
from app.models.enquiry import Enquiry
from app.models.property import Property
from app.models.user import User
from app.utils.decorators import admin_required

enquiries_bp = Blueprint('enquiries', __name__)

@enquiries_bp.route('/', methods=['POST'], strict_slashes=False)
def submit_enquiry():
    """Submit a property enquiry"""
    try:
        data = request.get_json()
        property_id = data.get('property_id')
        message = data.get('message', '').strip()
        
        if not property_id or not message:
            return jsonify({'message': 'Property ID and message are required'}), 400
            
        property = Property.query.get_or_404(property_id)
        
        # Check if auth'd
        user_id = None
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                user_id = int(identity)
        except:
            pass
            
        enquiry = Enquiry(
            property_id=property_id,
            user_id=user_id,
            message=message,
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone')
        )
        
        if not user_id and not (enquiry.name and enquiry.email):
            return jsonify({'message': 'Name and email required for guest enquiries'}), 400
            
        db.session.add(enquiry)
        db.session.commit()
        
        return jsonify({
            'message': 'Enquiry submitted successfully',
            'enquiry': enquiry.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to submit enquiry', 'error': str(e)}), 500

@enquiries_bp.route('/admin', methods=['GET'])
@jwt_required()
@admin_required
def get_admin_enquiries():
    """Get all enquiries (admin only)"""
    try:
        enquiries = Enquiry.query.order_by(Enquiry.created_at.desc()).all()
        return jsonify({
            'enquiries': [e.to_dict() for e in enquiries]
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to fetch enquiries', 'error': str(e)}), 500
