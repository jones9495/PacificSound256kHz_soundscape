# seed_db.py
from database import engine
from models import Base, Doctor
from sqlalchemy.orm import Session
from config import settings

def seed():
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        # Add sample doctors (use E.164 numbers WITHOUT 'whatsapp:' prefix)
        sample = [
            {"name": "Dr. John Doe", "phone": "+14155551234"},
            {"name": "Dr. Jane Smith", "phone": "+14155556789"},
        ]
        for s in sample:
            exists = db.query(Doctor).filter(Doctor.phone_number == s["phone"]).first()
            if not exists:
                doc = Doctor(name=s["name"], phone_number=s["phone"])
                db.add(doc)
        db.commit()
    print("DB seeded (doctors).")

if __name__ == "__main__":
    seed()
