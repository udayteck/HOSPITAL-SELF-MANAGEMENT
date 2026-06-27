from flask import jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Doctor, Availability, Patient, Appointment, GlobalSetting
from datetime import datetime, timedelta
import uuid
from flask import Blueprint
from flask_mail import Message
from app import mail
from threading import Thread
from flask import current_app
from sqlalchemy import func
from app.email_helper import send_html_email, build_skd_email_template, send_doctor_notification

api_bp = Blueprint('api', __name__)

# ---------- Email helper (plain text fallback – kept for any other uses) ----------
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email_async(recipient, subject, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

# ---------- Get available slots ----------
@api_bp.route('/available_slots/<int:doctor_id>')
def available_slots(doctor_id):
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date required'}), 400
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return jsonify({'error': 'Invalid date format'}), 400

    slots = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        func.date(Availability.slot_start) == target_date,
        Availability.is_booked == False
    ).all()

    slots_data = [{
        'id': s.id,
        'start': s.slot_start.strftime('%H:%M'),
        'end': s.slot_end.strftime('%H:%M')
    } for s in slots]
    return jsonify(slots_data)

# ---------- Book a slot (patient or receptionist) ----------
@api_bp.route('/book', methods=['POST'])
@login_required
def book_slot():
    if current_user.role != 'patient':
        return jsonify({'error': 'Only patients can book'}), 403

    data = request.get_json()
    slot_id = data.get('slot_id')
    reason_visit = data.get('reason', '')
    if not slot_id:
        return jsonify({'error': 'Slot ID required'}), 400

    availability = Availability.query.get(slot_id)
    if not availability or availability.is_booked:
        return jsonify({'error': 'Slot not available'}), 400

    lead_days = int(GlobalSetting.get('appointment_lead_days', 30))
    if availability.slot_start.date() > datetime.utcnow().date() + timedelta(days=lead_days):
        return jsonify({'error': f'Cannot book more than {lead_days} days in advance'}), 400

    patient = Patient.query.filter_by(user_id=current_user.id).first()
    appointment_id = f"APT-{uuid.uuid4().hex[:8].upper()}"
    appointment = Appointment(
        appointment_id=appointment_id,
        patient_id=patient.id,
        doctor_id=availability.doctor_id,
        availability_id=availability.id,
        status='pending',
        reason_visit=reason_visit
    )
    availability.is_booked = True
    availability.booked_by = patient.id
    db.session.add(appointment)
    db.session.commit()

    doctor = availability.doctor

    # 1. Send pending email to patient (HTML)
    subject_pending = "Appointment Request Pending - SKD Hospital"
    html_pending = build_skd_email_template(
        title="Appointment Request Pending",
        greeting_text=f"Dear {patient.full_name},",
        main_content=f"""
        <p>Your appointment request has been sent to the doctor.</p>
        <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
            <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor.full_name}</p>
            <p><strong>📅 Date:</strong> {availability.slot_start.strftime('%A, %B %d, %Y')}</p>
            <p><strong>⏰ Time:</strong> {availability.slot_start.strftime('%I:%M %p')}</p>
            <p><strong>🆔 Request ID:</strong> {appointment_id}</p>
        </div>
        <p>You will receive a confirmation email once the doctor approves your request.</p>
        <p>Thank you for choosing SKD Hospital.</p>
        """
    )
    send_html_email(patient.user.email, subject_pending, html_pending)

    # 2. Send notification to doctor (HTML)
    send_doctor_notification(
        doctor.user.email,
        patient.full_name,
        doctor.full_name,
        availability.slot_start,
        appointment_id
    )

    return jsonify({'success': True, 'appointment_id': appointment_id, 'message': 'Request sent to doctor for confirmation'})