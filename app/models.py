import secrets
import string
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

# ========== User ==========
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, doctor, patient, receptionist
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='user', uselist=False)
    doctor = db.relationship('Doctor', backref='user', uselist=False)
    receptionist = db.relationship('Receptionist', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


# ========== Patient ==========
class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    emergency_contact = db.Column(db.String(100))
    blood_group = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    prescriptions = db.relationship('Prescription', backref='patient', lazy=True)
    bills = db.relationship('Bill', backref='patient', lazy=True)
    insurances = db.relationship('Insurance', backref='patient', lazy=True)

    def __repr__(self):
        return f'<Patient {self.full_name}>'


# ========== Doctor ==========
class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100))
    qualification = db.Column(db.String(200))
    experience_years = db.Column(db.Integer, default=0)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    prescriptions = db.relationship('Prescription', backref='doctor', lazy=True)
    availabilities = db.relationship('Availability', backref='doctor', lazy=True)

    def __repr__(self):
        return f'<Doctor {self.full_name}>'


# ========== Receptionist ==========
class Receptionist(db.Model):
    __tablename__ = 'receptionists'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Receptionist {self.full_name}>'


# ========== Appointment ==========
class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled, pending
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    prescriptions = db.relationship('Prescription', backref='appointment', lazy=True)
    bill = db.relationship('Bill', backref='appointment', uselist=False)

    def __repr__(self):
        return f'<Appointment {self.id} - {self.date}>'


# ========== Prescription ==========
class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    diagnosis = db.Column(db.Text)
    medication = db.Column(db.Text)
    dosage = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Prescription {self.id} for Patient {self.patient_id}>'


# ========== Availability ==========
class Availability(db.Model):
    __tablename__ = 'availabilities'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    day_of_week = db.Column(db.Integer)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_available_slots(cls, doctor_id, date):
        """
        Return list of available time slots for a doctor on a given date.
        Each slot is a dict with 'start', 'end' (both time objects).
        """
        from datetime import datetime, timedelta
        day_of_week = date.weekday()
        availabilities = cls.query.filter_by(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            is_active=True
        ).all()
        if not availabilities:
            return []

        slot_duration = int(GlobalSetting.get('slot_duration_minutes', 30))
        slots = []
        for avail in availabilities:
            current = datetime.combine(date, avail.start_time)
            end = datetime.combine(date, avail.end_time)
            step = timedelta(minutes=slot_duration)
            while current + step <= end:
                slot_start = current.time()
                slot_end = (current + step).time()
                existing = Appointment.query.filter_by(
                    doctor_id=doctor_id,
                    date=date,
                    start_time=slot_start,
                    status='scheduled'
                ).first()
                if not existing:
                    slots.append({
                        'start': slot_start.strftime('%H:%M'),
                        'end': slot_end.strftime('%H:%M'),
                        'start_obj': slot_start,
                        'end_obj': slot_end
                    })
                current += step
        return slots

    def __repr__(self):
        return f'<Availability for Doctor {self.doctor_id} on {self.day_of_week}>'


# ========== Insurance ==========
class Insurance(db.Model):
    __tablename__ = 'insurances'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    provider = db.Column(db.String(100), nullable=False)
    policy_number = db.Column(db.String(100))
    coverage_details = db.Column(db.Text)
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Insurance {self.provider} for Patient {self.patient_id}>'


# ========== Bill ==========
class Bill(db.Model):
    __tablename__ = 'bills'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid, cancelled
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Bill {self.id} - {self.amount}>'


# ========== Global Setting ==========
class GlobalSetting(db.Model):
    __tablename__ = 'global_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key, value):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

    def __repr__(self):
        return f'<GlobalSetting {self.key}={self.value}>'


# ========== Email Verification ==========
class EmailVerification(db.Model):
    __tablename__ = 'email_verifications'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=10))

    @classmethod
    def generate_otp(cls, length=6):
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @classmethod
    def create_otp(cls, email, length=6, expiry_minutes=10):
        otp = cls.generate_otp(length)
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        cls.query.filter_by(email=email).delete()
        db.session.commit()
        record = cls(email=email, otp=otp, expires_at=expires_at)
        db.session.add(record)
        db.session.commit()
        return otp

    @classmethod
    def verify_otp(cls, email, otp):
        record = cls.query.filter_by(email=email).first()
        if not record:
            return False
        if record.otp != otp:
            return False
        if datetime.utcnow() > record.expires_at:
            return False
        db.session.delete(record)
        db.session.commit()
        return True

    def __repr__(self):
        return f'<EmailVerification {self.email}>'