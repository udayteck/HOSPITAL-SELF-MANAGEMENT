import os
from urllib.parse import quote_plus
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ---------- FORCE AIVEN DATABASE URL ----------
    # This ensures the app uses the DATABASE_URL from environment
    # with proper SSL for Aiven
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f"🔗 Using database from environment: {database_url[:50]}...")
    # ---------------------------------------------

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Import models for shell context
    from app.models import User, Patient, Doctor, Appointment, Prescription, GlobalSetting, Insurance, Bill, Receptionist, Availability

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprintsfrom app.routes.main import main_bp as main
    from app.routes.auth import auth_bp
    from app.routes.patient import patient_bp
    from app.routes.doctor import doctor_bp
    from app.routes.receptionist import receptionist_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(receptionist_bp, url_prefix='/receptionist')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Shell context for Flask shell
    @app.shell_context_processor
    def make_shell_context():
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
            'Availability': Availability
        }

    return app