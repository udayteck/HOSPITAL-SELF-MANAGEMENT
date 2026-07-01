from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    User, Doctor, Patient, Appointment, Availability,
    Receptionist, GlobalSetting, Bill, Insurance
)
from app.forms import DoctorForm
from datetime import datetime, timedelta
from sqlalchemy import func, extract

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


# ========== DASHBOARD ==========
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    doctor_count = Doctor.query.count()
    patient_count = Patient.query.count()
    receptionist_count = Receptionist.query.count()
    appointment_count = Appointment.query.count()

    # Doctors with availability count
    doctors = Doctor.query.all()
    doctors_data = []
    for doc in doctors:
        availability_count = Availability.query.filter_by(doctor_id=doc.id).count()
        doctors_data.append({
            'id': doc.id,
            'name': doc.full_name,
            'specialty': doc.specialization,
            'phone': doc.phone,
            'email': doc.user.email,
            'availability_count': availability_count,
            'is_active': doc.user.is_active
        })

    # Patients with appointment count
    patients = Patient.query.all()
    patients_data = []
    for pat in patients:
        appointment_count_pat = Appointment.query.filter_by(patient_id=pat.id).count()
        patients_data.append({
            'id': pat.id,
            'name': pat.full_name,
            'email': pat.user.email,
            'phone': pat.phone,
            'dob': pat.date_of_birth.strftime('%Y-%m-%d') if pat.date_of_birth else 'N/A',
            'appointment_count': appointment_count_pat,
            'is_active': pat.user.is_active
        })

    # Receptionists
    receptionists = Receptionist.query.all()
    receptionists_data = []
    for rec in receptionists:
        receptionists_data.append({
            'id': rec.id,
            'name': rec.full_name,
            'email': rec.user.email,
            'phone': rec.phone,
            'is_active': rec.user.is_active
        })

    # Appointment status breakdown
    total_appointments = Appointment.query.count()
    completed = Appointment.query.filter_by(status='completed').count()
    cancelled = Appointment.query.filter_by(status='cancelled').count()
    scheduled = Appointment.query.filter_by(status='scheduled').count()
    no_show = Appointment.query.filter_by(status='no_show').count()
    noshow_rate = (no_show / total_appointments * 100) if total_appointments > 0 else 0

    # Last 7 days appointments (by Appointment.date)
    last_7_days = []
    appointments_per_day = []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        last_7_days.append(day.strftime('%a, %d %b'))
        count = Appointment.query.filter(Appointment.date == day).count()
        appointments_per_day.append(count)

    # Monthly counts (by Appointment.date)
    monthly_labels = []
    monthly_counts = []
    for m in range(1, 13):
        monthly_labels.append(datetime(2026, m, 1).strftime('%b'))
        count = Appointment.query.filter(extract('month', Appointment.date) == m).count()
        monthly_counts.append(count)

    return render_template(
        'admin_dashboard.html',
        doctor_count=doctor_count,
        patient_count=patient_count,
        receptionist_count=receptionist_count,
        appointment_count=appointment_count,
        doctors=doctors_data,
        patients=patients_data,
        receptionists=receptionists_data,
        total_appointments=total_appointments,
        completed=completed,
        cancelled=cancelled,
        scheduled=scheduled,
        no_show=no_show,
        noshow_rate=noshow_rate,
        last_7_days=last_7_days,
        appointments_per_day=appointments_per_day,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts
    )


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # --- Basic Counts ---
    total_users = User.query.count()
    total_patients = Patient.query.count()
    total_doctors = Doctor.query.count()
    total_appointments = Appointment.query.count()
    total_bills = Bill.query.count()
    total_revenue = db.session.query(func.sum(Bill.amount)).filter(Bill.status == 'paid').scalar() or 0

    # --- Appointment Status Breakdown ---
    status_counts = db.session.query(
        Appointment.status, func.count(Appointment.id)
    ).group_by(Appointment.status).all()
    status_data = {status: count for status, count in status_counts}

    # --- Monthly Appointments (last 12 months) ---
    today = datetime.now().date()
    monthly_labels = []
    monthly_appointments = []
    monthly_revenue = []

    for i in range(11, -1, -1):
        month = today.replace(day=1) - timedelta(days=i*30)
        month_start = month.replace(day=1)
        if month.month == 12:
            month_end = month.replace(day=31)
        else:
            month_end = month.replace(month=month.month+1, day=1) - timedelta(days=1)
        # Appointments count
        count = Appointment.query.filter(
            Appointment.date >= month_start,
            Appointment.date <= month_end
        ).count()
        monthly_appointments.append(count)
        # Revenue (paid bills)
        revenue = db.session.query(func.sum(Bill.amount)).filter(
            Bill.status == 'paid',
            Bill.paid_at >= month_start,
            Bill.paid_at <= month_end
        ).scalar() or 0
        monthly_revenue.append(float(revenue))
        monthly_labels.append(month.strftime('%b %Y'))

    # --- Top Doctors by Appointments ---
    top_doctors = db.session.query(
        Doctor.full_name, func.count(Appointment.id).label('appt_count')
    ).join(Appointment, Appointment.doctor_id == Doctor.id).group_by(Doctor.id).order_by(
        func.count(Appointment.id).desc()
    ).limit(5).all()

    top_doctors_data = [{'name': d[0], 'count': d[1]} for d in top_doctors]

    # --- Recent Appointments (last 10) ---
    recent_appointments = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).limit(10).all()

    return render_template(
        'admin_analytics.html',
        total_users=total_users,
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_appointments=total_appointments,
        total_bills=total_bills,
        total_revenue=total_revenue,
        status_data=status_data,
        monthly_labels=monthly_labels,
        monthly_appointments=monthly_appointments,
        monthly_revenue=monthly_revenue,
        top_doctors_data=top_doctors_data,
        recent_appointments=recent_appointments
    )

