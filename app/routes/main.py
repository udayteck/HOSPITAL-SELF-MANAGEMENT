from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return "Welcome to SKD Hospital System"

@main_bp.route('/home')
def home():
    return "Home page"