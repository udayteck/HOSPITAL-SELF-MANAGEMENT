from flask import render_template, redirect, url_for, flash, request, jsonify, Blueprint
from flask_login import login_required, current_user
from app import db
from app.models import Patient, Doctor, Appointment, Availability, User, GlobalSetting, Insurance
from datetime import datetime, timedelta
import uuid
from app.email_helper import send_html_email, build_skd_email_template

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'patient':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    upcoming = Appointment.query.filter_by(patient_id=patient.id, status='scheduled')\
        .join(Availability).filter(Availability.slot_start > datetime.utcnow()).all()
    past = Appointment.query.filter_by(patient_id=patient.id, status='scheduled')\
        .join(Availability).filter(Availability.slot_start <= datetime.utcnow()).all()
    cancelled = Appointment.query.filter_by(patient_id=patient.id, status='cancelled').all()
    return render_template('patient_dashboard.html', upcoming=upcoming, past=past, cancelled=cancelled)

@patient_bp.route('/doctors')
@login_required
def view_doctors():
    doctors = Doctor.query.all()
    return render_template('doctors_list.html', doctors=doctors)

@patient_bp.route('/book/<int:doctor_id>')
@login_required
def book_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    today = datetime.utcnow().date()
    lead_days = int(GlobalSetting.get('appointment_lead_days', 30))
    max_date = today + timedelta(days=lead_days)
    return render_template('book_appointment.html', doctor=doctor, today=today.isoformat(), max_date=max_date.isoformat())

@patient_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != patient.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('patient.dashboard'))
    cancellation_hours = int(GlobalSetting.get('cancellation_hours', 2))
    slot_start = appointment.availability.slot_start
    if slot_start - datetime.utcnow() < timedelta(hours=cancellation_hours):
        flash(f'Appointments can only be cancelled at least {cancellation_hours} hours before the slot.', 'danger')
        return redirect(url_for('patient.dashboard'))
    
    cancel_reason = request.form.get('cancel_reason', 'Not specified')
    appointment.cancel_reason = cancel_reason
    appointment.status = 'cancelled'
    appointment.availability.is_booked = False
    appointment.availability.booked_by = None
    db.session.commit()
    
    # Send cancellation email (HTML)
    subject = "Appointment Cancelled - SKD Hospital"
    html_content = build_skd_email_template(
        title="Appointment Cancellation",
        greeting_text=f"Dear {patient.full_name},",
        main_content=f"""
        <p>Your appointment has been cancelled.</p>
        <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
            <p><strong>Doctor:</strong> Dr. {appointment.doctor.full_name}</p>
            <p><strong>Date:</strong> {slot_start.strftime('%A, %B %d, %Y')}</p>
            <p><strong>Time:</strong> {slot_start.strftime('%I:%M %p')}</p>
            <p><strong>Reason:</strong> {cancel_reason}</p>
        </div>
        <p>If you would like to book another appointment, please visit our patient portal.</p>
        """,
        button_text="Book New Appointment",
        button_link=url_for('patient.view_doctors', _external=True)
    )
    send_html_email(current_user.email, subject, html_content)
    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('patient.dashboard'))

# ========== INSURANCE ROUTES ==========
@patient_bp.route('/insurance')
@login_required
def view_insurance():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    insurance = Insurance.query.filter_by(patient_id=patient.id).first()
    return render_template('patient_insurance.html', insurance=insurance)

@patient_bp.route('/insurance/edit', methods=['GET', 'POST'])
@login_required
def edit_insurance():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    insurance = Insurance.query.filter_by(patient_id=patient.id).first()
    if request.method == 'POST':
        provider_name = request.form.get('provider_name')
        policy_number = request.form.get('policy_number')
        group_number = request.form.get('group_number')
        coverage_details = request.form.get('coverage_details')
        expiration_date = request.form.get('expiration_date')
        primary_holder_name = request.form.get('primary_holder_name')
        relationship = request.form.get('relationship')
        is_active = request.form.get('is_active') == 'on'

        if not provider_name or not policy_number:
            flash('Provider name and policy number are required.', 'danger')
            return redirect(url_for('patient.edit_insurance'))

        if insurance:
            insurance.provider_name = provider_name
            insurance.policy_number = policy_number
            insurance.group_number = group_number
            insurance.coverage_details = coverage_details
            insurance.expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d').date() if expiration_date else None
            insurance.primary_holder_name = primary_holder_name
            insurance.relationship = relationship
            insurance.is_active = is_active
            insurance.updated_at = datetime.utcnow()
        else:
            insurance = Insurance(
                patient_id=patient.id,
                provider_name=provider_name,
                policy_number=policy_number,
                group_number=group_number,
                coverage_details=coverage_details,
                expiration_date=datetime.strptime(expiration_date, '%Y-%m-%d').date() if expiration_date else None,
                primary_holder_name=primary_holder_name,
                relationship=relationship,
                is_active=is_active
            )
            db.session.add(insurance)
        db.session.commit()
        flash('Insurance details saved successfully.', 'success')
        return redirect(url_for('patient.view_insurance'))

    return render_template('edit_insurance.html', insurance=insurance)