import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.environ.get('RESEND_API_KEY')
target_email = "treinlojo@gmail.com"
from_email = os.environ.get('MAIL_FROM', 'Victor Springs <noreply@victorspringslimited.qzz.io>')

params = {
    "from": from_email,
    "to": [target_email],
    "subject": "Test - Plain Text Reputation Check",
    "text": "Hello. This is a purely plain-text email with absolutely no links, no HTML, and no formatting. We are testing if the SMTP server accepts the domain handshake.",
}

try:
    print(f"Attempting to send pure text email from {from_email}")
    email = resend.Emails.send(params)
    print("Successfully handed off to Resend API!")
    print(email)
except Exception as e:
    print(f"Error: {e}")
