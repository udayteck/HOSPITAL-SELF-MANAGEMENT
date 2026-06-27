"""
Run this script to add sample availability slots for all doctors.
Execute: python add_sample_slots.py
"""

import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Doctor, Availability, GlobalSetting

def add_availability_for_doctor(doctor_id, days_ahead=7):
    """Create 30-min slots from 9 AM to 5 PM for next `days_ahead` days"""
    slot_duration = int(GlobalSetting.get('slot_duration_minutes', 30))
    start_hour = 9
    end_hour = 17
    added = 0
    
    for day_offset in range(days_ahead):
        target_date = datetime.utcnow().date() + timedelta(days=day_offset)
        # Skip weekends if desired (optional)
        if target_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            continue
        
        start_dt = datetime.combine(target_date, datetime.strptime(f"{start_hour}:00", "%H:%M").time())
        end_dt = datetime.combine(target_date, datetime.strptime(f"{end_hour}:00", "%H:%M").time())
        
        current = start_dt
        while current + timedelta(minutes=slot_duration) <= end_dt:
            slot_end = current + timedelta(minutes=slot_duration)
            # Check if slot already exists to avoid duplicates
            existing = Availability.query.filter_by(
                doctor_id=doctor_id,
                slot_start=current,
                slot_end=slot_end
            ).first()
            if not existing:
                slot = Availability(
                    doctor_id=doctor_id,
                    slot_start=current,
                    slot_end=slot_end,
                    is_booked=False
                )
                db.session.add(slot)
                added += 1
            current = slot_end
    return added

def main():
    app = create_app()
    with app.app_context():
        doctors = Doctor.query.all()
        if not doctors:
            print("No doctors found. Run add_sample_data.py first.")
            return
        
        total_slots = 0
        for doctor in doctors:
            count = add_availability_for_doctor(doctor.id, days_ahead=7)
            total_slots += count
            print(f"Added {count} slots for Dr. {doctor.full_name}")
        db.session.commit()
        print(f"\n✅ Total {total_slots} availability slots added for {len(doctors)} doctors.")

if __name__ == "__main__":
    main()