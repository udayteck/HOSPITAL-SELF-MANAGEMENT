from flask import render_template, redirect, url_for, flash, request, Blueprint, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Patient, Doctor, Appointment, Availability, User, Receptionist, Bill
from datetime import datetime
import uuid
from sqlalchemy import func

receptionist_bp = Blueprint('receptionist', __name__)

def receptionist_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'receptionist':
            flash('Access denied. Receptionist only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ---------- Dashboard ----------
@receptionist_bp.route('/dashboard')
@login_required
@receptionist_required
def dashboard():
    return render_template('receptionist_dashboard.html')

# ---------- Create Appointment ----------
@receptionist_bp.route('/create_appointment', methods=['GET', 'POST'])
@login_required
@receptionist_required
def create_appointment():
    if request.method == 'POST':
        patient_email = request.form.get('patient_email')
        doctor_id = request.form.get('doctor_id')
        slot_id = request.form.get('slot_id')
        
        user = User.query.filter_by(email=patient_email).first()
        if not user or user.role != 'patient':
            flash('Patient not found. Please register first.', 'danger')
            return redirect(url_for('receptionist.create_appointment'))
        patient = Patient.query.filter_by(user_id=user.id).first()
        
        availability = Availability.query.get(slot_id)
        if not availability or availability.is_booked:
            flash('Slot not available', 'danger')
            return redirect(url_for('receptionist.create_appointment'))
        
        appointment_id = f"APT-{uuid.uuid4().hex[:8].upper()}"
        appointment = Appointment(
            appointment_id=appointment_id,
            patient_id=patient.id,
            doctor_id=doctor_id,
            availability_id=availability.id,
            status='pending'  # pending until doctor confirms
        )
        availability.is_booked = True
        availability.booked_by = patient.id
        db.session.add(appointment)
        db.session.commit()
        
        # Notify doctor (optional)
        doctor = availability.doctor
        # send_doctor_notification(...) if you have the helper
        
        flash(f'Appointment request sent to doctor for confirmation. ID: {appointment_id}', 'success')
        return redirect(url_for('receptionist.dashboard'))
    
    doctors = Doctor.query.all()
    return render_template('create_appointment.html', doctors=doctors)

# ---------- Verify Appointment ----------
@receptionist_bp.route('/verify_appointment', methods=['GET', 'POST'])
@login_required
@receptionist_required
def verify_appointment():
    appointment = None
    if request.method == 'POST':
        apt_id = request.form.get('appointment_id')
        appointment = Appointment.query.filter_by(appointment_id=apt_id).first()
        if not appointment:
            flash('Appointment not found', 'danger')
    return render_template('verify_appointment.html', appointment=appointment)

# ---------- Get Slots (AJAX) ----------
@receptionist_bp.route('/get_slots/<int:doctor_id>/<date>')
@login_required
@receptionist_required
def get_slots(doctor_id, date):
    target_date = datetime.strptime(date, '%Y-%m-%d').date()
    slots = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        func.date(Availability.slot_start) == target_date,
        Availability.is_booked == False
    ).all()
    slots_data = [{'id': s.id, 'start': s.slot_start.strftime('%H:%M'), 'end': s.slot_end.strftime('%H:%M')} for s in slots]
    return jsonify(slots_data)

# ---------- Bills Management (NEW) ----------
@receptionist_bp.route('/bills')
@login_required
@receptionist_required
def manage_bills():
    bills = Bill.query.order_by(Bill.created_at.desc()).all()
    total_amount = sum(b.amount for b in bills)
    pending_amount = sum(b.amount for b in bills if b.status == 'Pending')
    paid_amount = sum(b.amount for b in bills if b.status == 'Paid')
    overdue_amount = sum(b.amount for b in bills if b.status == 'Overdue')
    return render_template('manage_bills.html',
                         bills=bills,
                         total_amount=total_amount,
                         pending_amount=pending_amount,
                         paid_amount=paid_amount,
                         overdue_amount=overdue_amount)

@receptionist_bp.route('/bills/generate', methods=['GET', 'POST'])
@login_required
@receptionist_required
def generate_bill():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        appointment_id = request.form.get('appointment_id')
        amount = float(request.form.get('amount'))
        items = request.form.get('items')
        status = request.form.get('status', 'Pending')
        
        patient = Patient.query.get(patient_id)
        if not patient:
            flash('Patient not found', 'danger')
            return redirect(url_for('receptionist.generate_bill'))
        
        bill_number = f"BILL-{datetime.utcnow().strftime('%Y%m%d')}-{Bill.query.count() + 1}"
        bill = Bill(
            bill_number=bill_number,
            patient_id=patient_id,
            appointment_id=appointment_id if appointment_id else None,
            amount=amount,
            items=items,
            status=status,
            created_by=current_user.id
        )
        db.session.add(bill)
        db.session.commit()
        flash(f'Bill {bill_number} generated successfully', 'success')
        return redirect(url_for('receptionist.manage_bills'))
    
    patients = Patient.query.all()
    appointments = Appointment.query.filter_by(status='scheduled').all()
    return render_template('bill_form.html', patients=patients, appointments=appointments, title='Generate New Bill - Receptionist')

@receptionist_bp.route('/bills/view/<int:bill_id>')
@login_required
@receptionist_required
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('bill_details.html', bill=bill)

@receptionist_bp.route('/bills/edit/<int:bill_id>', methods=['GET', 'POST'])
@login_required
@receptionist_required
def edit_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        appointment_id = request.form.get('appointment_id')
        amount = float(request.form.get('amount'))
        items = request.form.get('items')
        status = request.form.get('status')
        
        patient = Patient.query.get(patient_id)
        if not patient:
            flash('Patient not found', 'danger')
            return redirect(url_for('receptionist.edit_bill', bill_id=bill.id))
        
        bill.patient_id = patient_id
        bill.appointment_id = appointment_id if appointment_id else None
        bill.amount = amount
        bill.items = items
        bill.status = status
        db.session.commit()
        
        flash('Bill updated successfully!', 'success')
        return redirect(url_for('receptionist.view_bill', bill_id=bill.id))
    
    patients = Patient.query.all()
    appointments = Appointment.query.filter_by(status='scheduled').all()
    return render_template('bill_edit.html', bill=bill, patients=patients, appointments=appointments)