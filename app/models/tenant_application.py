from app import db
from datetime import datetime

class TenantApplication(db.Model):
    __tablename__ = 'tenant_applications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    
    # Personal Info
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    id_number = db.Column(db.String(100), nullable=False)
    
    # Documents
    id_document_front = db.Column(db.String(500), nullable=False)
    id_document_back = db.Column(db.String(500), nullable=False)
    signed_agreement_url = db.Column(db.String(500), nullable=False)
    
    # Legal tracking
    digital_consent = db.Column(db.Boolean, nullable=False, default=False)
    digital_consent_ip = db.Column(db.String(100), nullable=True)
    
    # Status and links
    status = db.Column(db.String(50), default='pending_approval') # pending_approval, approved, rejected
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    assigned_unit = db.Column(db.String(100), nullable=True)
    
    # Verifier
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    property = db.relationship('Property', backref=db.backref('applications', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('applications_made', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'property_id': self.property_id,
            'property_title': self.property.title if self.property else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'id_number': self.id_number,
            'id_document_front': self.id_document_front,
            'id_document_back': self.id_document_back,
            'signed_agreement_url': self.signed_agreement_url,
            'digital_consent': self.digital_consent,
            'status': self.status,
            'payment_id': self.payment_id,
            'assigned_unit': self.assigned_unit,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'reviewer': self.reviewer.name if self.reviewer else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None
        }
