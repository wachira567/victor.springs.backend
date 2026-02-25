from datetime import datetime
from app import db

class Visit(db.Model):
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Visit Details
    visit_date = db.Column(db.Date, nullable=False)
    visit_time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Status: pending, confirmed, completed, cancelled, no_show
    status = db.Column(db.String(50), default='pending')
    
    # Admin/landlord notes
    landlord_notes = db.Column(db.Text, nullable=True)
    
    # Reminder sent
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def confirm(self):
        """Confirm the visit"""
        self.status = 'confirmed'
        self.confirmed_at = datetime.utcnow()
    
    def complete(self):
        """Mark visit as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
    def cancel(self, user_id):
        """Cancel the visit"""
        self.status = 'cancelled'
        self.cancelled_at = datetime.utcnow()
        self.cancelled_by = user_id
    
    def to_dict(self, include_property=False, include_tenant=False):
        data = {
            'id': self.id,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'visit_time': self.visit_time.isoformat() if self.visit_time else None,
            'notes': self.notes,
            'status': self.status,
            'landlord_notes': self.landlord_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_property and self.property:
            data['property'] = {
                'id': self.property.id,
                'title': self.property.title,
                'location': f"{self.property.address}, {self.property.city}",
                'image': self.property.images[0] if self.property.images else None,
            }
        
        if include_tenant and self.tenant:
            data['tenant'] = {
                'id': self.tenant.id,
                'name': self.tenant.name,
                'phone': self.tenant.phone,
                'email': self.tenant.email,
            }
        
        return data
    
    def __repr__(self):
        return f'<Visit {self.id}>'
