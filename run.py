import os
from app import create_app, db

app = create_app()

# Force database URI from environment
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
print(f"🔗 Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")

# ----- THIS RUNS ON RAILWAY (and locally) -----
with app.app_context():
    # Import models INSIDE the app context
    from app.models import User, GlobalSetting
    
    db.create_all()
    
    # Create admin user if none exists
    if not User.query.filter_by(role='admin').first():
        admin = User(
            email='admin@hospital.com',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created")
    
    # Set default settings if missing
    if not GlobalSetting.query.first():
        GlobalSetting.set('cancellation_hours', '2')
        GlobalSetting.set('slot_duration_minutes', '30')
        GlobalSetting.set('appointment_lead_days', '30')
        print("✅ Default settings created")
# ---------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)