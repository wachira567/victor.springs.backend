import requests
from app import create_app, db
from app.models.user import User
from flask_jwt_extended import create_access_token
import io

app = create_app()

def run_test():
    with app.app_context():
        user = User.query.filter_by(role='landlord').first()
        if not user:
            print("No landlord found.")
            return

        print(f"Testing with User ID: {user.id}")
        token = create_access_token(identity=str(user.id))
        
        import app.api.auth as auth_module
        auth_module.verify_otp_token = lambda a, b, c: True
        
        client = app.test_client()
        data = {
            'first_name': 'Test',
            'last_name': 'Landlord',
            'id_number': '12345678',
            'phone': '+254700000001',
            'signature_method': 'electronic',
            'otp': '123456',
            'otp_token': 'dummy',
            'id_document_front': (io.BytesIO(b"dummy image data"), "front.jpg"),
            'id_document_back': (io.BytesIO(b"dummy image data"), "back.jpg"),
        }
        
        resp = client.post('/api/auth/kyc/submit', headers={
            'Authorization': f'Bearer {token}'
        }, data=data, content_type='multipart/form-data')
        
        print(f"Response Status: {resp.status_code}")
        try:
            print("Data:", resp.json)
        except:
            print("Text:", resp.data)

if __name__ == "__main__":
    run_test()
