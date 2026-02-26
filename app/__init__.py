from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import cloudinary
import os
import os
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Trust reverse proxy headers (e.g. from Render)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/victorsprings')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 hours
    
    # Cloudinary configuration
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv('FRONTEND_URL', 'http://localhost:5173').split(','),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Security headers (only in production)
    if os.getenv('FLASK_ENV') == 'production':
        Talisman(
            app, 
            force_https=True,
            content_security_policy=None, # Configure CSP separately if needed
            cross_origin_opener_policy='same-origin-allow-popups' # Required for Google OAuth
        )
    
    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.properties import properties_bp
    from app.api.users import users_bp
    from app.api.payments import payments_bp
    from app.api.visits import visits_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(properties_bp, url_prefix='/api/properties')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(visits_bp, url_prefix='/api/visits')
    
    # Error handlers
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {'message': 'Rate limit exceeded. Please try again later.'}, 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'message': 'Internal server error'}, 500
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'victor-springs-api'}, 200
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app
