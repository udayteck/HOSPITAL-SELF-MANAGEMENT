import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hospital.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Change this line:
BREVO_API_KEY = os.environ.get('BREVO_API_KEY')   # No default value    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'sdkhospital479@gmail.com')