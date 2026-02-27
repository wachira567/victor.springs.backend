from datetime import datetime
from app import db
from flask import request

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True) # e.g., 'initiate_upload', 'view_agreement'
    resource_type = db.Column(db.String(50), nullable=True) # e.g., 'property', 'application'
    resource_id = db.Column(db.Integer, nullable=True)
    
    # Context
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.JSON, default=dict) # e.g. { 'property_title': 'Spacious Appt' }
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def log(action, user_id=None, resource_type=None, resource_id=None, details=None):
        """Helper to create a log entry"""
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request and request.user_agent else None
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'details': self.details,
            'created_at': self.created_at.isoformat()
        }
