# slot_generator.py
from datetime import datetime, timedelta
import uuid

def generate_slots(start_date=None, days=3, slots_per_day=4, start_hour=9, interval_minutes=60):
    """
    Generate available slots as a list of dicts with keys: id, title, description
    - start_date: datetime.date or None -> defaults to today
    - days: how many days to generate
    - slots_per_day: number of slots each day
    """
    if start_date is None:
        start_date = datetime.utcnow().date()
    slots = []
    for d in range(days):
        date = start_date + timedelta(days=d)
        for s in range(slots_per_day):
            hour = start_hour + s * (interval_minutes // 60)
            dt = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour)
            slot_id = f"slot_{date.isoformat()}_{hour:02d}_{s}"
            title = dt.strftime("%d-%b %I:%M %p")
            description = dt.strftime("%A, %d %b %Y")
            slots.append({
                "id": slot_id,
                "title": title,
                "description": description,
                "datetime": dt.isoformat()
            })
    return slots
