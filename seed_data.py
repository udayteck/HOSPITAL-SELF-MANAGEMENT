import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import secrets

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    User, Patient, Doctor, Appointment, Prescription, Bill, 
    Insurance, GlobalSetting, Availability, Receptionist
)

app = create_app()

def seed_database():
    with app.app_context():
        print("🌱 Seeding SKD Hospital database with Telugu sample data...")
        
        # ----- 1. Ensure Global Settings -----
        if not GlobalSetting.query.first():
            GlobalSetting.set('cancellation_hours', '2')
            GlobalSetting.set('slot_duration_minutes', '30')
            GlobalSetting.set('appointment_lead_days', '30')
            print("  ✅ Global settings created.")
        
        # ----- 2. Create Doctors (Telugu names) -----
        doctor_data = [
            {'email': 'dr.krishna.reddy@skd.com', 'full_name': 'Dr. Krishna Reddy', 
             'specialization': 'Cardiology', 'phone': '+91 98765 43210', 'fee': 1500,
             'qualification': 'MD, DM Cardiology', 'experience_years': 15},
            {'email': 'dr.radha.naidu@skd.com', 'full_name': 'Dr. Radha Naidu', 
             'specialization': 'Neurology', 'phone': '+91 98765 43211', 'fee': 1800,
             'qualification': 'MD, DM Neurology', 'experience_years': 12},
            {'email': 'dr.srinivas.rao@skd.com', 'full_name': 'Dr. Srinivas Rao', 
             'specialization': 'Orthopedics', 'phone': '+91 98765 43212', 'fee': 1200,
             'qualification': 'MS Ortho', 'experience_years': 10},
            {'email': 'dr.meena.gupta@skd.com', 'full_name': 'Dr. Meena Gupta', 
             'specialization': 'Pediatrics', 'phone': '+91 98765 43213', 'fee': 1000,
             'qualification': 'MD Pediatrics', 'experience_years': 8},
        ]
        
        doctors = []
        for data in doctor_data:
            user = User.query.filter_by(email=data['email']).first()
            if not user:
                user = User(email=data['email'], role='doctor', is_active=True)
                user.set_password('Doctor@123')
                db.session.add(user)
                db.session.flush()
            doctor = Doctor.query.filter_by(user_id=user.id).first()
            if not doctor:
                doctor = Doctor(
                    user_id=user.id,
                    full_name=data['full_name'],
                    specialization=data['specialization'],
                    qualification=data.get('qualification', ''),
                    experience_years=data.get('experience_years', 0),
                    phone=data['phone'],
                    fee=data['fee']
                )
                db.session.add(doctor)
                db.session.flush()
            doctors.append(doctor)
            print(f"  ✅ Doctor: {data['full_name']}")
        db.session.commit()
        
        # ----- 3. Create Patients (Telugu names) -----
        patient_data = [
            {'email': 'suresh.reddy@email.com', 'full_name': 'Suresh Reddy', 
             'dob': '1985-03-15', 'gender': 'Male', 'phone': '+91 98765 11111',
             'address': '123 Main Street, Hyderabad, Telangana 500001',
             'emergency_contact': 'Lakshmi Reddy, +91 98765 11112',
             'blood_group': 'A+', 'allergies': 'Penicillin, Peanuts',
             'medical_history': 'Hypertension (diagnosed 2019)'},
            {'email': 'lakshmi.naidu@email.com', 'full_name': 'Lakshmi Naidu',
             'dob': '1990-07-22', 'gender': 'Female', 'phone': '+91 98765 22222',
             'address': '456 Oak Avenue, Visakhapatnam, AP 530001',
             'emergency_contact': 'Ramesh Naidu, +91 98765 22223',
             'blood_group': 'B+', 'allergies': 'None',
             'medical_history': 'Asthma (diagnosed 2015)'},
            {'email': 'ramesh.rao@email.com', 'full_name': 'Ramesh Rao',
             'dob': '1978-11-02', 'gender': 'Male', 'phone': '+91 98765 33333',
             'address': '789 Pine Lane, Vijayawada, AP 520001',
             'emergency_contact': 'Sita Rao, +91 98765 33334',
             'blood_group': 'O-', 'allergies': 'Sulfa drugs',
             'medical_history': 'Diabetes Type 2, High Cholesterol'},
            {'email': 'sarada.gupta@email.com', 'full_name': 'Sarada Gupta',
             'dob': '1995-05-10', 'gender': 'Female', 'phone': '+91 98765 44444',
             'address': '321 Cedar Road, Chennai, TN 600001',
             'emergency_contact': 'Venkatesh Gupta, +91 98765 44445',
             'blood_group': 'AB+', 'allergies': 'Latex',
             'medical_history': 'Anemia (diagnosed 2020)'},
            {'email': 'mahesh.sharma@email.com', 'full_name': 'Mahesh Sharma',
             'dob': '1982-09-18', 'gender': 'Male', 'phone': '+91 98765 55555',
             'address': '654 Birch Blvd, Bengaluru, KA 560001',
             'emergency_contact': 'Kavya Sharma, +91 98765 55556',
             'blood_group': 'A-', 'allergies': 'Dairy',
             'medical_history': 'Gallstones (surgery 2018)'},
            {'email': 'padma.iyer@email.com', 'full_name': 'Padma Iyer',
             'dob': '1988-12-25', 'gender': 'Female', 'phone': '+91 98765 66666',
             'address': '987 Elm Street, Pune, MH 411001',
             'emergency_contact': 'Srinivas Iyer, +91 98765 66667',
             'blood_group': 'O+', 'allergies': 'None',
             'medical_history': 'None'},
            {'email': 'venkatesh.pillai@email.com', 'full_name': 'Venkatesh Pillai',
             'dob': '1992-04-07', 'gender': 'Male', 'phone': '+91 98765 77777',
             'address': '147 Maple Drive, Ahmedabad, GJ 380001',
             'emergency_contact': 'Meena Pillai, +91 98765 77778',
             'blood_group': 'B-', 'allergies': 'Aspirin',
             'medical_history': 'Migraine (diagnosed 2016)'},
            {'email': 'sita.yadav@email.com', 'full_name': 'Sita Yadav',
             'dob': '1980-06-30', 'gender': 'Female', 'phone': '+91 98765 88888',
             'address': '258 Willow Way, Kolkata, WB 700001',
             'emergency_contact': 'Nagesh Yadav, +91 98765 88889',
             'blood_group': 'AB-', 'allergies': 'Shellfish',
             'medical_history': 'Thyroid disorder (diagnosed 2010)'},
        ]
        
        patients = []
        for data in patient_data:
            user = User.query.filter_by(email=data['email']).first()
            if not user:
                user = User(email=data['email'], role='patient', is_active=True)
                user.set_password('Patient@123')
                db.session.add(user)
                db.session.flush()
            patient = Patient.query.filter_by(user_id=user.id).first()
            if not patient:
                patient = Patient(
                    user_id=user.id,
                    full_name=data['full_name'],
                    date_of_birth=datetime.strptime(data['dob'], '%Y-%m-%d'),
                    gender=data['gender'],
                    phone=data['phone'],
                    address=data['address'],
                    emergency_contact=data['emergency_contact'],
                    blood_group=data['blood_group'],
                    allergies=data['allergies'],
                    medical_history=data['medical_history']
                )
                db.session.add(patient)
                db.session.flush()
            patients.append(patient)
            print(f"  ✅ Patient: {data['full_name']}")
        db.session.commit()
        
        # ----- 4. Create Availability for Doctors -----
        from datetime import time
        avail_days = [0, 1, 2, 3, 4, 5]  # Mon-Sat
        for doctor in doctors:
            for day in avail_days:
                start_hour = 9 if day != 5 else 10  # Sat starts later
                start = time(start_hour, 0)
                end = time(17, 0) if day != 5 else time(14, 0)
                existing = Availability.query.filter_by(
                    doctor_id=doctor.id,
                    day_of_week=day,
                    start_time=start,
                    end_time=end
                ).first()
                if not existing:
                    avail = Availability(
                        doctor_id=doctor.id,
                        day_of_week=day,
                        start_time=start,
                        end_time=end,
                        is_active=True
                    )
                    db.session.add(avail)
            print(f"  ✅ Availability for Dr. {doctor.full_name}")
        db.session.commit()
        
        # ----- 5. Create Appointments (past, present, upcoming) -----
        today = datetime.now().date()
        appointments = []
        statuses = ['scheduled', 'completed', 'cancelled', 'pending']
        # We'll create a mix with different statuses and dates
        appointment_slots = [
            # Patient 0 (Suresh) with Doctor 0 (Krishna) - past completed
            {'patient_idx': 0, 'doctor_idx': 0, 'days_ago': 30, 'status': 'completed', 'notes': 'Routine checkup'},
            {'patient_idx': 0, 'doctor_idx': 0, 'days_ago': 2, 'status': 'scheduled', 'notes': 'Follow-up ECG'},
            # Patient 1 (Lakshmi) with Doctor 1 (Radha) - past completed
            {'patient_idx': 1, 'doctor_idx': 1, 'days_ago': 25, 'status': 'completed', 'notes': 'Migraine consultation'},
            {'patient_idx': 1, 'doctor_idx': 1, 'days_ago': 5, 'status': 'scheduled', 'notes': 'Neurology follow-up'},
            # Patient 2 (Ramesh) with Doctor 2 (Srinivas) - past completed
            {'patient_idx': 2, 'doctor_idx': 2, 'days_ago': 20, 'status': 'completed', 'notes': 'Knee pain assessment'},
            {'patient_idx': 2, 'doctor_idx': 2, 'days_ago': 3, 'status': 'scheduled', 'notes': 'Post-surgery check'},
            # Patient 3 (Sarada) with Doctor 3 (Meena) - completed
            {'patient_idx': 3, 'doctor_idx': 3, 'days_ago': 15, 'status': 'completed', 'notes': 'Childhood vaccination'},
            {'patient_idx': 3, 'doctor_idx': 3, 'days_ago': 1, 'status': 'scheduled', 'notes': 'Follow-up vaccination'},
            # Patient 4 (Mahesh) with Doctor 0 (Krishna) - pending (waiting for doctor)
            {'patient_idx': 4, 'doctor_idx': 0, 'days_ago': -1, 'status': 'pending', 'notes': 'New patient consult'},
            # Patient 5 (Padma) with Doctor 1 (Radha) - scheduled future
            {'patient_idx': 5, 'doctor_idx': 1, 'days_ago': -3, 'status': 'scheduled', 'notes': 'Headache follow-up'},
            # Patient 6 (Venkatesh) with Doctor 2 (Srinivas) - cancelled
            {'patient_idx': 6, 'doctor_idx': 2, 'days_ago': -2, 'status': 'cancelled', 'notes': 'Patient cancelled'},
            # Patient 7 (Sita) with Doctor 3 (Meena) - pending
            {'patient_idx': 7, 'doctor_idx': 3, 'days_ago': -4, 'status': 'pending', 'notes': 'New patient'},
            # Additional upcoming for dashboard
            {'patient_idx': 0, 'doctor_idx': 1, 'days_ago': -5, 'status': 'scheduled', 'notes': 'Cardiology review'},
            {'patient_idx': 2, 'doctor_idx': 3, 'days_ago': -6, 'status': 'scheduled', 'notes': 'Pediatric checkup'},
            {'patient_idx': 4, 'doctor_idx': 2, 'days_ago': -7, 'status': 'scheduled', 'notes': 'Orthopedic follow-up'},
        ]
        
        for slot in appointment_slots:
            patient = patients[slot['patient_idx']]
            doctor = doctors[slot['doctor_idx']]
            days_ago = slot['days_ago']
            if days_ago >= 0:
                date = today - timedelta(days=days_ago)
            else:
                date = today + timedelta(days=-days_ago)
            start_hour = 9 + (slot['patient_idx'] % 6)  # spread across day
            start_time = datetime.strptime(f"{start_hour:02d}:00", '%H:%M').time()
            end_time = (datetime.combine(date, start_time) + timedelta(minutes=30)).time()
            
            # Check if appointment already exists to avoid duplication
            existing = Appointment.query.filter_by(
                patient_id=patient.id,
                doctor_id=doctor.id,
                date=date,
                start_time=start_time
            ).first()
            if existing:
                continue
            
            # Generate reference
            ref = Appointment.generate_reference()
            appt = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                status=slot['status'],
                notes=slot['notes'],
                reference=ref
            )
            db.session.add(appt)
            appointments.append(appt)
        db.session.commit()
        print(f"  ✅ Created {len(appointments)} appointments.")
        
        # ----- 6. Create Prescriptions for completed appointments -----
        completed_appts = Appointment.query.filter_by(status='completed').limit(6).all()
        rx_data = [
            {'medication': 'Amlodipine 5mg', 'dosage': '1 tablet daily', 'duration': '30 days',
             'instructions': 'Take after breakfast', 'diagnosis': 'Hypertension'},
            {'medication': 'Sumatriptan 50mg', 'dosage': '1 tablet as needed', 'duration': '10 days',
             'instructions': 'Take at onset of migraine', 'diagnosis': 'Migraine'},
            {'medication': 'Ibuprofen 400mg', 'dosage': '1 tablet every 8 hours', 'duration': '5 days',
             'instructions': 'Take with food', 'diagnosis': 'Knee pain'},
            {'medication': 'Salbutamol inhaler', 'dosage': '2 puffs as needed', 'duration': '30 days',
             'instructions': 'Use before exercise', 'diagnosis': 'Asthma'},
            {'medication': 'Metformin 500mg', 'dosage': '1 tablet twice daily', 'duration': '90 days',
             'instructions': 'Take after meals', 'diagnosis': 'Type 2 Diabetes'},
            {'medication': 'Cetirizine 10mg', 'dosage': '1 tablet daily', 'duration': '15 days',
             'instructions': 'Take at night', 'diagnosis': 'Allergy'},
        ]
        prescriptions = []
        for i, apt in enumerate(completed_appts):
            if i >= len(rx_data):
                break
            data = rx_data[i]
            existing = Prescription.query.filter_by(
                patient_id=apt.patient_id,
                doctor_id=apt.doctor_id,
                appointment_id=apt.id
            ).first()
            if existing:
                continue
            rx = Prescription(
                patient_id=apt.patient_id,
                doctor_id=apt.doctor_id,
                appointment_id=apt.id,
                diagnosis=data['diagnosis'],
                medication=data['medication'],
                dosage=data['dosage'],
                duration=data['duration'],
                instructions=data['instructions']
            )
            db.session.add(rx)
            prescriptions.append(rx)
        db.session.commit()
        print(f"  ✅ Created {len(prescriptions)} prescriptions.")
        
        # ----- 7. Create Bills for appointments (some paid, some pending) -----
        bill_appts = Appointment.query.filter(
            Appointment.status.in_(['completed', 'scheduled'])
        ).limit(8).all()
        bills = []
        bill_amounts = [1500, 2500, 800, 1200, 3000, 500, 1800, 2200]
        for i, apt in enumerate(bill_appts):
            if i >= len(bill_amounts):
                break
            existing = Bill.query.filter_by(appointment_id=apt.id).first()
            if existing:
                continue
            status = 'paid' if i % 2 == 0 else 'pending'
            bill = Bill(
                patient_id=apt.patient_id,
                appointment_id=apt.id,
                amount=bill_amounts[i],
                status=status,
                payment_method='Cash' if status == 'paid' else None,
                paid_at=datetime.utcnow() if status == 'paid' else None
            )
            db.session.add(bill)
            bills.append(bill)
        db.session.commit()
        print(f"  ✅ Created {len(bills)} bills.")
        
        # ----- 8. Create Insurance for some patients -----
        insurance_patients = patients[:4]
        insurance_data = [
            {'provider': 'Star Health', 'policy_number': 'SH-2024-001', 'coverage': 'Family Plan - 5 Lakh', 'expiry': '2025-12-31'},
            {'provider': 'ICICI Lombard', 'policy_number': 'IL-2024-002', 'coverage': 'Individual Plan - 3 Lakh', 'expiry': '2025-06-30'},
            {'provider': 'Bajaj Allianz', 'policy_number': 'BA-2024-003', 'coverage': 'Senior Plan - 10 Lakh', 'expiry': '2026-01-15'},
            {'provider': 'HDFC Ergo', 'policy_number': 'HE-2024-004', 'coverage': 'Family Plan - 7 Lakh', 'expiry': '2025-09-30'},
        ]
        ins = []
        for i, patient in enumerate(insurance_patients):
            existing = Insurance.query.filter_by(patient_id=patient.id).first()
            if existing:
                continue
            data = insurance_data[i]
            ins_rec = Insurance(
                patient_id=patient.id,
                provider=data['provider'],
                policy_number=data['policy_number'],
                coverage_details=data['coverage'],
                expiry_date=datetime.strptime(data['expiry'], '%Y-%m-%d')
            )
            db.session.add(ins_rec)
            ins.append(ins_rec)
        db.session.commit()
        print(f"  ✅ Created {len(ins)} insurance records.")
        
        # ----- 9. Create a receptionist user -----
        rec_email = 'reception@skd.com'
        if not User.query.filter_by(email=rec_email).first():
            rec_user = User(email=rec_email, role='receptionist', is_active=True)
            rec_user.set_password('Reception@123')
            db.session.add(rec_user)
            db.session.flush()
            rec = Receptionist(
                user_id=rec_user.id,
                full_name='Priya Reddy',
                phone='+91 98765 99999',
                email=rec_email
            )
            db.session.add(rec)
            db.session.commit()
            print("  ✅ Receptionist created: reception@skd.com / Reception@123")
        else:
            print("  ⏭️ Receptionist already exists.")
        
        print("\n✅ Seeding completed successfully!")
        print("\n🔑 Login credentials:")
        print("  Admin: admin@hospital.com / admin123")
        print("  Doctor: dr.krishna.reddy@skd.com / Doctor@123")
        print("  Patient: suresh.reddy@email.com / Patient@123")
        print("  Receptionist: reception@skd.com / Reception@123")

if __name__ == '__main__':
    seed_database()