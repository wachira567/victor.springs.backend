from app import db
from datetime import datetime

class Enquiry(db.Model):
    __tablename__ = 'enquiries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Could be from anonymous
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    
    # In case of non-registered users enquiring
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new') # new, reading, resolved
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    property = db.relationship('Property', backref=db.backref('enquiries', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('enquiries_made', lazy=True))

    def to_dict(self):
        user_data = None
        if self.user:
            user_data = {
                'id': self.user.id,
                'name': self.user.name or f"{self.user.firstName} {self.user.lastName}",
                'email': self.user.email,
                'phone': self.user.phone
            }
        else:
            user_data = {
                'name': self.name,
                'email': self.email,
                'phone': self.phone
            }
            
        return {
            'id': self.id,
            'property_id': self.property_id,
            'property': {
                'id': self.property.id,
                'title': self.property.title,
                'location': self.property.location or self.property.city,
                'landlord': {
                    'id': self.property.landlord.id if self.property.landlord else None,
                    'name': self.property.landlord.name if self.property.landlord else 'Unknown'
                } if self.property.landlord else None
            } if self.property else None,
            'user': user_data,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
