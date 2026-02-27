import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app

class CloudinaryService:
    def __init__(self):
        try:
            cloudinary.config(
                cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
                api_key=current_app.config['CLOUDINARY_API_KEY'],
                api_secret=current_app.config['CLOUDINARY_API_SECRET']
            )
        except Exception as e:
            pass
            
    def upload_image(self, file, folder='victorsprings_images'):
        """Upload an image to Cloudinary and return the secure URL"""
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type='image'
            )
            return result.get('secure_url')
        except Exception as e:
            print(f"Cloudinary image upload error: {str(e)}")
            return None
            
    def upload_document(self, file, folder='victorsprings_documents'):
        """Upload a document to Cloudinary (backup) and return the secure URL"""
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type='auto'
            )
            return result.get('secure_url')
        except Exception as e:
            print(f"Cloudinary document upload error: {str(e)}")
            return None

    def upload_document_dual(self, file, folder='victorsprings_documents', filename=None):
        """Upload a document to both Uploadcare (primary) and Cloudinary (backup).
        
        Returns a dict with:
            'primary_url': Uploadcare CDN URL (for downloads)
            'backup_url': Cloudinary URL (for backup/audit)
        """
        from app.services.uploadcare_service import UploadcareService
        
        # Upload to Uploadcare first (primary delivery)
        uploadcare = UploadcareService()
        primary_url = uploadcare.upload_file(file, filename=filename)
        
        # Upload to Cloudinary as backup (file pointer was reset by Uploadcare service)
        backup_url = self.upload_document(file, folder=folder)
        
        # If Uploadcare failed, fall back to Cloudinary URL  
        if not primary_url:
            primary_url = backup_url
        
        return {
            'primary_url': primary_url,
            'backup_url': backup_url
        }
