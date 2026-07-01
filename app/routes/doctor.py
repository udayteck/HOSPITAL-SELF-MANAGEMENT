from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Appointment, Patient, Doctor, Prescription, User, GlobalSetting
from app.email_helper import send_html_email, build_skd_email_template
from datetime import datetime, timedelta
from sqlalchemy import func

doctor_bp = Blueprint('doctor', __name__)

def doctor_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'doctor':
            flash('Doctor access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


# ============================
# DASHBOARD
# ============================
@doctor_bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('main.index'))

    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    # --- Pending Requests ---
    pending_requests = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == 'pending'
    ).order_by(Appointment.date, Appointment.start_time).all()

    # --- Today's Appointments ---
    today_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date == today,
        Appointment.status == 'scheduled'
    ).order_by(Appointment.start_time).all()

    # --- Upcoming Appointments (next 7 days) ---
    next_week = today + timedelta(days=7)
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date >= today,
        Appointment.date <= next_week,
        Appointment.status == 'scheduled'
    ).order_by(Appointment.date, Appointment.start_time).all()

    # --- Statistics ---
    total_patients = db.session.query(func.count(db.distinct(Appointment.patient_id))).filter(
        Appointment.doctor_id == doctor.id
    ).scalar()

    total_appointments = Appointment.query.filter_by(doctor_id=doctor.id).count()
    completed_appointments = Appointment.query.filter_by(doctor_id=doctor.id, status='completed').count()
    pending_count = Appointment.query.filter_by(doctor_id=doctor.id, status='pending').count()

    # Seen patients (completed or no-show)
    seen_patients = db.session.query(func.count(func.distinct(Appointment.patient_id))).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(['completed', 'no_show'])
    ).scalar()

    # Recent patients (last 10 unique patients)
    recent_patients = db.session.query(Patient).join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).order_by(Appointment.created_at.desc()).limit(10).all()

    # Patient records with last visit date
    patient_records = db.session.query(
        Patient, func.max(Appointment.date).label('last_visit')
    ).join(Appointment, Appointment.patient_id == Patient.id).filter(
        Appointment.doctor_id == doctor.id
    ).group_by(Patient.id).order_by(
        func.max(Appointment.date).desc()
    ).all()

    # Monthly appointment count for the last 6 months (chart)
    monthly_labels = []
    monthly_counts = []
    for i in range(5, -1, -1):
        month = today.replace(day=1) - timedelta(days=i*30)
        month_start = month.replace(day=1)
        if month.month == 12:
            month_end = month.replace(day=31)
        else:
            month_end = month.replace(month=month.month+1, day=1) - timedelta(days=1)
        count = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date >= month_start,
            Appointment.date <= month_end
        ).count()
        monthly_labels.append(month.strftime('%b'))
        monthly_counts.append(count)

    return render_template(
        'doctor_dashboard.html',
        doctor=doctor,
        pending_requests=pending_requests,
        today_appointments=today_appointments,
        upcoming_appointments=upcoming_appointments,
        total_patients=total_patients,
        total_appointments=total_appointments,
        completed_appointments=completed_appointments,
        pending_count=pending_count,
        seen_patients=seen_patients,
        recent_patients=recent_patients,
        patient_records=patient_records,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts,
        now=datetime.utcnow()
    )


