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
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <div style="background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 24px;">🎉 Welcome to Victor Springs!</h2>
            </div>
            <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
                <p>Thank you for signing up! Please verify your email address to complete your registration.</p>
                <p>Click the button below to verify your email:</p>
                <center>
                    <a href="{verify_link}" style="display: inline-block; background-color: #2196F3; color: white; padding: 15px 30px; text-decoration: none; border-radius: 4px; margin: 20px 0; font-weight: bold;">Verify My Email</a>
                </center>
                <p>If you didn't create an account with Victor Springs, you can safely ignore this email.</p>
                <div style="text-align: center; margin-top: 30px; color: #666; font-size: 12px;">
                    <p>&copy; 2026 Victor Springs Limited. All rights reserved.</p>
                </div>
            </div>
        </div>
        """

        params = {
            "from": os.environ.get('MAIL_FROM', 'Victor Springs <noreply@victorspringslimited.qzz.io>'),
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
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <div style="background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 24px;">🔐 Password Reset Request</h2>
            </div>
            <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
                <p>We received a request to reset your password. Click the button below to choose a new password:</p>
                <center>
                    <a href="{reset_link}" style="display: inline-block; background-color: #2196F3; color: white; padding: 15px 30px; text-decoration: none; border-radius: 4px; margin: 20px 0; font-weight: bold;">Reset My Password</a>
                </center>
                <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 10px; border-radius: 4px; margin: 15px 0;">
                    <p><strong>This link will expire in 1 hour for security purposes.</strong></p>
                    <p>If you didn't request a password reset, you can safely ignore this email.</p>
                </div>
                <div style="text-align: center; margin-top: 30px; color: #666; font-size: 12px;">
                    <p>&copy; 2026 Victor Springs Limited. All rights reserved.</p>
                </div>
            </div>
        </div>
        """

        params = {
            "from": os.environ.get('MAIL_FROM', 'Victor Springs <noreply@victorspringslimited.qzz.io>'),
            "to": [to_email],
            "subject": "Reset your password - Victor Springs",
            "html": html_content
        }

        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False
def send_payment_notification_email(admin_email, payment_details):
    """Notify admin of a successful tenant payment."""
    try:
        resend.api_key = os.environ.get('RESEND_API_KEY')
        if not resend.api_key:
            return False

        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 24px;">💰 New Payment Received</h2>
            </div>
            <div style="background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
                <p>A new payment has been successfully processed on Victor Springs.</p>
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Type:</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{payment_details.get('payment_type', 'N/A')}</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Amount:</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">KES {payment_details.get('amount', '0')}</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Tenant:</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{payment_details.get('tenant_name', 'N/A')}</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Phone:</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{payment_details.get('phone', 'N/A')}</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>House:</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{payment_details.get('property_title', 'N/A')}</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Reference:</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{payment_details.get('receipt_number', 'N/A')}</td></tr>
                </table>
                <div style="text-align: center; margin-top: 30px; color: #666; font-size: 12px;">
                    <p>&copy; 2026 Victor Springs Limited. All rights reserved.</p>
                </div>
            </div>
        </div>
        """

        params = {
            "from": os.environ.get('MAIL_FROM', 'Victor Springs <noreply@victorspringslimited.qzz.io>'),
            "to": [admin_email],
            "subject": f"New Payment: KES {payment_details.get('amount')} - {payment_details.get('tenant_name')}",
            "html": html_content
        }

        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Failed to send payment notification email: {e}")
        return False
