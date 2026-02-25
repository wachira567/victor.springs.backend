from datetime import datetime
from app import db

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # User who owns the document
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Related property (if applicable)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)
    
    # Document Details
    name = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # lease_agreement, id_document, proof_of_income, etc.
    
    # File URL (Cloudinary)
    file_url = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
    mime_type = db.Column(db.String(100), nullable=True)
    
    # Status: pending, verified, rejected, expired
    status = db.Column(db.String(50), default='pending')
    
    # Verification
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    
    # For lease agreements
    lease_start_date = db.Column(db.Date, nullable=True)
    lease_end_date = db.Column(db.Date, nullable=True)
    is_signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime, nullable=True)
    signed_by_tenant = db.Column(db.Boolean, default=False)
    signed_by_landlord = db.Column(db.Boolean, default=False)
    
    # Access control
    is_accessible = db.Column(db.Boolean, default=False)
    access_granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    access_granted_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    def verify(self, admin_user_id, notes=None):
        """Verify the document"""
        self.status = 'verified'
        self.verified_by = admin_user_id
        self.verified_at = datetime.utcnow()
        self.verification_notes = notes
    
    def reject(self, admin_user_id, notes):
        """Reject the document"""
        self.status = 'rejected'
        self.verified_by = admin_user_id
        self.verified_at = datetime.utcnow()
        self.verification_notes = notes
    
    def sign(self, is_tenant=True):
        """Sign the document"""
        if is_tenant:
            self.signed_by_tenant = True
        else:
            self.signed_by_landlord = True
        
        if self.signed_by_tenant and self.signed_by_landlord:
            self.is_signed = True
            self.signed_at = datetime.utcnow()
    
    def grant_access(self, admin_user_id):
        """Grant access to the document"""
        self.is_accessible = True
        self.access_granted_by = admin_user_id
        self.access_granted_at = datetime.utcnow()
    
    def revoke_access(self):
        """Revoke access to the document"""
        self.is_accessible = False
    
    def to_dict(self, include_file_url=False):
        data = {
            'id': self.id,
            'name': self.name,
            'document_type': self.document_type,
            'status': self.status,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'is_signed': self.is_signed,
            'is_accessible': self.is_accessible,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
        
        if include_file_url and self.is_accessible:
            data['file_url'] = self.file_url
        
        if self.lease_start_date:
            data['lease_start_date'] = self.lease_start_date.isoformat()
        if self.lease_end_date:
            data['lease_end_date'] = self.lease_end_date.isoformat()
        
        return data
    
    def __repr__(self):
        return f'<Document {self.name}>'
