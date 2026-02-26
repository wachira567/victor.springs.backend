import requests
import re
import subprocess

# get token
output = subprocess.check_output(['bash', '-c', 'source venv/bin/activate && python test_db.py'], text=True)
token = re.search(r'TOKEN_START (.*) TOKEN_END', output).group(1)

with open('test_submit.py', 'rb') as f:
    res = requests.post('http://127.0.0.1:5000/api/properties/', 
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "Test Title",
            "description": "Test Descr",
            "propertyType": "apartment",
            "city": "Nairobi",
            "address": "123 Test St",
            "latitude": "-1.2",
            "longitude": "36.8",
            "units": '[{"type": "Studio", "price": 20000}]',
            "amenities": '["wifi"]'
        },
        files={"images": f}
    )
print("Status:", res.status_code)
print("Response:", res.text)
