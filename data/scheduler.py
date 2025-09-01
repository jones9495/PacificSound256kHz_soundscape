# scheduler.py
# Small helper that can be used to produce scheduled jobs later.
# For now it's a convenience wrapper around slot_generator.
from slot_generator import generate_slots

def get_slots_for_doctor(doctor_phone, days=3):
    # in a real app you might vary by doctor schedule; here we return a generic list
    return generate_slots(days=days, slots_per_day=4)
