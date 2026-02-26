from datetime import datetime
from app import db
import bcrypt

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True) # Nullable because of Google OAuth
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='tenant')  # super_admin, admin, landlord, tenant
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    phone_verified_at = db.Column(db.DateTime, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    
    # Identity & KYC Fields (Shared)
    id_number = db.Column(db.String(50), nullable=True)
    id_document_url = db.Column(db.String(500), nullable=True)
    
    # Landlord specific fields
    company_name = db.Column(db.String(255), nullable=True)
    company_registration = db.Column(db.String(100), nullable=True)
    is_landlord_verified = db.Column(db.Boolean, default=False)
    verification_status = db.Column(db.String(20), default='pending') # pending, verified, rejected
    
    # Tenant specific fields
    employment_status = db.Column(db.String(50), nullable=True)
    monthly_income = db.Column(db.Numeric(12, 2), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    properties = db.relationship('Property', backref='landlord', lazy='dynamic',
                                foreign_keys='Property.landlord_id')
    visits = db.relationship('Visit', backref='tenant', lazy='dynamic',
                            foreign_keys='Visit.tenant_id')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    documents = db.relationship('Document', backref='user', lazy='dynamic',
                               foreign_keys='Document.user_id')
    identities = db.relationship('Identity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set user password"""
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_admin(self):
        return self.role in ['super_admin', 'admin']
    
    def is_landlord(self):
        return self.role == 'landlord'
    
    def is_tenant(self):
        return self.role == 'tenant'
    
    def can_manage_property(self, property_id):
        """Check if user can manage a specific property"""
        if self.is_admin():
            return True
        if self.is_landlord():
            return any(p.id == property_id for p in self.properties)
        return False
    
    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if self.is_landlord():
            data.update({
                'company_name': self.company_name,
                'company_registration': self.company_registration,
                'is_landlord_verified': self.is_landlord_verified,
                'verification_status': self.verification_status,
                'id_number': self.id_number,
            })
        
        if include_sensitive:
            data.update({
                'id_number': self.id_number,
                'id_document_url': self.id_document_url,
                'employment_status': self.employment_status,
                'monthly_income': float(self.monthly_income) if self.monthly_income else None,
            })
        
        return data
    
    def __repr__(self):
        return f'<User {self.email}>'
