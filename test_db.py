from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
import requests

app = create_app()
with app.app_context():
    user = User(name='Test Landlord', email='demo2@landlord.com', role='landlord')
    user.set_password('Password123!')
    user.is_verified = True
    user.verification_status = 'verified'
    db.session.add(user)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        user = User.query.filter_by(email='demo2@landlord.com').first()
    
    token = create_access_token(identity=str(user.id))
    print("TOKEN_START", token, "TOKEN_END")
