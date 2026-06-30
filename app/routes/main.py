from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Later you can render a custom home page, but for now base.html is enough
    return render_template('base.html')