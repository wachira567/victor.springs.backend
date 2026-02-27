import requests
from flask import current_app


class UploadcareService:
    """Service for uploading files to Uploadcare for reliable PDF delivery.
    Uploadcare serves as the primary CDN for document downloads.
    """
    
    BASE_UPLOAD_URL = 'https://upload.uploadcare.com/base/'
    BASE_CDN_URL = 'https://ucarecdn.com'
    
    def __init__(self):
        try:
            self.public_key = current_app.config.get('UPLOADCARE_PUBLIC_KEY', '')
            self.secret_key = current_app.config.get('UPLOADCARE_SECRET_KEY', '')
        except Exception:
            self.public_key = ''
            self.secret_key = ''
    
    def upload_file(self, file_obj, filename=None):
        """Upload a file to Uploadcare and return the CDN URL.
        
        Uses the simple upload API (multipart POST).
        Returns the full CDN URL for direct download, or None on failure.
        """
        if not self.public_key:
            print("Uploadcare: No public key configured, skipping upload")
            return None
            
        try:
            fname = filename or getattr(file_obj, 'filename', 'document.pdf')
            
            # Read file content
            file_content = file_obj.read()
            
            # Reset file pointer so Cloudinary can also read it
            file_obj.seek(0)
            
            resp = requests.post(
                self.BASE_UPLOAD_URL,
                files={'file': (fname, file_content)},
                data={
                    'UPLOADCARE_PUB_KEY': self.public_key,
                    'UPLOADCARE_STORE': '1',  # auto-store
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                file_uuid = data.get('file')
                if file_uuid:
                    cdn_url = f"{self.BASE_CDN_URL}/{file_uuid}/{fname}"
                    return cdn_url
            
            print(f"Uploadcare upload failed: {resp.status_code} {resp.text}")
            return None
            
        except Exception as e:
            print(f"Uploadcare upload error: {str(e)}")
            return None
