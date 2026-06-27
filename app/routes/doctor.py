from flask import render_template, redirect, url_for, flash, request, Blueprint
from flask_login import login_required, current_user
from app import db
from app.models import Doctor, Availability, Appointment, Patient, User, GlobalSetting
from datetime import datetime, timedelta
from sqlalchemy import func
from app.email_helper import send_html_email, build_skd_email_template, send_doctor_notification

doctor_bp = Blueprint('doctor', __name__)

def doctor_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'doctor':
            flash('Access denied. Doctor only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def create_time_slots(doctor_id, date_str, start_time_str, end_time_str):
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    start_dt = datetime.combine(date, datetime.strptime(start_time_str, '%H:%M').time())
    end_dt = datetime.combine(date, datetime.strptime(end_time_str, '%H:%M').time())
    slot_duration = int(GlobalSetting.get('slot_duration_minutes', 30))
    current = start_dt
    slots = []
    while current + timedelta(minutes=slot_duration) <= end_dt:
        slot_end = current + timedelta(minutes=slot_duration)
        existing = Availability.query.filter_by(doctor_id=doctor_id, slot_start=current).first()
        if not existing:
            slots.append(Availability(doctor_id=doctor_id, slot_start=current, slot_end=slot_end))
        current = slot_end
    db.session.add_all(slots)
    db.session.commit()
    return len(slots)

@doctor_bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('index'))
    
    today = datetime.utcnow().date()
    today_end = datetime.combine(today, datetime.max.time())
    
    pending_requests = db.session.query(Appointment).join(
        Availability, Appointment.availability_id == Availability.id
    ).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == 'pending'
    ).order_by(Availability.slot_start).all()
    
    today_appointments = db.session.query(Appointment).join(
        Availability, Appointment.availability_id == Availability.id
    ).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == 'scheduled',
        func.date(Availability.slot_start) == today
    ).order_by(Availability.slot_start).all()
    
    upcoming_appointments = db.session.query(Appointment).join(
        Availability, Appointment.availability_id == Availability.id
    ).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == 'scheduled',
        Availability.slot_start > today_end
    ).order_by(Availability.slot_start).all()
    
    seen_patients = db.session.query(func.count(func.distinct(Appointment.patient_id))).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(['completed', 'no_show'])
    ).scalar()
    
    patient_records = db.session.query(
        Patient, func.max(Availability.slot_start).label('last_visit')
    ).join(Appointment, Appointment.patient_id == Patient.id).join(
        Availability, Appointment.availability_id == Availability.id
    ).filter(
        Appointment.doctor_id == doctor.id
    ).group_by(Patient.id).order_by(
        func.max(Availability.slot_start).desc()
    ).all()
    
    return render_template(
        'doctor_dashboard.html',
        doctor=doctor,
        pending_requests=pending_requests,
        today_appointments=today_appointments,
        upcoming_appointments=upcoming_appointments,
        seen_patients=seen_patients,
        patient_records=patient_records,
        now=datetime.utcnow()
    )

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
        
        # --- Send confirmation email to patient (HTML) ---
        try:
            patient_email = appointment.patient.user.email
            patient_name = appointment.patient.full_name
            doctor_name = doctor.full_name
            slot_start = appointment.availability.slot_start
            appointment_id_str = appointment.appointment_id
            
            subject = "Appointment Confirmed - SKD Hospital"
            html_content = build_skd_email_template(
                title="Appointment Confirmed",
                greeting_text=f"Dear {patient_name},",
                main_content=f"""
                <p>Your appointment has been confirmed.</p>
                <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
                    <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
                    <p><strong>📅 Date:</strong> {slot_start.strftime('%A, %B %d, %Y')}</p>
                    <p><strong>⏰ Time:</strong> {slot_start.strftime('%I:%M %p')}</p>
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
        appointment.availability.is_booked = False
        appointment.availability.booked_by = None
        db.session.commit()
        flash('Appointment rejected.', 'danger')
        
        # Send rejection email to patient (HTML)
        try:
            patient_email = appointment.patient.user.email
            patient_name = appointment.patient.full_name
            doctor_name = doctor.full_name
            slot_start = appointment.availability.slot_start
            
            subject = "Appointment Rejected - SKD Hospital"
            html_content = build_skd_email_template(
                title="Appointment Rejected",
                greeting_text=f"Dear {patient_name},",
                main_content=f"""
                <p>We regret to inform you that your appointment request has been rejected.</p>
                <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
                    <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
                    <p><strong>📅 Date:</strong> {slot_start.strftime('%A, %B %d, %Y')}</p>
                    <p><strong>⏰ Time:</strong> {slot_start.strftime('%I:%M %p')}</p>
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

@doctor_bp.route('/patient/<int:patient_id>')
@login_required
@doctor_required
def patient_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointments = db.session.query(Appointment).join(
        Availability, Appointment.availability_id == Availability.id
    ).filter(
        Appointment.patient_id == patient_id,
        Appointment.doctor_id == doctor.id
    ).order_by(
        Availability.slot_start.desc()
    ).all()
    if not appointments:
        flash('You do not have access to this patient\'s records.', 'danger')
        return redirect(url_for('doctor.dashboard'))
    
    return render_template('patient_records.html', patient=patient, appointments=appointments)

@doctor_bp.route('/add_availability', methods=['GET', 'POST'])
@login_required
@doctor_required
def add_availability():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        try:
            count = create_time_slots(doctor.id, date, start_time, end_time)
            flash(f'{count} time slots added successfully.', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('doctor.dashboard'))
    slot_duration = GlobalSetting.get('slot_duration_minutes', 30)
    return render_template('add_availability.html', slot_duration=slot_duration)