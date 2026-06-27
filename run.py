from app import create_app, db
from app.models import User, GlobalSetting

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'GlobalSetting': GlobalSetting}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin if none exists
        if not User.query.filter_by(role='admin').first():
            admin = User(email='admin@hospital.com', role='admin', is_active=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        # Set default settings if missing
        if not GlobalSetting.query.first():
            GlobalSetting.set('cancellation_hours', '2')
            GlobalSetting.set('slot_duration_minutes', '30')
            GlobalSetting.set('appointment_lead_days', '30')
    app.run(debug=True)