# ============================
# ACCEPT APPOINTMENT
# ============================
@doctor_bp.route('/appointment/<int:appointment_id>/accept', methods=['POST'])
@login_required
@doctor_required
def accept_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    if appointment.status != 'pending':
        flash('This appointment has already been processed.', 'warning')
        return redirect(url_for('doctor.dashboard'))

    appointment.status = 'scheduled'
    db.session.commit()

    # Send confirmation email to patient
    try:
        patient_email = appointment.patient.user.email
        patient_name = appointment.patient.full_name
        doctor_name = doctor.full_name
        appointment_date = appointment.date.strftime('%A, %B %d, %Y')
        appointment_time = appointment.start_time.strftime('%I:%M %p')

        subject = "✅ Appointment Confirmed - SKD Hospital"
        html_content = build_skd_email_template(
            title="Appointment Confirmed",
            greeting_text=f"Dear {patient_name},",
            main_content=f"""
            <p>Great news! Your appointment has been <strong>confirmed</strong> by Dr. {doctor_name}.</p>
            <div style="background: #0f172a; border-left: 5px solid #00ccb0; border-radius: 8px; padding: 16px; margin: 24px 0;">
                <p><strong>🆔 Appointment ID:</strong> {appointment.reference}</p>
                <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
                <p><strong>📅 Date:</strong> {appointment_date}</p>
                <p><strong>⏰ Time:</strong> {appointment_time}</p>
            </div>
            <p>Please arrive 10 minutes before your scheduled time.</p>
            <p>Thank you for choosing SKD Hospital.</p>
            """
        )
        send_html_email(patient_email, subject, html_content)
        print(f"✅ Confirmation email sent to {patient_email}")
    except Exception as e:
        print(f"❌ Failed to send confirmation email: {e}")

    flash('Appointment confirmed. Patient has been notified.', 'success')
    return redirect(url_for('doctor.dashboard'))


# ============================
# REJECT APPOINTMENT
# ============================
@doctor_bp.route('/appointment/<int:appointment_id>/reject', methods=['POST'])
@login_required
@doctor_required
def reject_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    if appointment.status != 'pending':
        flash('This appointment has already been processed.', 'warning')
        return redirect(url_for('doctor.dashboard'))

    appointment.status = 'cancelled'
    db.session.commit()

    # Send rejection email to patient
    try:
        patient_email = appointment.patient.user.email
        patient_name = appointment.patient.full_name
        doctor_name = doctor.full_name
        appointment_date = appointment.date.strftime('%A, %B %d, %Y')
        appointment_time = appointment.start_time.strftime('%I:%M %p')

        subject = "❌ Appointment Rejected - SKD Hospital"
        html_content = build_skd_email_template(
            title="Appointment Rejected",
            greeting_text=f"Dear {patient_name},",
            main_content=f"""
            <p>We regret to inform you that your appointment request has been <strong>rejected</strong> by Dr. {doctor_name}.</p>
            <div style="background: #0f172a; border-left: 5px solid #ef4444; border-radius: 8px; padding: 16px; margin: 24px 0;">
                <p><strong>🆔 Appointment ID:</strong> {appointment.reference}</p>
                <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
                <p><strong>📅 Date:</strong> {appointment_date}</p>
                <p><strong>⏰ Time:</strong> {appointment_time}</p>
            </div>
            <p>Please book another slot or contact us for assistance.</p>
            <p>Thank you for choosing SKD Hospital.</p>
            """
        )
        send_html_email(patient_email, subject, html_content)
        print(f"✅ Rejection email sent to {patient_email}")
    except Exception as e:
        print(f"❌ Failed to send rejection email: {e}")

    flash('Appointment rejected. Patient has been notified.', 'danger')
    return redirect(url_for('doctor.dashboard'))


