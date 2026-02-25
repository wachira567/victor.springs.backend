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
        <a href="{verify_link}" style="display:inline-block;padding:10px 20px;background-color:#2196F3;color:white;text-decoration:none;border-radius:5px;">Verify Email</a>
        <p>If you did not create this account, you can safely ignore this email.</p>
        <p>Alternatively, you can copy and paste this link into your browser:</p>
        <p>{verify_link}</p>
        """

        params = {
            "from": "Victor Springs <noreply@victorsprings.com>", # Use a verified domain or testing domain
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
        <a href="{reset_link}" style="display:inline-block;padding:10px 20px;background-color:#2196F3;color:white;text-decoration:none;border-radius:5px;">Reset Password</a>
        <p>If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
        <p>Alternatively, you can copy and paste this link into your browser:</p>
        <p>{reset_link}</p>
        """

        params = {
            "from": "Victor Springs <noreply@victorsprings.com>",
            "to": [to_email],
            "subject": "Reset your password - Victor Springs",
            "html": html_content
        }

        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False
