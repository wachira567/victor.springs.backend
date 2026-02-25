from datetime import datetime
from app import db

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # User who made the payment
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Payment Details
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), default='KES')
    
    # Payment Type: partnership_fee, application_fee, deposit, rent, service_fee
    payment_type = db.Column(db.String(50), nullable=False)
    
    # Related property (if applicable)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)
    
    # M-Pesa Details
    mpesa_receipt_number = db.Column(db.String(100), nullable=True, unique=True)
    mpesa_checkout_request_id = db.Column(db.String(100), nullable=True, index=True)
    phone_number = db.Column(db.String(20), nullable=False)
    
    # Status: pending, processing, completed, failed, refunded
    status = db.Column(db.String(50), default='pending', index=True)
    
    # Description
    description = db.Column(db.Text, nullable=True)
    
    # Extra Data (JSON for additional data)
    extra_data = db.Column(db.JSON, default=dict)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    failed_at = db.Column(db.DateTime, nullable=True)
    failure_reason = db.Column(db.Text, nullable=True)
    
    def complete(self, receipt_number):
        """Mark payment as completed"""
        self.status = 'completed'
        self.mpesa_receipt_number = receipt_number
        self.completed_at = datetime.utcnow()
    
    def fail(self, reason):
        """Mark payment as failed"""
        self.status = 'failed'
        self.failure_reason = reason
        self.failed_at = datetime.utcnow()
    
    def process(self):
        """Mark payment as processing"""
        self.status = 'processing'
    
    def to_dict(self, include_user=False):
        data = {
            'id': self.id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_type': self.payment_type,
            'status': self.status,
            'mpesa_receipt_number': self.mpesa_receipt_number,
            'phone_number': self.phone_number,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        
        if include_user and self.user:
            data['user'] = {
                'id': self.user.id,
                'name': self.user.name,
                'email': self.user.email,
            }
        
        if self.property_id:
            data['property_id'] = self.property_id
        
        return data
    
    def __repr__(self):
        return f'<Payment {self.id}>'
