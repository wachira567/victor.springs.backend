import os
import random
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

logger = logging.getLogger(__name__)

def generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))

def generate_otp_token(phone, otp):
    """Statelessly generate a secure hash for the OTP."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps({'phone': phone, 'otp': otp}, salt='otp-salt')

def verify_otp_token(token, phone, otp):
    """Verify the secure hash generated for the OTP."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='otp-salt', max_age=600)  # 10 minutes expiry
        return str(data['phone']) == str(phone) and str(data['otp']) == str(otp)
    except Exception:
        return False

def send_otp_sms(phone_number, otp):
    """
    Send an OTP via Twilio.
    Note: Trial accounts can only send to verified Twilio numbers.
    """
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # Fallback to console if env vars are missing
    if not all([account_sid, auth_token, from_number]):
        logger.warning("Twilio credentials missing. Skipping SMS HTTP dispatch.")
        print(f"--- DEVELOPMENT MODE (Missing Keys) ---")
        print(f"OTP for {phone_number} is: {otp}")
        print(f"---------------------------------------")
        return True, "SMS simulated in console"

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Your Victor Springs Landlord Verification code is: {otp}. It expires in 10 minutes.",
            from_=from_number,
            to=phone_number
        )
        return True, message.sid
    except TwilioRestException as e:
        logger.error(f"Twilio SMS Error: {str(e)}")
        # Since the user is on a trial account, it might fail if the number isn't verified in the Twilio console.
        # We gracefully print it out so development can continue without breaking the UI flow.
        print(f"--- TWILIO ERROR FALLBACK (Trial Account Limit?) ---")
        print(f"Failed to send to {phone_number}. Twilio Error: {e.msg}")
        print(f"OTP for {phone_number} is: {otp}")
        print(f"----------------------------------------------------")
        return False, str(e.msg)
