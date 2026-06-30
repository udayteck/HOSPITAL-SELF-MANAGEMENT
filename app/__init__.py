import os
from flask import Flask
from app.extensions import db, migrate, login_manager, mail
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f"🔗 Using database from environment: {database_url[:50]}...")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Import models only inside the function to avoid circular imports
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints (import inside)
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.patient import patient_bp
    from app.routes.doctor import doctor_bp
    from app.routes.receptionist import receptionist_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(receptionist_bp, url_prefix='/receptionist')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Shell context (import models here too)
    @app.shell_context_processor
    def make_shell_context():
        from app.models import (
            User, Patient, Doctor, Appointment, Prescription,
            GlobalSetting, Insurance, Bill, Receptionist,
            Availability, EmailVerification
        )
        return {
            'db': db,
            'User': User,
            'Patient': Patient,
            'Doctor': Doctor,
            'Appointment': Appointment,
            'Prescription': Prescription,
            'GlobalSetting': GlobalSetting,
            'Insurance': Insurance,
            'Bill': Bill,
            'Receptionist': Receptionist,
            'Availability': Availability,
            'EmailVerification': EmailVerification
        }

    return app