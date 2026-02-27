import requests
import base64
import json
from datetime import datetime
from flask import current_app
import os

class MpesaService:
    """M-Pesa Daraja API Service"""
    
    def __init__(self):
        self.consumer_key = os.getenv('MPESA_CONSUMER_KEY', '')
        self.consumer_secret = os.getenv('MPESA_CONSUMER_SECRET', '')
        self.passkey = os.getenv('MPESA_PASSKEY', '')
        self.shortcode = os.getenv('MPESA_SHORTCODE', '174379')  # Test shortcode
        self.env = os.getenv('MPESA_ENV', 'sandbox')
        
        # Base URLs
        # Base URLs (Kenyan M-Pesa API)
        if self.env == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
    
    def get_access_token(self):
        """Get M-Pesa access token"""
        try:
            url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
            
            credentials = base64.b64encode(
                f'{self.consumer_key}:{self.consumer_secret}'.encode()
            ).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                current_app.logger.error(f'M-Pesa token error: {response.status_code} - {response.text}')
                return None
                
        except Exception as e:
            current_app.logger.error(f'M-Pesa token exception: {str(e)}')
            return None
    
    def generate_password(self, timestamp):
        """Generate M-Pesa password"""
        data_to_encode = f'{self.shortcode}{self.passkey}{timestamp}'
        return base64.b64encode(data_to_encode.encode()).decode()
    
    def format_phone_number(self, phone_number):
        """Format phone number to 254XXXXXXXXX format for Safaricom API"""
        if not phone_number:
            return ""
            
        # Remove spaces, dashes, and plus sign
        phone = str(phone_number).replace(' ', '').replace('-', '').replace('+', '')
        
        # Kenyan Specifics: Convert 07... or 01... to 2547... or 2541...
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('7') and len(phone) == 9:
            phone = '254' + phone
        elif phone.startswith('1') and len(phone) == 9:
            phone = '254' + phone
            
        # Ensure it starts with 254
        if not phone.startswith('254') and len(phone) == 9:
             phone = '254' + phone
        
        return phone
    
    def initiate_stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate M-Pesa STK Push (Lipa na M-Pesa Online)"""
        try:
            access_token = self.get_access_token()
            
            if not access_token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Generate password
            password = self.generate_password(timestamp)
            
            # Format phone number
            formatted_phone = self.format_phone_number(phone_number)
            
            # Prepare request
            url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(amount),
                'PartyA': formatted_phone,
                'PartyB': self.shortcode,
                'PhoneNumber': formatted_phone,
                'CallBackURL': os.getenv('MPESA_CALLBACK_URL', ''),
                'AccountReference': str(account_reference)[:12],  # Max 12 chars for better compatibility
                'TransactionDesc': str(transaction_desc)[:12]  # Max 12 chars
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ResponseCode') == '0':
                    return {
                        'success': True,
                        'checkout_request_id': result.get('CheckoutRequestID'),
                        'merchant_request_id': result.get('MerchantRequestID'),
                        'response_description': result.get('ResponseDescription')
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('ResponseDescription', 'Unknown error')
                    }
            else:
                current_app.logger.error(f'M-Pesa STK push error: {response.text}')
                return {'success': False, 'error': 'Failed to initiate payment'}
                
        except Exception as e:
            current_app.logger.error(f'M-Pesa STK push exception: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def query_stk_status(self, checkout_request_id):
        """Query STK push transaction status"""
        try:
            access_token = self.get_access_token()
            
            if not access_token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self.generate_password(timestamp)
            
            url = f'{self.base_url}/mpesa/stkpushquery/v1/query'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': 'Failed to query status'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def validate_transaction(self, callback_data):
        """Validate M-Pesa callback data"""
        try:
            result_code = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
            
            if result_code == 0:
                return {'valid': True}
            else:
                return {
                    'valid': False,
                    'error': callback_data.get('Body', {}).get('stkCallback', {}).get('ResultDesc', 'Transaction failed')
                }
                
        except Exception as e:
            return {'valid': False, 'error': str(e)}
