import bleach
import re

def sanitize_string(text, allowed_tags=None):
    """Sanitize a string by removing HTML tags and stripping whitespace"""
    if text is None:
        return ''
    
    if allowed_tags:
        # Allow specific HTML tags
        text = bleach.clean(text, tags=allowed_tags, strip=True)
    else:
        # Remove all HTML tags
        text = bleach.clean(text, tags=[], strip=True)
    
    return text.strip()

def sanitize_html(html, allowed_tags=None):
    """Sanitize HTML content with allowed tags"""
    if html is None:
        return ''
    
    if allowed_tags is None:
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li']
    
    allowed_attributes = {}
    
    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attributes, strip=True)

def sanitize_filename(filename):
    """Sanitize a filename by removing special characters"""
    if not filename:
        return ''
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove special characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
    
    return filename

def sanitize_search_query(query):
    """Sanitize search query by removing special characters"""
    if not query:
        return ''
    
    # Remove SQL injection risky characters
    query = re.sub(r'[;\'"\\]', '', query)
    
    # Limit length
    query = query[:200]
    
    return query.strip()
