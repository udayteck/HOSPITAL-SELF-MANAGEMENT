import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Patient, Doctor, Appointment, Prescription, Bill, Insurance, GlobalSetting

app = create_app()

def seed_database():
    with app.app_context():
        # ----- 1. Create Users (Telugu names) -----
        patient_users = [
            {'email': 'suresh.reddy@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
            {'email': 'lakshmi.naidu@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
            {'email': 'ramesh.rao@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
            {'email': 'sarada.gupta@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
            {'email': 'mahesh.sharma@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
            {'email': 'padma.iyer@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
            {'email': 'venkatesh.pillai@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
            {'email': 'sita.yadav@email.com', 'password': 'Patient@123', 'role': 'patient', 'is_active': True},
        ]

        print("Creating patient users (Telugu names)...")
        created_users = []
        for data in patient_users:
            existing = User.query.filter_by(email=data['email']).first()
            if existing:
                print(f"  ⏭️  User {data['email']} already exists.")
                created_users.append(existing)
                continue
            user = User(
                email=data['email'],
                role=data['role'],
                is_active=data['is_active']
            )
            user.set_password(data['password'])
            db.session.add(user)
            db.session.flush()
            created_users.append(user)
            print(f"  ✅ Created user: {data['email']}")
        db.session.commit()

        # ----- 2. Create Doctors (Telugu names) -----
        doctor_data = [
            {'email': 'dr.krishna.reddy@skd.com', 'full_name': 'Dr. Krishna Reddy', 'specialization': 'Cardiology', 'phone': '+91 98765 43210', 'fee': 1500},
            {'email': 'dr.radha.naidu@skd.com', 'full_name': 'Dr. Radha Naidu', 'specialization': 'Neurology', 'phone': '+91 98765 43211', 'fee': 1800},
            {'email': 'dr.srinivas.rao@skd.com', 'full_name': 'Dr. Srinivas Rao', 'specialization': 'Orthopedics', 'phone': '+91 98765 43212', 'fee': 1200},
            {'email': 'dr.meena.gupta@skd.com', 'full_name': 'Dr. Meena Gupta', 'specialization': 'Pediatrics', 'phone': '+91 98765 43213', 'fee': 1000},
        ]

        print("\nCreating doctors (Telugu names)...")
        doctors = []
        for data in doctor_data:
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user:
                doctor = Doctor.query.filter_by(user_id=existing_user.id).first()
                if doctor:
                    doctors.append(doctor)
                    print(f"  ⏭️  Doctor {data['full_name']} already exists.")
                    continue
            else:
                user = User(email=data['email'], role='doctor', is_active=True)
                user.set_password('Doctor@123')
                db.session.add(user)
                db.session.flush()
                existing_user = user
            doctor = Doctor(
                user_id=existing_user.id,
                full_name=data['full_name'],
                specialization=data['specialization'],
                phone=data['phone'],
                fee=data['fee'],
                experience_years=12
            )
            db.session.add(doctor)
            db.session.flush()
            doctors.append(doctor)
            print(f"  ✅ Created doctor: {data['full_name']}")
        db.session.commit()

        # ----- 3. Create Patients (Telugu names) -----
        patient_details = [
            {
                'user_email': 'suresh.reddy@email.com',
                'full_name': 'Suresh Reddy',
                'dob': '1985-03-15',
                'gender': 'Male',
                'phone': '+91 98765 11111',
                'address': '123 Main Street, Hyderabad, Telangana 500001',
                'emergency_contact': 'Lakshmi Reddy, +91 98765 11112',
                'blood_group': 'A+',
                'allergies': 'Penicillin, Peanuts',
                'medical_history': 'Hypertension (diagnosed 2019)'
            },
            {
                'user_email': 'lakshmi.naidu@email.com',
                'full_name': 'Lakshmi Naidu',
                'dob': '1990-07-22',
                'gender': 'Female',
                'phone': '+91 98765 22222',
                'address': '456 Oak Avenue, Visakhapatnam, Andhra Pradesh 530001',
                'emergency_contact': 'Ramesh Naidu, +91 98765 22223',
                'blood_group': 'B+',
                'allergies': 'None',
                'medical_history': 'Asthma (diagnosed 2015)'
            },
            {
                'user_email': 'ramesh.rao@email.com',
                'full_name': 'Ramesh Rao',
                'dob': '1978-11-02',
                'gender': 'Male',
                'phone': '+91 98765 33333',
                'address': '789 Pine Lane, Vijayawada, Andhra Pradesh 520001',
                'emergency_contact': 'Sita Rao, +91 98765 33334',
                'blood_group': 'O-',
                'allergies': 'Sulfa drugs',
                'medical_history': 'Diabetes Type 2, High Cholesterol'
            },
            {
                'user_email': 'sarada.gupta@email.com',
                'full_name': 'Sarada Gupta',
                'dob': '1995-05-10',
                'gender': 'Female',
                'phone': '+91 98765 44444',
                'address': '321 Cedar Road, Chennai, Tamil Nadu 600001',
                'emergency_contact': 'Venkatesh Gupta, +91 98765 44445',
                'blood_group': 'AB+',
                'allergies': 'Latex',
                'medical_history': 'Anemia (diagnosed 2020)'
            },
            {
                'user_email': 'mahesh.sharma@email.com',
                'full_name': 'Mahesh Sharma',
                'dob': '1982-09-18',
                'gender': 'Male',
                'phone': '+91 98765 55555',
                'address': '654 Birch Boulevard, Bengaluru, Karnataka 560001',
                'emergency_contact': 'Kavya Sharma, +91 98765 55556',
                'blood_group': 'A-',
                'allergies': 'Dairy',
                'medical_history': 'Gallstones (surgery 2018)'
            },
            {
                'user_email': 'padma.iyer@email.com',
                'full_name': 'Padma Iyer',
                'dob': '1988-12-25',
                'gender': 'Female',
                'phone': '+91 98765 66666',
                'address': '987 Elm Street, Pune, Maharashtra 411001',
                'emergency_contact': 'Srinivas Iyer, +91 98765 66667',
                'blood_group': 'O+',
                'allergies': 'None',
                'medical_history': 'None'
            },
            {
                'user_email': 'venkatesh.pillai@email.com',
                'full_name': 'Venkatesh Pillai',
                'dob': '1992-04-07',
                'gender': 'Male',
                'phone': '+91 98765 77777',
                'address': '147 Maple Drive, Ahmedabad, Gujarat 380001',
                'emergency_contact': 'Meena Pillai, +91 98765 77778',
                'blood_group': 'B-',
                'allergies': 'Aspirin',
                'medical_history': 'Migraine (diagnosed 2016)'
            },
            {
                'user_email': 'sita.yadav@email.com',
                'full_name': 'Sita Yadav',
                'dob': '1980-06-30',
                'gender': 'Female',
                'phone': '+91 98765 88888',
                'address': '258 Willow Way, Kolkata, West Bengal 700001',
                'emergency_contact': 'Nagesh Yadav, +91 98765 88889',
                'blood_group': 'AB-',
                'allergies': 'Shellfish',
                'medical_history': 'Thyroid disorder (diagnosed 2010)'
            },
        ]

        print("\nCreating patients (Telugu names)...")
        patients = []
        for data in patient_details:
            user = User.query.filter_by(email=data['user_email']).first()
            if not user:
                print(f"  ⚠️  User {data['user_email']} not found. Skipping.")
                continue

            existing_patient = Patient.query.filter_by(user_id=user.id).first()
            if existing_patient:
                patients.append(existing_patient)
                print(f"  ⏭️  Patient {data['full_name']} already exists.")
                continue

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
            print(f"  ✅ Created patient: {data['full_name']}")
        db.session.commit()

        # ----- 4. Create Appointments (past and future) -----
        print("\nCreating appointments...")
        today = datetime.now().date()

        appointment_data = [
            # Past appointments (completed)
            {'patient': 0, 'doctor': 0, 'date': today - timedelta(days=30), 'start': '09:00', 'end': '09:30', 'status': 'completed', 'notes': 'Routine checkup'},
            {'patient': 1, 'doctor': 1, 'date': today - timedelta(days=25), 'start': '10:00', 'end': '10:30', 'status': 'completed', 'notes': 'Migraine consultation'},
            {'patient': 2, 'doctor': 2, 'date': today - timedelta(days=20), 'start': '11:00', 'end': '11:30', 'status': 'completed', 'notes': 'Knee pain assessment'},
            {'patient': 3, 'doctor': 3, 'date': today - timedelta(days=15), 'start': '14:00', 'end': '14:30', 'status': 'completed', 'notes': 'Childhood vaccination'},
            {'patient': 4, 'doctor': 0, 'date': today - timedelta(days=10), 'start': '15:00', 'end': '15:30', 'status': 'completed', 'notes': 'Heart checkup'},
            {'patient': 5, 'doctor': 1, 'date': today - timedelta(days=5), 'start': '09:00', 'end': '09:30', 'status': 'completed', 'notes': 'Headache follow-up'},
            # Upcoming appointments (scheduled)
            {'patient': 0, 'doctor': 0, 'date': today + timedelta(days=2), 'start': '09:00', 'end': '09:30', 'status': 'scheduled', 'notes': 'Follow-up'},
            {'patient': 1, 'doctor': 2, 'date': today + timedelta(days=3), 'start': '10:30', 'end': '11:00', 'status': 'scheduled', 'notes': 'Back pain consultation'},
            {'patient': 2, 'doctor': 3, 'date': today + timedelta(days=5), 'start': '14:00', 'end': '14:30', 'status': 'scheduled', 'notes': 'Pediatric checkup'},
            {'patient': 3, 'doctor': 1, 'date': today + timedelta(days=7), 'start': '11:00', 'end': '11:30', 'status': 'scheduled', 'notes': 'Neurology consultation'},
            {'patient': 4, 'doctor': 0, 'date': today + timedelta(days=10), 'start': '15:00', 'end': '15:30', 'status': 'scheduled', 'notes': 'ECG test'},
            {'patient': 5, 'doctor': 2, 'date': today + timedelta(days=12), 'start': '09:00', 'end': '09:30', 'status': 'scheduled', 'notes': 'Fracture follow-up'},
            # Pending appointments (awaiting doctor confirmation)
            {'patient': 6, 'doctor': 3, 'date': today + timedelta(days=1), 'start': '16:00', 'end': '16:30', 'status': 'pending', 'notes': 'New patient consultation'},
            {'patient': 7, 'doctor': 0, 'date': today + timedelta(days=4), 'start': '09:30', 'end': '10:00', 'status': 'pending', 'notes': 'Heart murmur check'},
        ]

        for data in appointment_data:
            patient = patients[data['patient']]
            doctor = doctors[data['doctor']]
            appointment_date = data['date']
            start_time = datetime.strptime(data['start'], '%H:%M').time()
            end_time = datetime.strptime(data['end'], '%H:%M').time()

            existing = Appointment.query.filter_by(
                patient_id=patient.id,
                doctor_id=doctor.id,
                date=appointment_date,
                start_time=start_time
            ).first()
            if existing:
                continue

            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                date=appointment_date,
                start_time=start_time,
                end_time=end_time,
                status=data['status'],
                notes=data['notes']
            )
            db.session.add(appointment)
        db.session.commit()
        print(f"  ✅ Created {len(appointment_data)} appointments.")

        # ----- 5. Create Prescriptions (for completed appointments) -----
        print("\nCreating prescriptions...")
        completed_appointments = Appointment.query.filter_by(status='completed').limit(4).all()

        prescription_data = [
            {'medication': 'Amlodipine 5mg', 'dosage': '1 tablet daily', 'duration': '30 days', 'instructions': 'Take after breakfast', 'diagnosis': 'Hypertension'},
            {'medication': 'Sumatriptan 50mg', 'dosage': '1 tablet as needed', 'duration': '10 days', 'instructions': 'Take at onset of migraine', 'diagnosis': 'Migraine'},
            {'medication': 'Ibuprofen 400mg', 'dosage': '1 tablet every 8 hours', 'duration': '5 days', 'instructions': 'Take with food', 'diagnosis': 'Knee pain'},
            {'medication': 'Salbutamol inhaler', 'dosage': '2 puffs as needed', 'duration': '30 days', 'instructions': 'Use before exercise', 'diagnosis': 'Asthma'},
        ]

        for i, apt in enumerate(completed_appointments[:4]):
            if i >= len(prescription_data):
                break
            data = prescription_data[i]
            existing = Prescription.query.filter_by(
                patient_id=apt.patient_id,
                doctor_id=apt.doctor_id,
                appointment_id=apt.id
            ).first()
            if existing:
                continue
            prescription = Prescription(
                patient_id=apt.patient_id,
                doctor_id=apt.doctor_id,
                appointment_id=apt.id,
                diagnosis=data['diagnosis'],
                medication=data['medication'],
                dosage=data['dosage'],
                duration=data['duration'],
                instructions=data['instructions']
            )
            db.session.add(prescription)
        db.session.commit()
        print(f"  ✅ Created {len(completed_appointments[:4])} prescriptions.")

        # ----- 6. Create Bills (for completed appointments) -----
        print("\nCreating bills...")
        bill_appointments = Appointment.query.filter_by(status='completed').limit(3).all()
        bill_amounts = [1500, 2500, 800, 1200, 3000, 500]

        for i, apt in enumerate(bill_appointments[:6]):
            if i >= len(bill_amounts):
                break
            existing = Bill.query.filter_by(appointment_id=apt.id).first()
            if existing:
                continue
            bill = Bill(
                patient_id=apt.patient_id,
                appointment_id=apt.id,
                amount=bill_amounts[i],
                status='paid' if i % 2 == 0 else 'pending'
            )
            db.session.add(bill)
        db.session.commit()
        print(f"  ✅ Created {len(bill_appointments[:6])} bills.")

        # ----- 7. Create Insurance (for some patients) -----
        print("\nCreating insurance records...")
        insurance_patients = patients[:4]
        insurance_data = [
            {'provider': 'Star Health', 'policy_number': 'SH-2024-001', 'coverage': 'Family Plan - 5 Lakh', 'expiry': '2025-12-31'},
            {'provider': 'ICICI Lombard', 'policy_number': 'IL-2024-002', 'coverage': 'Individual Plan - 3 Lakh', 'expiry': '2025-06-30'},
            {'provider': 'Bajaj Allianz', 'policy_number': 'BA-2024-003', 'coverage': 'Senior Plan - 10 Lakh', 'expiry': '2026-01-15'},
            {'provider': 'HDFC Ergo', 'policy_number': 'HE-2024-004', 'coverage': 'Family Plan - 7 Lakh', 'expiry': '2025-09-30'},
        ]

        for i, patient in enumerate(insurance_patients):
            data = insurance_data[i]
            existing = Insurance.query.filter_by(patient_id=patient.id).first()
            if existing:
                continue
            insurance = Insurance(
                patient_id=patient.id,
                provider=data['provider'],
                policy_number=data['policy_number'],
                coverage_details=data['coverage'],
                expiry_date=datetime.strptime(data['expiry'], '%Y-%m-%d')
            )
            db.session.add(insurance)
        db.session.commit()
        print(f"  ✅ Created {len(insurance_patients)} insurance records.")

        print("\n✅ Seeding completed successfully!")

if __name__ == '__main__':
    seed_database()