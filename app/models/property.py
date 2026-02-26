from datetime import datetime
from app import db

class Property(db.Model):
    __tablename__ = 'properties'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Property Type & Location
    property_type = db.Column(db.String(50), nullable=False)  # apartment, house, villa, studio, condo, townhouse
    city = db.Column(db.String(100), nullable=False, index=True)
    address = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Numeric(10, 8), nullable=True)
    longitude = db.Column(db.Numeric(11, 8), nullable=True)
    
    # Pricing
    price = db.Column(db.Numeric(12, 2), nullable=True)
    deposit = db.Column(db.Numeric(12, 2), nullable=True)
    tenant_agreement_fee = db.Column(db.Numeric(12, 2), nullable=True)
    
    # Documents & Legal
    tenant_agreement_url = db.Column(db.String(500), nullable=True)
    
    # Details
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Integer, nullable=True)
    area = db.Column(db.Integer, nullable=True)  # in square meters
    
    # Multi-Unit Configuration & Map Location
    units = db.Column(db.JSON, default=list)
    location_description = db.Column(db.Text, nullable=True)
    
    # Amenities (stored as JSON array)
    amenities = db.Column(db.JSON, default=list)
    
    # Images (stored as JSON array of Cloudinary URLs)
    images = db.Column(db.JSON, default=list)
    
    # Availability
    available_from = db.Column(db.Date, nullable=False)
    minimum_lease_months = db.Column(db.Integer, default=12)
    
    # Status
    # pending_review -> fee_pending -> approved/active -> rented -> inactive
    status = db.Column(db.String(50), default='pending_review', index=True)
    
    # Partnership Pipeline Fields
    is_partner_property = db.Column(db.Boolean, default=False)
    partnership_fee = db.Column(db.Numeric(12, 2), nullable=True)
    partnership_fee_paid = db.Column(db.Boolean, default=False)
    partnership_fee_paid_at = db.Column(db.DateTime, nullable=True)
    
    # Review Fields
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Admin edits (for quality control)
    admin_edited_title = db.Column(db.String(255), nullable=True)
    admin_edited_description = db.Column(db.Text, nullable=True)
    
    # Statistics
    view_count = db.Column(db.Integer, default=0)
    inquiry_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    whatsapp_clicks = db.Column(db.Integer, default=0)
    call_clicks = db.Column(db.Integer, default=0)
    map_clicks = db.Column(db.Integer, default=0)
    
    # Relationships
    landlord_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    visits = db.relationship('Visit', backref='property', lazy='dynamic')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)
    
    def get_display_title(self):
        """Return admin-edited title if available, otherwise original"""
        return self.admin_edited_title or self.title
    
    def get_display_description(self):
        """Return admin-edited description if available, otherwise original"""
        return self.admin_edited_description or self.description
    
    def can_be_edited_by(self, user):
        """Check if user can edit this property"""
        if user.is_super_admin():
            return True
        if user.is_admin() and self.status in ['pending_review', 'fee_pending']:
            return True
        if user.id == self.landlord_id and self.status in ['pending_review', 'rejected']:
            return True
        return False
    
    def approve(self, admin_user_id):
        """Approve the property listing"""
        self.status = 'active'
        self.reviewed_by = admin_user_id
        self.reviewed_at = datetime.utcnow()
        self.published_at = datetime.utcnow()
    
    def reject(self, admin_user_id, reason):
        """Reject the property listing"""
        self.status = 'rejected'
        self.reviewed_by = admin_user_id
        self.reviewed_at = datetime.utcnow()
        self.rejection_reason = reason
    
    def set_partnership_fee(self, fee_amount):
        """Set partnership fee for external landlord"""
        self.partnership_fee = fee_amount
        self.status = 'fee_pending'
    
    def mark_fee_paid(self):
        """Mark partnership fee as paid"""
        self.partnership_fee_paid = True
        self.partnership_fee_paid_at = datetime.utcnow()
        self.status = 'pending_review'
    
    def increment_views(self):
        """Increment view counter"""
        self.view_count += 1
    
    def increment_inquiries(self):
        """Increment inquiry counter"""
        self.inquiry_count += 1
    
    def to_dict(self, include_landlord=False):
        data = {
            'id': self.id,
            'title': self.get_display_title(),
            'description': self.get_display_description(),
            'property_type': self.property_type,
            'city': self.city,
            'address': self.address,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'price': float(self.price) if self.price is not None else None,
            'deposit': float(self.deposit) if self.deposit is not None else (float(self.price) if self.price is not None else None),
            'tenant_agreement_fee': float(self.tenant_agreement_fee) if self.tenant_agreement_fee is not None else None,
            'tenant_agreement_url': self.tenant_agreement_url,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'area': self.area,
            'units': self.units or [],
            'location_description': self.location_description,
            'amenities': self.amenities or [],
            'images': self.images or [],
            'available_from': self.available_from.isoformat() if self.available_from else None,
            'minimum_lease_months': self.minimum_lease_months,
            'status': self.status,
            'is_partner_property': self.is_partner_property,
            'view_count': self.view_count,
            'inquiry_count': self.inquiry_count,
            'like_count': self.like_count,
            'whatsapp_clicks': self.whatsapp_clicks,
            'call_clicks': self.call_clicks,
            'map_clicks': self.map_clicks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }
        
        if include_landlord and self.landlord:
            data['landlord'] = {
                'id': self.landlord.id,
                'name': self.landlord.name,
                'phone': self.landlord.phone,
                'email': self.landlord.email,
            }
        
        return data
    
    def __repr__(self):
        return f'<Property {self.title}>'
