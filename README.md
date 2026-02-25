# Victor Springs Backend ⚙️

Welcome to the backend repository of the Victor Springs real estate application! This RESTful API serves as the core data layer for the platform, handling everything from user authentication to property management and scheduled viewings.

It is built on a robust Python/Flask foundation with a PostgreSQL database.

## 🚀 Technologies Used
- **Language:** Python 3.8+
- **Framework:** Flask & Flask-RESTful
- **Database:** PostgreSQL (hosted on Neon)
- **ORM:** SQLAlchemy & Flask-Migrate
- **Authentication:** Flask-JWT-Extended & Google OAuth2
- **Email Delivery:** Resend
- **Token Security:** ItsDangerous

## ✨ Key Features
- **Role-Based Access Control:** Distinct permission levels for `admin`, `landlord`, and `tenant` roles using custom decorators.
- **Hybrid Authentication:** Supports both traditional local username/password and Google Single Sign-on via token exchange.
- **Magic Links:** Implements fully secure, URL-safe magic links for Email Verification and Password Reset workflows.
- **Robust Relational Data:** Manages relationships between users, properties, applications, visits (viewings), and property inquiries.
- **Cloudinary Integration:** Ready to handle property image uploads directly or via the frontend signed-url mechanism.

## 📦 Project Setup

### Prerequisites
Make sure you have Python 3.8 or higher, `pip`, and `git` installed.

### 1. Clone the repository
```bash
git clone git@github.com:wachira567/victor.springs.backend.git
cd victor.springs.backend
```

### 2. Set up the Environment
It is highly recommended to use a virtual environment.
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file at the root of the project with your secrets:

```env
# Database
DATABASE_URL=postgresql://user:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# JWT Secret Keys
JWT_SECRET_KEY=your_super_secret_jwt_key
SECRET_KEY=your_flask_secret_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com

# Resend Mailer
RESEND_API_KEY=re_123456789...
FRONTEND_URL=http://localhost:5173
```

### 5. Running Database Migrations
The Victor Springs backend uses Flask-Migrate to maintain schema parity. If the database schema isn't fully created:
```bash
flask db upgrade
```

### 6. Start the Server
```bash
python app.py
```
The application will launch in development mode, typically accessible at `http://localhost:5000`.

## 📂 Project Structure
```
backend/
├── app/
│   ├── api/             # Flask Blueprints mapping endpoints to auth/users/properties
│   ├── models/          # SQLAlchemy definitions (User, Property, Visit, Identity)
│   ├── utils/           # Helper scripts (email.py, validators.py, sanitizers.py)
│   └── __init__.py      # App factory and configuration layer
├── migrations/          # Alembic auto-generated database migrations
├── .env                 # Secret keys (do not commit!)
├── requirements.txt     # Python package dependencies
└── app.py               # Application entry point
```

## 🤝 Contribution Guidelines
When making PRs, ensure that you run the application to verify that the API endpoints respond correctly. Make sure any new models are captured by running `flask db migrate -m "message"`.
