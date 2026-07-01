from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Appointment, Patient, Doctor, User, Availability, Bill
from datetime import datetime, timedelta
from sqlalchemy import func

receptionist_bp = Blueprint('receptionist', __name__)

def receptionist_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'receptionist':
            flash('Receptionist access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


# ============================
# DASHBOARD
# ============================
@receptionist_bp.route('/dashboard')
@login_required
@receptionist_required
def dashboard():
    today = datetime.now().date()
    appointments = Appointment.query.filter(
        Appointment.status.in_(['scheduled', 'pending']),
        Appointment.date == today
    ).order_by(Appointment.start_time).all()
    return render_template('receptionist_dashboard.html', appointments=appointments)


# ============================
# CREATE APPOINTMENT (for receptionist)
# ============================
@receptionist_bp.route('/create_appointment', methods=['GET', 'POST'])
@login_required
@receptionist_required
def create_appointment():
    if request.method == 'POST':
        patient_email = request.form.get('patient_email')
        doctor_id = request.form.get('doctor_id')
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        notes = request.form.get('notes', '')

        # Validate patient
        user = User.query.filter_by(email=patient_email).first()
        if not user or user.role != 'patient':
            flash('Patient not found. Please register first.', 'danger')
            return redirect(url_for('receptionist.create_appointment'))
        patient = Patient.query.filter_by(user_id=user.id).first()

        # Validate date/time
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('receptionist.create_appointment'))

        # Check if slot is available
        available_slots = Availability.get_available_slots(doctor_id, date)
        slot_found = any(s['start_obj'] == start_time for s in available_slots)
        if not slot_found:
            flash('Selected slot is not available.', 'danger')
            return redirect(url_for('receptionist.create_appointment'))

        # Double-check existing booking
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date,
            start_time=start_time,
            status='scheduled'
        ).first()
        if existing:
            flash('This slot was just booked by someone else.', 'danger')
            return redirect(url_for('receptionist.create_appointment'))

        # Calculate end time
        slot_duration = 30  # default; you can fetch from GlobalSetting
        end_time = (datetime.combine(date, start_time) + timedelta(minutes=slot_duration)).time()

        # Generate unique reference
        reference = Appointment.generate_reference()

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status='pending',
            notes=notes,
            reference=reference
        )
        db.session.add(appointment)
        db.session.commit()

        flash(f'✅ Appointment {reference} created and sent to doctor for confirmation.', 'success')
        return redirect(url_for('receptionist.dashboard'))

    # GET: show form
    doctors = Doctor.query.all()
    return render_template('create_appointment.html', doctors=doctors)


# ============================
# VERIFY APPOINTMENT (check-in)
# ============================
@receptionist_bp.route('/verify', methods=['GET', 'POST'])
@login_required
@receptionist_required
def verify_appointment():
    appointment = None
    if request.method == 'POST':
        reference = request.form.get('reference', '').strip().upper()
        if not reference:
            flash('Please enter an Appointment ID.', 'danger')
            return render_template('receptionist_verify.html', appointment=appointment)

        appointment = Appointment.query.filter_by(reference=reference).first()
        if not appointment:
            flash('Appointment not found.', 'danger')
            return render_template('receptionist_verify.html', appointment=appointment)

        if appointment.status != 'scheduled':
            flash(f'Appointment status is "{appointment.status}". Cannot mark as completed.', 'warning')
            return render_template('receptionist_verify.html', appointment=appointment)

        # Mark as completed
        appointment.status = 'completed'
        db.session.commit()
        flash(f'✅ Appointment {reference} verified and marked as completed!', 'success')
        return render_template('receptionist_verify.html', appointment=appointment)

    # GET: show form
    return render_template('receptionist_verify.html', appointment=appointment)


# ============================
# LEGACY VERIFY (alternative URL)
# ============================
@receptionist_bp.route('/verify_appointment', methods=['GET', 'POST'])
@login_required
@receptionist_required
def verify_appointment_legacy():
    appointment = None
    if request.method == 'POST':
        apt_id = request.form.get('appointment_id')
        appointment = Appointment.query.filter_by(reference=apt_id).first()
        if not appointment:
            flash('Appointment not found', 'danger')
        else:
            if appointment.status == 'scheduled':
                appointment.status = 'completed'
                db.session.commit()
                flash(f'✅ Appointment {apt_id} marked as completed!', 'success')
            else:
                flash(f'Appointment status is "{appointment.status}". Cannot mark as completed.', 'warning')
    return render_template('verify_appointment.html', appointment=appointment)


# ============================
# GET AVAILABLE SLOTS (AJAX)
# ============================
@receptionist_bp.route('/get_slots/<int:doctor_id>/<date>')
@login_required
@receptionist_required
def get_slots(doctor_id, date):
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    slots = Availability.get_available_slots(doctor_id, target_date)
    return jsonify(slots)


# ============================
# BILLS MANAGEMENT
# ============================
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