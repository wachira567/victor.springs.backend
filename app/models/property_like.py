from app import db
from datetime import datetime

class PropertyLike(db.Model):
    __tablename__ = 'property_likes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensure a user can only like a property once
    __table_args__ = (db.UniqueConstraint('user_id', 'property_id', name='uq_user_property_like'),)

    property = db.relationship('Property', backref=db.backref('likes', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('property_likes', lazy='dynamic'))
