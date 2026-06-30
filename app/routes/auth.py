from flask import render_template, redirect, url_for, flash, request, jsonify, session, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
from app import db, mail
from app.models import User, Patient, EmailVerification
from app.forms import RegistrationForm, LoginForm
from app.email_helper import send_html_email, build_skd_email_template   # <-- NEW IMPORT
from datetime import datetime, timedelta
import random
from threading import Thread
from flask_mail import Message

auth_bp = Blueprint('auth', __name__)

# ---------- Helper: send plain email (fallback, not used anymore) ----------
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email_async(recipient, subject, body):
    from flask import current_app
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

# ---------- OTP routes (with HTML email) ----------
@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Email required'}), 400
    
    # Check if email already registered
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    # Generate OTP
    otp = EmailVerification.generate_otp()
    # Delete any previous unused OTPs for this email
    EmailVerification.query.filter_by(email=email, is_used=False).delete()
    
    # Save new OTP
    expiry = datetime.utcnow() + timedelta(minutes=10)
    verification = EmailVerification(email=email, otp=otp, expires_at=expiry)
    db.session.add(verification)
    db.session.commit()
    
    # ---------- ATTRACTIVE HTML OTP EMAIL ----------
    subject = "Your OTP for SKD Hospital Registration"
    html_content = build_skd_email_template(
        title="Email Verification",
        greeting_text="Hello,",
        main_content=f"""
        <p>You requested to register at SKD Hospital. Use the OTP below to verify your email address.</p>
        <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0; text-align: center;">
            <p style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #0f766e;">{otp}</p>
            <p style="color: #0f766e;">This OTP is valid for 10 minutes.</p>
        </div>
        <p>If you did not request this, please ignore this email.</p>
        """
    )
    # Send HTML email (asynchronous)
    try:
        send_html_email(email, subject, html_content)
        print(f"✅ OTP HTML email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send HTML email: {e}")
        # Fallback: print OTP to console for development
        print(f"\n🔐 OTP for {email}: {otp}\n")
    
    return jsonify({'success': True, 'message': 'OTP sent to your email'})

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    if not email or not otp:
        return jsonify({'success': False, 'message': 'Email and OTP required'}), 400
    
    if EmailVerification.is_valid(email, otp):
        # Store verified email in session temporarily
        session['verified_email'] = email
        return jsonify({'success': True, 'message': 'OTP verified'})
    else:
        return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400

# ---------- Regular routes ----------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        print("🔍 Registration POST received")
        verified_email = session.get('verified_email')
        print(f"Verified email from session: {verified_email}")
        if not verified_email:
            flash('Please verify your email first.', 'danger')
            return redirect(url_for('auth.register'))

        form = RegistrationForm()
        if form.validate_on_submit():
            print(f"Form valid. Email: {form.email.data}, Name: {form.full_name.data}")
            if form.email.data != verified_email:
                flash('Email mismatch. Please re-verify.', 'danger')
                return redirect(url_for('auth.register'))

            # Create user
            user = User(email=form.email.data, role='patient', is_active=True)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            print(f"User created with id: {user.id}")

            patient = Patient(
                user_id=user.id,
                full_name=form.full_name.data,
                phone=form.phone.data
            )
            db.session.add(patient)
            db.session.commit()
            print("Patient profile created")

            session.pop('verified_email', None)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            print(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}", 'danger')
        return render_template('register.html', form=form)

    form = RegistrationForm()
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        # Manual extraction from request (bypass WTForms for debug)
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        print(f"🔍 Login attempt: email={email}, password length={len(password)}")

        user = User.query.filter_by(email=email).first()
        if user:
            print(f"✅ User found: {user.email}, role={user.role}, active={user.is_active}")
            print(f"🔑 Password check: {user.check_password(password)}")
            if user.check_password(password) and user.is_active:
                login_user(user)
                flash('Login successful!', 'success')
                if user.role == 'patient':
                    return redirect(url_for('patient.dashboard'))
                elif user.role == 'doctor':
                    return redirect(url_for('doctor.dashboard'))
                elif user.role == 'receptionist':
                    return redirect(url_for('receptionist.dashboard'))
                elif user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
        else:
            print("❌ No user with that email.")

        flash('Invalid email or password.', 'danger')
        return render_template('login.html')

    # GET request – show login form
    return render_template('login.html')
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))