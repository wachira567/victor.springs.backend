#!/usr/bin/env python3
"""
Victor Springs Backend Application Runner
"""
import os
from app import create_app, db
from app.models import User, Property, Payment, Document

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Property': Property,
        'Payment': Payment,
        'Document': Document
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
