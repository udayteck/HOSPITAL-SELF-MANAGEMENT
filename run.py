import os
from app import create_app, db
from app.models import User, GlobalSetting   # <-- import at top

app = create_app()
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
print(f"🔗 Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")

with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        admin = User(email='admin@hospital.com', role='admin', is_active=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created")
    if not GlobalSetting.query.first():
        GlobalSetting.set('cancellation_hours', '2')
        GlobalSetting.set('slot_duration_minutes', '30')
        GlobalSetting.set('appointment_lead_days', '30')
        print("✅ Default settings created")

if __name__ == '__main__':
    app.run(debug=True)