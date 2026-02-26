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
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px; }}
                .content {{ padding: 20px; text-align: center; }}
                .button {{ display: inline-block; padding: 14px 28px; background-color: #2196F3; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; margin: 30px 0; }}
                .footer {{ text-align: center; margin-top: 40px; color: #777777; font-size: 12px; border-top: 1px solid #e0e0e0; padding-top: 20px; }}
                h2 {{ margin: 0; font-size: 24px; }}
            </style>
        </head>
        <body style="background-color: #f5f5f5; padding: 20px;">
            <div class="container">
                <div class="header">
                    <h2>Welcome to Victor Springs</h2>
                </div>
                <div class="content">
                    <p>Thank you for registering an account with us. We're thrilled to have you!</p>
                    <p>Before you get started, we just need to verify your email address to ensure your account is secure.</p>
                    <a href="{verify_link}" class="button">Verify My Email</a>
                    <p style="text-align: left; font-size: 14px; margin-top: 20px;">If you did not create an account using this email address, please ignore this message. Your information is safe.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Victor Springs Limited. All rights reserved.</p>
                    <p>This is an automated message, please do not reply directly to this email.</p>
                </div>
            </div>
        </body>
        </html>
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
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px; }}
                .content {{ padding: 20px; text-align: center; }}
                .button {{ display: inline-block; padding: 14px 28px; background-color: #2196F3; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px; margin: 30px 0; }}
                .footer {{ text-align: center; margin-top: 40px; color: #777777; font-size: 12px; border-top: 1px solid #e0e0e0; padding-top: 20px; }}
                h2 {{ margin: 0; font-size: 24px; }}
            </style>
        </head>
        <body style="background-color: #f5f5f5; padding: 20px;">
            <div class="container">
                <div class="header">
                    <h2>Password Reset Request</h2>
                </div>
                <div class="content">
                    <p>We received a secure request to reset the password for your Victor Springs account.</p>
                    <p>Click the button below to choose a new password and regain access to your account:</p>
                    <a href="{reset_link}" class="button">Reset My Password</a>
                    <p style="text-align: left; font-size: 14px; margin-top: 20px; background-color: #fff3cd; padding: 15px; border-radius: 5px;"><strong>Security Notice:</strong> If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged, and your account is completely secure.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Victor Springs Limited. All rights reserved.</p>
                    <p>This is an automated safety notification.</p>
                </div>
            </div>
        </body>
        </html>
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
