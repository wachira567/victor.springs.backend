from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    users = User.query.all()
    updated = 0
    for u in users:
        if u.role:
            valid_roles = ['super_admin', 'admin', 'landlord', 'tenant']
            normalized = str(u.role).strip().lower()
            if normalized == 'super admin':
                normalized = 'super_admin'
            elif normalized not in valid_roles:
                normalized = 'tenant' # fallback
            
            if u.role != normalized:
                print(f"Fixing role for user {u.email}: {u.role} -> {normalized}")
                u.role = normalized
                updated += 1
    
    if updated > 0:
        db.session.commit()
        print(f"Updated {updated} user roles.")
    else:
        print("All roles are valid.")
