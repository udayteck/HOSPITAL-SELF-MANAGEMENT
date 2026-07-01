from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Patient, Doctor, EmailVerification
from app.email_helper import send_html_email, build_skd_email_template
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


# ==================== SEND OTP ====================
@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    if not email or not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email address'}), 400

    try:
        otp = EmailVerification.create_otp(email)
        print(f"✅ OTP generated for {email}: {otp}")

        # Send OTP via Brevo
        subject = "Your OTP for SKD Hospital Registration"
        html_content = build_skd_email_template(
            title="OTP Verification",
            greeting_text=f"Dear {email},",
            main_content=f"""
            <p>Your OTP for registration is:</p>
            <h2 style="color: #00ccb0; font-size: 36px; text-align: center; letter-spacing: 4px;">{otp}</h2>
            <p>This OTP is valid for 10 minutes.</p>
            <p>If you didn't request this, please ignore.</p>
            """
        )
        success = send_html_email(email, subject, html_content)
        if success:
            return jsonify({'success': True, 'message': 'OTP sent to your email'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'}), 500

    except Exception as e:
        print(f"❌ OTP error: {e}")
        return jsonify({'success': False, 'message': 'Failed to generate or send OTP.'}), 500


# ==================== VERIFY OTP ====================
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    if not email or not otp:
        return jsonify({'success': False, 'message': 'Email and OTP required'}), 400

    if EmailVerification.verify_otp(email, otp):
        session['verified_email'] = email
        return jsonify({'success': True, 'message': 'OTP verified'})
    else:
        return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400


# ==================== REGISTER ====================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'patient')

        if not email or not password or not full_name:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'danger')
            return render_template('register.html')

        if session.get('verified_email') != email:
            flash('Please verify your email with OTP first.', 'danger')
            return render_template('register.html')

        user = User(email=email, role=role, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == 'patient':
            patient = Patient(user_id=user.id, full_name=full_name)
            db.session.add(patient)

        db.session.commit()
        session.pop('verified_email', None)

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


# ==================== LOGIN ====================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        if not user.is_active:
            flash('Account is disabled.', 'danger')
            return render_template('login.html')

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif user.role == 'receptionist':
            return redirect(url_for('receptionist.dashboard'))
        elif user.role == 'patient':
            return redirect(url_for('patient.dashboard'))
        return redirect(url_for('main.index'))

    return render_template('login.html')


# ==================== LOGOUT ====================
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))