# ============================
# LEGACY APPOINTMENT ROUTES (Keep for compatibility)
# ============================
@doctor_bp.route('/appointment/<int:appointment_id>/update', methods=['POST'])
@login_required
@doctor_required
def update_appointment_status(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('doctor.dashboard'))

    new_status = request.form.get('status')
    if new_status in ['completed', 'no_show']:
        appointment.status = new_status
        db.session.commit()
        flash(f'Appointment marked as {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('doctor.dashboard'))


@doctor_bp.route('/appointment/<int:appointment_id>/respond', methods=['POST'])
@login_required
@doctor_required
def respond_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('doctor.dashboard'))

    action = request.form.get('action')
    if action == 'confirm':
        appointment.status = 'scheduled'
        db.session.commit()
        flash('Appointment confirmed.', 'success')

        try:
            patient_email = appointment.patient.user.email
            patient_name = appointment.patient.full_name
            doctor_name = doctor.full_name
            appointment_date = appointment.date.strftime('%A, %B %d, %Y')
            appointment_time = appointment.start_time.strftime('%I:%M %p')
            appointment_id_str = f"APT{appointment.id:06d}"

            subject = "Appointment Confirmed - SKD Hospital"
            html_content = build_skd_email_template(
                title="Appointment Confirmed",
                greeting_text=f"Dear {patient_name},",
                main_content=f"""
                <p>Your appointment has been confirmed.</p>
                <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
                    <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
                    <p><strong>📅 Date:</strong> {appointment_date}</p>
                    <p><strong>⏰ Time:</strong> {appointment_time}</p>
                    <p><strong>🆔 Appointment ID:</strong> {appointment_id_str}</p>
                </div>
                <p>Thank you for choosing SKD Hospital.</p>
                """
            )
            send_html_email(patient_email, subject, html_content)
            print(f"✅ Confirmation email sent to {patient_email}")
        except Exception as e:
            print(f"❌ Failed to send confirmation email: {e}")
            flash('Appointment confirmed but email could not be sent.', 'warning')

    elif action == 'reject':
        appointment.status = 'cancelled'
        db.session.commit()
        flash('Appointment rejected.', 'danger')

        try:
            patient_email = appointment.patient.user.email
            patient_name = appointment.patient.full_name
            doctor_name = doctor.full_name
            appointment_date = appointment.date.strftime('%A, %B %d, %Y')
            appointment_time = appointment.start_time.strftime('%I:%M %p')

            subject = "Appointment Rejected - SKD Hospital"
            html_content = build_skd_email_template(
                title="Appointment Rejected",
                greeting_text=f"Dear {patient_name},",
                main_content=f"""
                <p>We regret to inform you that your appointment request has been rejected.</p>
                <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
                    <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
                    <p><strong>📅 Date:</strong> {appointment_date}</p>
                    <p><strong>⏰ Time:</strong> {appointment_time}</p>
                </div>
                <p>Please book another slot.</p>
                <p>Thank you for choosing SKD Hospital.</p>
                """
            )
            send_html_email(patient_email, subject, html_content)
            print(f"✅ Rejection email sent to {patient_email}")
        except Exception as e:
            print(f"❌ Failed to send rejection email: {e}")
            flash('Appointment rejected but email could not be sent.', 'warning')
    else:
        flash('Invalid action.', 'danger')

    return redirect(url_for('doctor.dashboard'))


# ============================
# VIEW APPOINTMENT DETAILS
# ============================
@doctor_bp.route('/appointment/<int:appointment_id>/view')
@login_required
@doctor_required
def view_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('doctor.dashboard'))
    return render_template('doctor_view_appointment.html', appointment=appointment)


# ============================
# PATIENT RECORDS
# ============================
@doctor_bp.route('/patient/<int:patient_id>')
@login_required
@doctor_required
def patient_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.doctor_id == doctor.id
    ).order_by(Appointment.date.desc(), Appointment.start_time.desc()).all()

    if not appointments:
        flash('You do not have access to this patient\'s records.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    return render_template('patient_records.html', patient=patient, appointments=appointments)


# ============================
# ADD AVAILABILITY (Placeholder)
# ============================
@doctor_bp.route('/add_availability', methods=['GET', 'POST'])
@login_required
@doctor_required
def add_availability():
    flash('Availability management is not implemented yet.', 'info')
    return redirect(url_for('doctor.dashboard'))


# ============================
# APPOINTMENTS LIST
# ============================
@doctor_bp.route('/appointments')
@login_required
@doctor_required
def appointments():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('main.index'))
    all_appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.date.desc()).all()
    return render_template('doctor_appointments.html', appointments=all_appointments)


# ============================
# PATIENTS LIST
# ============================
@doctor_bp.route('/patients')
@login_required
@doctor_required
def patients():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('main.index'))
    all_patients = db.session.query(Patient).join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    return render_template('doctor_patients.html', patients=all_patients)


# ============================
# PRESCRIPTIONS LIST
# ============================
@doctor_bp.route('/prescriptions')
@login_required
@doctor_required
def prescriptions():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('main.index'))
    all_prescriptions = Prescription.query.filter_by(doctor_id=doctor.id).order_by(Prescription.created_at.desc()).all()
    return render_template('doctor_prescriptions.html', prescriptions=all_prescriptions)