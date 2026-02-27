import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app

class CloudinaryService:
    def __init__(self):
        # Configure cloudinary if current_app is available, 
        # otherwise assumes it's configured elsewhere setup
        try:
            cloudinary.config(
                cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
                api_key=current_app.config['CLOUDINARY_API_KEY'],
                api_secret=current_app.config['CLOUDINARY_API_SECRET']
            )
        except Exception as e:
            # Silently pass if config is missing during init, as it might be configured globally
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
        """Upload a generic document (like PDF) to Cloudinary and return the secure URL"""
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
