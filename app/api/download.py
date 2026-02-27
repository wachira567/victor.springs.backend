from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required
import requests as http_requests

download_bp = Blueprint('download', __name__)

@download_bp.route('/', methods=['GET'], strict_slashes=False)
@jwt_required()
def proxy_download():
    """Proxy file download — fetches from CDN server-side and streams to client.
    Bypasses CORS and CDN URL issues. Forces Content-Disposition: attachment.
    
    Usage: GET /api/download?url=https://...&filename=document.pdf
    """
    file_url = request.args.get('url')
    filename = request.args.get('filename', 'document.pdf')
    
    if not file_url:
        return jsonify({'message': 'Missing url parameter'}), 400
    
    # Only allow downloads from trusted CDNs
    allowed_hosts = ['ucarecdn.com', 'res.cloudinary.com', 'cloudinary.com']
    from urllib.parse import urlparse
    parsed = urlparse(file_url)
    if not any(host in parsed.hostname for host in allowed_hosts):
        return jsonify({'message': 'Untrusted file source'}), 403
    
    try:
        # If it's a Cloudinary URL, inject fl_attachment for reliable PDF delivery
        if 'cloudinary.com' in file_url and '/upload/' in file_url and 'fl_attachment' not in file_url:
            file_url = file_url.replace('/upload/', '/upload/fl_attachment/')
        
        resp = http_requests.get(file_url, stream=True, timeout=30)
        
        if resp.status_code != 200:
            # If Uploadcare fails, try Cloudinary backup if URL is Uploadcare
            return jsonify({
                'message': 'File not found on CDN',
                'status': resp.status_code
            }), 404
        
        content_type = resp.headers.get('Content-Type', 'application/octet-stream')
        
        # Force PDF content type for PDF files
        if filename.endswith('.pdf'):
            content_type = 'application/pdf'
        
        return Response(
            resp.iter_content(chunk_size=8192),
            content_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-cache'
            }
        )
        
    except http_requests.Timeout:
        return jsonify({'message': 'Download timed out'}), 504
    except Exception as e:
        return jsonify({'message': 'Download failed', 'error': str(e)}), 500
