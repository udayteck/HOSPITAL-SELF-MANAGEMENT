"""
Run this script to insert sample patients and doctors with Indian names & numbers.
Execute: python add_sample_data.py
"""

import sys
import os
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash

# Add the current directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Patient, Doctor, GlobalSetting

# ========== INDIAN SAMPLE DATA ==========
indian_first_names = [
    "Aarav", "Vihaan", "Vivaan", "Ananya", "Diya", "Advik", "Kabir", "Reyansh", "Sai", "Arjun",
    "Ishita", "Myra", "Shaurya", "Aditi", "Sara", "Rudra", "Aadhya", "Dhruv", "Anvi", "Krishna",
    "Shreya", "Rohan", "Priya", "Raj", "Simran", "Amit", "Neha", "Sanjay", "Pooja", "Vikram",
    "Deepika", "Rahul", "Anjali", "Suresh", "Kavita", "Mahesh", "Swati", "Sunil", "Geeta", "Ashok"
]

indian_last_names = [
    "Sharma", "Verma", "Gupta", "Kumar", "Singh", "Reddy", "Yadav", "Jha", "Malhotra",
    "Mehta", "Choudhary", "Rajput", "Thakur", "Mishra", "Joshi", "Nair", "Menon", "Pillai", "Bose",
    "Das", "Ghosh", "Sen", "Bannerjee", "Chatterjee", "Mukherjee", "Sarkar", "Roy", "Chopra", "Khanna"
]

specialties = [
    "Cardiology", "Dermatology", "Pediatrics", "Orthopedics", "Neurology", "Gynaecology", "Urology",
    "Ophthalmology", "ENT", "Psychiatry", "Dentistry", "Radiology", "Anesthesiology", "Emergency Medicine",
    "Family Medicine", "Internal Medicine", "Pathology", "Pulmonology", "Rheumatology", "Endocrinology"
]

def generate_indian_phone():
    """Generate a valid Indian mobile number starting with 6,7,8,9 and 10 digits total."""
    first_digit = random.choice(['6','7','8','9'])
    rest = ''.join([str(random.randint(0,9)) for _ in range(9)])
    return f"+91 {first_digit}{rest}"

def add_sample_patients(count=15):
    print(f"Adding {count} sample patients (Indian names)...")
    existing_patient_emails = set(p.user.email for p in Patient.query.all() if p.user)
    added = 0
    for i in range(count):
        first = random.choice(indian_first_names)
        last = random.choice(indian_last_names)
        full_name = f"{first} {last}"
        # Email: firstname.lastname.random@example.com
        email = f"{first.lower()}.{last.lower()}{random.randint(1,999)}@example.com"
        if email in existing_patient_emails:
            continue
        phone = generate_indian_phone()
        # Create user
        user = User(
            email=email,
            role='patient',
            is_active=True
        )
        user.set_password("password123")  # default password for all sample patients
        db.session.add(user)
        db.session.flush()
        patient = Patient(
            user_id=user.id,
            full_name=full_name,
            phone=phone,
            date_of_birth=datetime(random.randint(1950, 2010), random.randint(1,12), random.randint(1,28))
        )
        db.session.add(patient)
        existing_patient_emails.add(email)
        added += 1
        if added % 5 == 0:
            db.session.commit()
    db.session.commit()
    print(f"Added {added} patients with Indian details.")

def add_sample_doctors(count=20):
    print(f"Adding {count} sample doctors (Indian names)...")
    existing_doctor_emails = set(d.user.email for d in Doctor.query.all() if d.user)
    added = 0
    for i in range(count):
        first = random.choice(indian_first_names)
        last = random.choice(indian_last_names)
        full_name = f"Dr. {first} {last}"
        email = f"dr.{first.lower()}.{last.lower()}@skdhospital.in"
        if email in existing_doctor_emails:
            email = f"dr.{first.lower()}.{last.lower()}{random.randint(1,100)}@skdhospital.in"
        specialty = random.choice(specialties)
        phone = generate_indian_phone()
        user = User(
            email=email,
            role='doctor',
            is_active=True
        )
        user.set_password("doctor123")  # default password for doctors
        db.session.add(user)
        db.session.flush()
        doctor = Doctor(
            user_id=user.id,
            full_name=full_name,
            specialty=specialty,
            phone=phone
        )
        db.session.add(doctor)
        existing_doctor_emails.add(email)
        added += 1
        if added % 5 == 0:
            db.session.commit()
    db.session.commit()
    print(f"Added {added} doctors with Indian details.")

def main():
    app = create_app()
    with app.app_context():
        patient_count = Patient.query.count()
        doctor_count = Doctor.query.count()
        print(f"Current patients: {patient_count}, doctors: {doctor_count}")
        if patient_count < 5:
            add_sample_patients(15)
        else:
            print("Patients already exist, skipping patient sample.")
        if doctor_count < 5:
            add_sample_doctors(20)
        else:
            print("Doctors already exist, skipping doctor sample.")
        print("Sample data addition complete.")

if __name__ == "__main__":
    main()