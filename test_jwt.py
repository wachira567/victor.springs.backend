import requests
import json

base_url = "http://127.0.0.1:5000/api"

# Login to get token
resp = requests.post(f"{base_url}/auth/login", json={
    "email": "admin@victorsprings.com", # Needs a real user
    "password": "password123"
}, headers={'Content-Type': 'application/json'})

print("Login:", resp.status_code, resp.text)
if resp.status_code == 200:
    token = resp.json().get('token')
    
    # Test my-properties
    resp2 = requests.get(f"{base_url}/properties/my-properties", headers={
        "Authorization": f"Bearer {token}"
    })
    print("My Properties:", resp2.status_code, resp2.text)
