from app import db
from datetime import datetime

class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.String(500), nullable=True) # E.g. '+254712345678'
    description = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
