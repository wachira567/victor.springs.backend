import os
import resend
from flask import render_template_string

def send_verification_email(to_email, token):
    """Send an email verification magic link using Resend."""
    try:
        resend.api_key = os.environ.get('RESEND_API_KEY')
        if not resend.api_key:
            print("WARNING: RESEND_API_KEY is not set. Email not sent.")
            return False

        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
        verify_link = f"{frontend_url}/verify-email?token={token}"

        html_content = f"""
        <h2>Welcome to Victor Springs!</h2>
        <p>Thank you for registering. Please click the button below to verify your email address and activate your account:</p>
        <br>
        <center>
            <a href="{verify_link}" style="display:inline-block;padding:12px 24px;background-color:#2196F3;color:white;text-decoration:none;border-radius:5px;font-weight:bold;font-size:16px;">Verify Email</a>
        </center>
        <br>
        <p>If you did not create this account, you can safely ignore this email.</p>
        """

        params = {
            "from": os.environ.get('MAIL_FROM', 'Victor Springs <victorsprings@victorspringslimited.qzz.io>'),
            "to": [to_email],
            "subject": "Verify your email address - Victor Springs",
            "html": html_content
        }

        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False

def send_password_reset_email(to_email, token):
    """Send a password reset magic link using Resend."""
    try:
        resend.api_key = os.environ.get('RESEND_API_KEY')
        if not resend.api_key:
            print("WARNING: RESEND_API_KEY is not set. Email not sent.")
            return False

        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
        reset_link = f"{frontend_url}/reset-password?token={token}"

        html_content = f"""
        <h2>Reset Your Password</h2>
        <p>We received a request to reset the password for your Victor Springs account. Click the button below to choose a new password:</p>
        <br>
        <center>
            <a href="{reset_link}" style="display:inline-block;padding:12px 24px;background-color:#2196F3;color:white;text-decoration:none;border-radius:5px;font-weight:bold;font-size:16px;">Reset Password</a>
        </center>
        <br>
        <p>If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
        """

        params = {
            "from": os.environ.get('MAIL_FROM', 'Victor Springs <victorsprings@victorspringslimited.qzz.io>'),
            "to": [to_email],
            "subject": "Reset your password - Victor Springs",
            "html": html_content
        }

        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False