# ========== DOCTOR MANAGEMENT ==========
@admin_bp.route('/doctors')
@login_required
@admin_required
def manage_doctors():
    doctors = Doctor.query.all()
    return render_template('manage_doctors.html', doctors=doctors)

@admin_bp.route('/doctors/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_doctor():
    form = DoctorForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.add_doctor'))
        user = User(email=form.email.data, role='doctor', is_active=True)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        doctor = Doctor(
            user_id=user.id,
            full_name=form.full_name.data,
            specialization=form.specialty.data,
            phone=form.phone.data
        )
        db.session.add(doctor)
        db.session.commit()
        flash('Doctor added successfully', 'success')
        return redirect(url_for('admin.manage_doctors'))
    return render_template('doctor_form.html', form=form, title='Add Doctor')

@admin_bp.route('/doctors/delete/<int:doctor_id>')
@login_required
@admin_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    user = doctor.user
    db.session.delete(doctor)
    db.session.delete(user)
    db.session.commit()
    flash('Doctor deleted', 'success')
    return redirect(url_for('admin.manage_doctors'))

@admin_bp.route('/doctors/disable/<int:user_id>')
@login_required
@admin_required
def disable_doctor(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'doctor':
        user.is_active = not user.is_active
        db.session.commit()
        status = 'disabled' if not user.is_active else 'enabled'
        flash(f'Doctor {status}', 'success')
    return redirect(url_for('admin.manage_doctors'))


# ========== PATIENT MANAGEMENT ==========
@admin_bp.route('/patients')
@login_required
@admin_required
def manage_patients():
    patients = Patient.query.all()
    return render_template('manage_patients.html', patients=patients)

@admin_bp.route('/patients/disable/<int:user_id>')
@login_required
@admin_required
def disable_patient(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'patient':
        user.is_active = not user.is_active
        db.session.commit()
        status = 'disabled' if not user.is_active else 'enabled'
        flash(f'Patient {status}', 'success')
    return redirect(url_for('admin.manage_patients'))


# ========== RECEPTIONIST MANAGEMENT ==========
@admin_bp.route('/receptionists')
@login_required
@admin_required
def manage_receptionists():
    receptionists = Receptionist.query.all()
    return render_template('manage_receptionists.html', receptionists=receptionists)

@admin_bp.route('/receptionists/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_receptionist():
    if request.method == 'POST':
        email = request.form['email']
        full_name = request.form['full_name']
        phone = request.form['phone']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.add_receptionist'))
        user = User(email=email, role='receptionist', is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        rec = Receptionist(user_id=user.id, full_name=full_name, phone=phone)
        db.session.add(rec)
        db.session.commit()
        flash('Receptionist added', 'success')
        return redirect(url_for('admin.manage_receptionists'))
    return render_template('receptionist_form.html')

@admin_bp.route('/receptionists/delete/<int:receptionist_id>')
@login_required
@admin_required
def delete_receptionist(receptionist_id):
    rec = Receptionist.query.get_or_404(receptionist_id)
    user = rec.user
    db.session.delete(rec)
    db.session.delete(user)
    db.session.commit()
    flash('Receptionist deleted', 'success')
    return redirect(url_for('admin.manage_receptionists'))

@admin_bp.route('/receptionists/disable/<int:user_id>')
@login_required
@admin_required
def disable_receptionist(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'receptionist':
        user.is_active = not user.is_active
        db.session.commit()
        status = 'disabled' if not user.is_active else 'enabled'
        flash(f'Receptionist {status}', 'success')
    return redirect(url_for('admin.manage_receptionists'))


# ========== APPOINTMENT MANAGEMENT ==========
@admin_bp.route('/appointments')
@login_required
@admin_required
def all_appointments():
    appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.start_time.desc()).all()
    return render_template('all_appointments.html', appointments=appointments)


# ========== BILLS MANAGEMENT ==========
@admin_bp.route('/bills')
@login_required
@admin_required
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

@admin_bp.route('/bills/generate', methods=['GET', 'POST'])
@login_required
@admin_required
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
            return redirect(url_for('admin.generate_bill'))

        bill_number = f"BILL-{datetime.utcnow().strftime('%Y%m%d')}-{Bill.query.count() + 1}"
        bill = Bill(
            #bill_number=bill_number,
            patient_id=patient_id,
            appointment_id=appointment_id if appointment_id else None,
            amount=amount,
            items=items,
            status=status,
           # created_by=current_user.id
        )
        db.session.add(bill)
        db.session.commit()
        flash(f'Bill {bill_number} generated successfully', 'success')
        return redirect(url_for('admin.manage_bills'))

    patients = Patient.query.all()
    appointments = Appointment.query.filter_by(status='scheduled').all()
    return render_template('bill_form.html', patients=patients, appointments=appointments, title='Generate New Bill')

@admin_bp.route('/bills/view/<int:bill_id>')
@login_required
@admin_required
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('bill_details.html', bill=bill)

@admin_bp.route('/bills/edit/<int:bill_id>', methods=['GET', 'POST'])
@login_required
@admin_required
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
            return redirect(url_for('admin.edit_bill', bill_id=bill.id))

        bill.patient_id = patient_id
        bill.appointment_id = appointment_id if appointment_id else None
        bill.amount = amount
        bill.items = items
        bill.status = status
        db.session.commit()

        flash('Bill updated successfully!', 'success')
        return redirect(url_for('admin.view_bill', bill_id=bill.id))

    patients = Patient.query.all()
    appointments = Appointment.query.filter_by(status='scheduled').all()
    return render_template('bill_edit.html', bill=bill, patients=patients, appointments=appointments)


# ========== PATIENT INSURANCE (ADMIN) ==========
@admin_bp.route('/patient/<int:patient_id>/insurance')
@login_required
@admin_required
def view_patient_insurance(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    insurance = Insurance.query.filter_by(patient_id=patient.id).first()
    return render_template('admin_patient_insurance.html', patient=patient, insurance=insurance)

@admin_bp.route('/patient/<int:patient_id>/insurance/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_patient_insurance(patient_id):
    patient = Patient.query.get_or_404(patient_id)
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
            return redirect(url_for('admin.edit_patient_insurance', patient_id=patient.id))

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
        flash('Insurance details updated.', 'success')
        return redirect(url_for('admin.view_patient_insurance', patient_id=patient.id))

    return render_template('admin_edit_patient_insurance.html', patient=patient, insurance=insurance)


# ========== REPORTS & SETTINGS ==========
@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    total_appointments = Appointment.query.count()
    completed = Appointment.query.filter_by(status='completed').count()
    cancelled = Appointment.query.filter_by(status='cancelled').count()
    no_show = Appointment.query.filter_by(status='no_show').count()
    noshow_rate = (no_show / total_appointments * 100) if total_appointments > 0 else 0
    doctor_stats = db.session.query(Doctor.full_name, func.count(Appointment.id)).outerjoin(Appointment).group_by(Doctor.id).all()
    return render_template('reports.html', total=total_appointments, completed=completed, cancelled=cancelled, noshow_rate=noshow_rate, doctor_stats=doctor_stats)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        GlobalSetting.set('cancellation_hours', request.form.get('cancellation_hours', 2))
        GlobalSetting.set('slot_duration_minutes', request.form.get('slot_duration_minutes', 30))
        GlobalSetting.set('appointment_lead_days', request.form.get('appointment_lead_days', 30))
        flash('Settings updated.', 'success')
        return redirect(url_for('admin.settings'))
    cancellation_hours = GlobalSetting.get('cancellation_hours', 2)
    slot_duration = GlobalSetting.get('slot_duration_minutes', 30)
    lead_days = GlobalSetting.get('appointment_lead_days', 30)
    return render_template('settings.html', cancellation_hours=cancellation_hours, slot_duration=slot_duration, lead_days=lead_days)