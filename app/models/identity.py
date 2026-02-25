from datetime import datetime
from app import db

class Identity(db.Model):
    __tablename__ = 'identities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'local', 'google'
    provider_id = db.Column(db.String(255), nullable=True, index=True) # Google Sub ID, or None for local
    password_hash = db.Column(db.String(255), nullable=True) # Used if provider is 'local'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Identity {self.provider} for User {self.user_id}>'
