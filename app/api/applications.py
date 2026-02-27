from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.tenant_application import TenantApplication
from app.models.property import Property
from app.models.user import User
from app.models.payment import Payment
from app.models.audit_log import AuditLog
from app.services.cloudinary_service import CloudinaryService
from app.utils.decorators import admin_required
from datetime import datetime
import json

applications_bp = Blueprint('applications', __name__)

@applications_bp.route('/', methods=['POST'], strict_slashes=False)
@jwt_required()
def submit_application():
    """Submit a tenant application (with signed document and IDs)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        if request.form.get('digital_consent') != 'true':
            return jsonify({'message': 'Legal digital consent is required'}), 400
            
        property_id = request.form.get('property_id')
        property = Property.query.get_or_404(property_id)
        
        # Verify Payment if required
        if property.tenant_agreement_fee and property.tenant_agreement_fee > 0:
            payment_id = request.form.get('payment_id')
            if not payment_id:
                return jsonify({'message': 'Payment reference is required for this property'}), 400
            payment = Payment.query.get(payment_id)
            if not payment or payment.status != 'completed' or payment.property_id != property.id or payment.user_id != user.id:
                return jsonify({'message': 'Valid completed payment not found'}), 400
        else:
            payment_id = None
            
        # File uploads
        cloudinary = CloudinaryService()
        id_front = request.files.get('id_document_front')
        id_back = request.files.get('id_document_back')
        signed_agreement = request.files.get('signed_agreement')
        
        if not all([id_front, id_back, signed_agreement]):
            return jsonify({'message': 'ID (front and back) and Signed Agreement are required'}), 400
            
        front_url = cloudinary.upload_image(id_front, folder='tenant_kyc')
        back_url = cloudinary.upload_image(id_back, folder='tenant_kyc')
        
        # Dual upload: Uploadcare (primary) + Cloudinary (backup)
        agreement_result = cloudinary.upload_document_dual(
            signed_agreement,
            folder='tenant_agreements',
            filename=f"signed_agreement_{user.id}_{property_id}.pdf"
        )
        agreement_url = agreement_result['primary_url']
        agreement_backup_url = agreement_result.get('backup_url')
            
        app_record = TenantApplication(
            user_id=user.id,
            property_id=property.id,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            phone=request.form.get('phone'),
            id_number=request.form.get('id_number'),
            id_document_front=front_url,
            id_document_back=back_url,
            signed_agreement_url=agreement_url,
            digital_consent=True,
            digital_consent_ip=request.remote_addr,
            payment_id=payment_id
        )
        
        db.session.add(app_record)
        db.session.flush()  # Get app_record.id before commit
        
        # Court-ready audit log
        AuditLog.log(
            action='application_submitted',
            user_id=user.id,
            resource_type='application',
            resource_id=app_record.id,
            details={
                'tenant_name': f"{request.form.get('first_name')} {request.form.get('last_name')}",
                'tenant_phone': request.form.get('phone'),
                'tenant_id_number': request.form.get('id_number'),
                'property_id': property.id,
                'property_title': property.title,
                'property_address': f"{property.address}, {property.city}",
                'agreement_fee': float(property.tenant_agreement_fee) if property.tenant_agreement_fee else 0,
                'payment_id': payment_id,
                'digital_consent': True,
                'digital_consent_ip': request.remote_addr,
                'id_front_url': front_url,
                'id_back_url': back_url,
                'signed_agreement_url': agreement_url,
                'signed_agreement_backup_url': agreement_backup_url,
                'submission_timestamp': datetime.utcnow().isoformat()
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application': app_record.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to submit application', 'error': str(e)}), 500

@applications_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_applications():
    """Get all applications submitted by current user"""
    try:
        user_id = get_jwt_identity()
        apps = TenantApplication.query.filter_by(user_id=user_id).order_by(TenantApplication.created_at.desc()).all()
        return jsonify({'applications': [a.to_dict() for a in apps]}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch applications', 'error': str(e)}), 500

@applications_bp.route('/admin', methods=['GET'])
@jwt_required()
@admin_required
def get_admin_applications():
    """Admin endpoint to fetch ALL applications or filter by status"""
    try:
        status = request.args.get('status')
        query = TenantApplication.query
        
        if status and status != 'all':
            query = query.filter_by(status=status)
            
        apps = query.order_by(TenantApplication.created_at.desc()).all()
        
        # For the approval modal, include property units data
        results = []
        for app in apps:
            app_dict = app.to_dict()
            # Include property units for vacancy-aware assignment
            if app.property:
                app_dict['property_units'] = app.property.units or []
                app_dict['property_city'] = app.property.city
            results.append(app_dict)
        
        return jsonify({'applications': results}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch applications', 'error': str(e)}), 500

@applications_bp.route('/<int:app_id>/status', methods=['PUT'])
@jwt_required()
@admin_required
def update_application_status(app_id):
    """Admin endpoint to approve or reject an application with vacancy management"""
    try:
        admin_id = get_jwt_identity()
        admin_user = User.query.get(admin_id)
        data = request.get_json()
        new_status = data.get('status')
        assigned_unit = data.get('assigned_unit')
        
        if new_status not in ['approved', 'rejected']:
            return jsonify({'message': 'Invalid status'}), 400
            
        app_record = TenantApplication.query.get_or_404(app_id)
        property = Property.query.get(app_record.property_id)
        
        if new_status == 'approved':
            if not assigned_unit:
                return jsonify({'message': 'Assigned unit type is required for approval'}), 400
            
            app_record.assigned_unit = assigned_unit
            
            # Decrement vacancy count for the assigned unit type
            if property and property.units:
                units = list(property.units)  # Make a mutable copy
                unit_found = False
                all_occupied = True
                
                for unit in units:
                    if unit.get('type') == assigned_unit:
                        current_count = unit.get('vacantCount', 0)
                        if current_count <= 0:
                            return jsonify({'message': f'No vacant units of type "{assigned_unit}" remaining'}), 400
                        unit['vacantCount'] = current_count - 1
                        unit_found = True
                    
                    # Check if any unit type still has vacancies
                    if unit.get('vacantCount', 0) > 0:
                        all_occupied = False
                
                if not unit_found:
                    return jsonify({'message': f'Unit type "{assigned_unit}" not found on this property'}), 400
                
                # After decrementing, re-check if the assigned unit itself brought count to 0
                # and if ALL units are now 0
                all_occupied = all(u.get('vacantCount', 0) <= 0 for u in units)
                
                property.units = units
                
                # If all units are occupied, mark property as rented
                if all_occupied:
                    property.status = 'rented'
                    
        else:
            app_record.rejection_reason = data.get('reason', '')
            
        app_record.status = new_status
        app_record.reviewed_by = admin_id
        app_record.reviewed_at = datetime.utcnow()
        
        # Court-ready audit log for approval/rejection
        AuditLog.log(
            action=f'application_{new_status}',
            user_id=admin_id,
            resource_type='application',
            resource_id=app_id,
            details={
                'admin_name': admin_user.name if admin_user else 'Unknown',
                'admin_id': admin_id,
                'tenant_name': f"{app_record.first_name} {app_record.last_name}",
                'tenant_phone': app_record.phone,
                'tenant_id_number': app_record.id_number,
                'property_id': app_record.property_id,
                'property_title': app_record.property.title if app_record.property else None,
                'assigned_unit': assigned_unit if new_status == 'approved' else None,
                'rejection_reason': data.get('reason', '') if new_status == 'rejected' else None,
                'decision_timestamp': datetime.utcnow().isoformat(),
                'property_auto_rented': (property.status == 'rented') if property else False
            }
        )
        
        db.session.commit()
        
        response_data = {
            'message': f'Application has been {new_status}',
            'application': app_record.to_dict()
        }
        
        # Include updated property units so frontend can update
        if property:
            response_data['updated_units'] = property.units or []
            response_data['property_status'] = property.status
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update application', 'error': str(e)}), 500
