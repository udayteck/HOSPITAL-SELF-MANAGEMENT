import os
from app import create_app, db
from app.models import User, GlobalSetting

app = create_app()

# ---------- FORCE RAILWAY DATABASE ----------
# Override any hardcoded value with the environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
# Print the actual URI being used – check the logs after deployment!
print(f"🔗 Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
# --------------------------------------------

# ----- THIS RUNS ON RAILWAY (and locally) -----
with app.app_context():
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