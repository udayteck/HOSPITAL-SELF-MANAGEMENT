from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db
from app.models import (
    User, Patient, Doctor, Appointment, Prescription,
    GlobalSetting, Bill, Insurance, Availability
)
from app.email_helper import send_html_email, build_skd_email_template

patient_bp = Blueprint('patient', __name__)

def patient_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'patient':
            flash('Patient access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))

    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'scheduled',
        Appointment.date >= datetime.now().date()
    ).order_by(Appointment.date, Appointment.start_time).all()

    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status.in_(['completed', 'cancelled'])
    ).order_by(Appointment.date.desc()).all()

    pending_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'pending'
    ).all()

    total_appointments = Appointment.query.filter_by(patient_id=patient.id).count()
    total_bills = Bill.query.filter_by(patient_id=patient.id).count()
    unpaid_bills = Bill.query.filter_by(patient_id=patient.id, status='pending').count()

    return render_template(
        'patient_dashboard.html',
        patient=patient,
        upcoming_appointments=upcoming_appointments,
        past_appointments=past_appointments,
        pending_appointments=pending_appointments,
        total_appointments=total_appointments,
        total_bills=total_bills,
        unpaid_bills=unpaid_bills
    )


@patient_bp.route('/appointments')
@login_required
@patient_required
def appointments():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))

    all_appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.date.desc(), Appointment.start_time.desc()
    ).all()
    return render_template('patient_appointments.html', appointments=all_appointments)


@patient_bp.route('/api/available_slots/<int:doctor_id>')
@login_required
@patient_required
def api_available_slots(doctor_id):
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date required'}), 400
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    slots = Availability.get_available_slots(doctor_id, date)
    result = [{'start': s['start'], 'end': s['end']} for s in slots]
    return jsonify(result)


@patient_bp.route('/book', methods=['GET', 'POST'])
@login_required
@patient_required
def book_appointment():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        notes = request.form.get('notes', '')

        if not doctor_id or not date_str or not start_time_str:
            flash('Please select doctor, date, and time.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        available_slots = Availability.get_available_slots(doctor_id, date)
        slot_found = any(s['start_obj'] == start_time for s in available_slots)
        if not slot_found:
            flash('Selected slot is not available.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date,
            start_time=start_time,
            status='scheduled'
        ).first()
        if existing:
            flash('This slot was just booked by someone else. Please choose another.', 'danger')
            return redirect(url_for('patient.book_appointment'))

        slot_duration = int(GlobalSetting.get('slot_duration_minutes', 30))
        end_time = (datetime.combine(date, start_time) + timedelta(minutes=slot_duration)).time()

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status='pending',
            notes=notes
        )
        db.session.add(appointment)
        db.session.commit()

        # Notify doctor (optional)
        try:
            doctor = Doctor.query.get(doctor_id)
            if doctor and doctor.user.email:
                subject = f"New Appointment Request from {patient.full_name}"
                html = build_skd_email_template(
                    title="New Appointment Request",
                    greeting_text=f"Dear Dr. {doctor.full_name},",
                    main_content=f"""
                    <p>A new appointment has been requested by <strong>{patient.full_name}</strong>.</p>
                    <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
                        <p><strong>📅 Date:</strong> {date.strftime('%A, %B %d, %Y')}</p>
                        <p><strong>⏰ Time:</strong> {start_time.strftime('%I:%M %p')}</p>
                        <p><strong>📝 Notes:</strong> {appointment.notes or 'None'}</p>
                    </div>
                    <p>Please login to confirm or reject this request.</p>
                    """
                )
                send_html_email(doctor.user.email, subject, html)
        except Exception as e:
            print(f"⚠️ Failed to send notification to doctor: {e}")

        flash('Appointment request sent! Please wait for doctor confirmation.', 'success')
        return redirect(url_for('patient.dashboard'))

    # GET
    doctors = Doctor.query.all()
    slot_duration = int(GlobalSetting.get('slot_duration_minutes', 30))
    return render_template(
        'book_appointment.html',
        doctors=doctors,
        slot_duration=slot_duration,
        now=datetime.now()
    )


@patient_bp.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@patient_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if appointment.patient_id != patient.id:
        abort(403)

    if appointment.status in ['completed', 'cancelled']:
        flash('This appointment cannot be cancelled.', 'warning')
        return redirect(url_for('patient.dashboard'))

    now = datetime.now()
    appointment_datetime = datetime.combine(appointment.date, appointment.start_time)
    hours_diff = (appointment_datetime - now).total_seconds() / 3600
    cancellation_hours = int(GlobalSetting.get('cancellation_hours', 2))
    if hours_diff < cancellation_hours:
        flash(f'Appointments can only be cancelled at least {cancellation_hours} hours in advance.', 'danger')
        return redirect(url_for('patient.dashboard'))

    appointment.status = 'cancelled'
    db.session.commit()
    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('patient.dashboard'))


@patient_bp.route('/appointment/<int:appointment_id>')
@login_required
@patient_required
def view_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if appointment.patient_id != patient.id:
        abort(403)

    return render_template('patient_appointment_details.html', appointment=appointment)


@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def profile():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        patient.full_name = request.form.get('full_name', patient.full_name)
        patient.phone = request.form.get('phone', patient.phone)
        patient.address = request.form.get('address', patient.address)
        patient.emergency_contact = request.form.get('emergency_contact', patient.emergency_contact)
        patient.blood_group = request.form.get('blood_group', patient.blood_group)
        patient.allergies = request.form.get('allergies', patient.allergies)
        patient.medical_history = request.form.get('medical_history', patient.medical_history)
        dob_str = request.form.get('date_of_birth')
        if dob_str:
            try:
                patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'danger')
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('patient.profile'))

    return render_template('patient_profile.html', patient=patient)


@patient_bp.route('/prescriptions')
@login_required
@patient_required
def prescriptions():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))

    all_prescriptions = Prescription.query.filter_by(patient_id=patient.id).order_by(
        Prescription.created_at.desc()
    ).all()
    return render_template('patient_prescriptions.html', prescriptions=all_prescriptions)


@patient_bp.route('/bills')
@login_required
@patient_required
def bills():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))

    all_bills = Bill.query.filter_by(patient_id=patient.id).order_by(Bill.created_at.desc()).all()
    return render_template('patient_bills.html', bills=all_bills)


@patient_bp.route('/bill/<int:bill_id>/pay', methods=['POST'])
@login_required
@patient_required
def pay_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if bill.patient_id != patient.id:
        abort(403)

    if bill.status.lower() == 'paid':
        flash('This bill is already paid.', 'info')
        return redirect(url_for('patient.bills'))

    bill.status = 'paid'
    bill.paid_at = datetime.utcnow()
    db.session.commit()
    flash('Bill paid successfully (simulated).', 'success')
    return redirect(url_for('patient.bills'))