# main.py
import json
import logging
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from config import settings
from database import get_db, engine
from models import Base, Doctor, Patient, Appointment
from sqlalchemy.orm import Session
from slot_generator import generate_slots
from scheduler import get_slots_for_doctor

logging.basicConfig(level=logging.INFO)
app = FastAPI()

# ensure tables exist (for local dev)
Base.metadata.create_all(bind=engine)

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
TWILIO_FROM = settings.TWILIO_WHATSAPP_NUMBER

GREETINGS = {"hi", "hello", "hai"}

# helper: normalize Twilio 'To'/'From' phoneformat to E.164 (strip 'whatsapp:' prefix)
def normalize_number(raw):
    if not raw:
        return None
    return raw.replace("whatsapp:", "").strip()

def send_template_message(to, template_name, template_vars):
    """
    Send a Twilio Content Template message via the 'content' parameter.
    template_vars: list of strings corresponding to template body placeholders in order
    e.g. ["Dr. John"] or ["Patient Name", "Dr. John", "01-Sep 10:00 AM"]
    """
    components = []
    if template_vars:
        # build parameters for body
        params = [{"type": "text", "text": v} for v in template_vars]
        components.append({"type": "body", "parameters": params})

    content = [{
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": settings.TEMPLATE_LANG},
            "components": components
        }
    }]

    msg = twilio_client.messages.create(
        from_=TWILIO_FROM,
        to=f"whatsapp:{to}",
        content=content
    )
    logging.info("Sent template '%s' SID=%s to=%s", template_name, getattr(msg, "sid", None), to)
    return msg

def send_list_picker(to, header_text, body_text, footer_text, slots):
    """
    Send an interactive List Picker via Twilio content payload.
    `slots` is a list of dicts with keys: id, title, description
    """
    # Build sections (single section)
    rows = []
    for s in slots:
        rows.append({
            "id": s["id"],
            "title": s["title"],
            "description": s.get("description", "")
        })
    sections = [
        {
            "title": "Available Slots",
            "rows": rows
        }
    ]

    interactive = {
        "type": "list",
        "header": {"type": "text", "text": header_text},
        "body": {"text": body_text},
        "footer": {"text": footer_text},
        "action": {"button": "Select Slot", "sections": sections}
    }

    content = [{
        "type": "interactive",
        "interactive": interactive
    }]

    msg = twilio_client.messages.create(
        from_=TWILIO_FROM,
        to=f"whatsapp:{to}",
        content=content
    )
    logging.info("Sent list picker to=%s sid=%s", to, getattr(msg, "sid", None))
    return msg

@app.post("/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Twilio will POST form-encoded fields. We'll parse common keys, including interactive payloads.
    """
    form = await request.form()
    data = {k: form.get(k) for k in form.keys()}
    logging.info("Incoming webhook form: %s", data)

    raw_from = data.get("From")  # 'whatsapp:+9198...'
    raw_to = data.get("To")
    body = (data.get("Body") or "").strip()

    from_number = normalize_number(raw_from)
    to_number = normalize_number(raw_to)

    if not from_number or not to_number:
        logging.error("Missing from/to in webhook")
        return PlainTextResponse("Missing from/to", status_code=400)

    # helper to get doctor record by to_number (E.164)
    doctor = db.query(Doctor).filter(Doctor.phone_number == to_number).first()
    doctor_name = doctor.name if doctor else "Doctor"

    # 1) Detect interactive selection payloads (List Picker returns interactive with selected_row_id)
    # Twilio may send 'Interactive' JSON in fields like 'Interactive', 'interactive', or nested; also may populate Body with selected title.
    selected_row_id = None
    interactive_raw = data.get("Interactive") or data.get("interactive") or data.get("interactive_response") or data.get("InteractiveBody")
    # Also check for 'ListSelection' style keys or 'ListResponse'
    if interactive_raw:
        try:
            parsed = json.loads(interactive_raw)
            # try common shapes
            # Twilio sandbox/console sometimes uses parsed['type'] etc; but in case we have a select row id:
            # check 'list_reply' or 'list' keys
            # We'll try multiple possibilities:
            list_reply = parsed.get("list_reply") or parsed.get("list") or parsed.get("action") or parsed.get("selected_option")
            # try a few paths:
            if isinstance(list_reply, dict):
                # e.g. {"id": "...", "title": "..."}
                selected_row_id = list_reply.get("id") or list_reply.get("rowId") or list_reply.get("selected_row_id")
            else:
                # maybe parsed directly gives id
                selected_row_id = parsed.get("id") or parsed.get("rowId")
        except Exception:
            # not JSON or different shape
            selected_row_id = interactive_raw

    # Another place Twilio may send the selected id is a specific field 'ListReply' or 'ButtonPayload'
    for key in ("ListReply", "list_reply", "SelectedRowId", "selected_row_id", "ButtonPayload", "button_payload"):
        if not selected_row_id and data.get(key):
            try:
                parsed = json.loads(data.get(key))
                selected_row_id = parsed.get("id") or parsed.get("payload") or parsed.get("title") or data.get(key)
            except Exception:
                selected_row_id = data.get(key)

    logging.info("Detected selected_row_id: %s", selected_row_id)

    # 2) If it's a greeting
    if body.lower() in GREETINGS:
        # Send greeting template; it expects one placeholder: doctor name
        send_template_message(to=from_number, template_name=settings.GREETING_TEMPLATE_NAME, template_vars=[doctor_name])
        return PlainTextResponse("Greeting template sent")

    # 3) If the webhook indicates a quick-reply button was pressed (we expect button ids)
    # Twilio may post the button id in 'ButtonPayload' OR Body may contain the visible label.
    button_id = data.get("ButtonPayload") or data.get("button_payload") or data.get("buttonId") or data.get("postback")
    if button_id:
        button_id = button_id.strip()
        logging.info("Received button id: %s", button_id)
        # match your IDs
        if button_id == "schedule_appointment":
            # Generate slots and send List Picker to user
            slots = get_slots_for_doctor(doctor.phone_number if doctor else None, days=3)
            # use only id/title/description
            simple_slots = [{"id": s["id"], "title": s["title"], "description": s["description"]} for s in slots]
            send_list_picker(to=from_number,
                             header_text=f"Available slots for {doctor_name}",
                             body_text="Please choose one of the options below to schedule your appointment:",
                             footer_text="Powered by domain.in",
                             slots=simple_slots)
            return PlainTextResponse("List picker sent for scheduling")

        elif button_id == "reschedule_appoinment":
            # Check if patient has existing appointment
            patient = db.query(Patient).filter(Patient.phone_number == from_number).first()
            appt = None
            if patient:
                appt = db.query(Appointment).filter(Appointment.patient_id == patient.id, Appointment.doctor_id == (doctor.id if doctor else None), Appointment.status == "scheduled").first()
            if not appt:
                # send plain text error
                twilio_client.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{from_number}",
                                              body="Sorry, we couldn't find any existing appointments linked to your number.")
                return PlainTextResponse("No appointment found for reschedule")
            # else offer slots to reschedule
            slots = get_slots_for_doctor(doctor.phone_number if doctor else None, days=3)
            simple_slots = [{"id": s["id"], "title": s["title"], "description": s["description"]} for s in slots]
            send_list_picker(to=from_number,
                             header_text=f"Reschedule for {doctor_name}",
                             body_text=f"Your current appointment: {appt.slot_time}. Please select a new slot:",
                             footer_text="Select a new slot",
                             slots=simple_slots)
            return PlainTextResponse("List picker sent for reschedule")

        elif button_id == "cancel_appoinmnet":
            # Show patient's existing appointments (list) to cancel
            patient = db.query(Patient).filter(Patient.phone_number == from_number).first()
            appts = []
            if patient:
                appts_q = db.query(Appointment).filter(Appointment.patient_id == patient.id, Appointment.status == "scheduled").all()
                for a in appts_q:
                    appts.append({"id": f"cancel_{a.id}", "title": a.slot_time, "description": f"Doctor: {a.doctor.name if a.doctor else ''}"})
            if not appts:
                twilio_client.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{from_number}",
                                              body="No scheduled appointments found to cancel.")
                return PlainTextResponse("No appointments to cancel")
            # send list picker of appointments to cancel
            send_list_picker(to=from_number,
                             header_text=f"Your Appointments",
                             body_text="Select an appointment to cancel:",
                             footer_text="Cancel an appointment",
                             slots=appts)
            return PlainTextResponse("List picker sent for cancellation")

    # 4) If user selected a slot (selected_row_id starts with slot_ -> scheduling or rescheduling)
    if selected_row_id and str(selected_row_id).startswith("slot_"):
        # map the selected id back to a slot (we used generate_slots so reproduce)
        all_slots = generate_slots(days=3, slots_per_day=4)
        chosen = next((s for s in all_slots if s["id"] == selected_row_id), None)
        if not chosen:
            twilio_client.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{from_number}",
                                          body="Sorry, could not find the selected slot. Please try again.")
            return PlainTextResponse("Slot not found")

        # retrieve or create patient record
        patient = db.query(Patient).filter(Patient.phone_number == from_number).first()
        if not patient:
            patient = Patient(name=None, phone_number=from_number)
            db.add(patient)
            db.commit()
            db.refresh(patient)

        # create appointment
        appt = Appointment(patient_id=patient.id, doctor_id=doctor.id if doctor else None, slot_time=f"{chosen['title']} ({chosen['description']})", status="scheduled")
        db.add(appt)
        db.commit()
        db.refresh(appt)

        # Ask for patient name if unknown (we requested name earlier in greeting template)
        # If patient.name is None we instruct them to reply with their name; otherwise confirm using template
        if not patient.name:
            twilio_client.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{from_number}",
                                          body=f"Thanks — your slot {chosen['title']} is reserved. Please reply with your full name to confirm the booking.")
            return PlainTextResponse("Asked for patient name")
        else:
            # send appointment scheduled template: variables patient_name, doctor_name, slot
            send_template_message(to=from_number, template_name=settings.APPT_SCHEDULED_TEMPLATE,
                                  template_vars=[patient.name, doctor_name, f"{chosen['title']} ({chosen['description']}"])
            return PlainTextResponse("Appointment scheduled and template sent")

    # 5) If the user replies with a plain name (we can detect as a simple non-command text and patient has a pending appointment without name)
    if body and not body.lower() in GREETINGS:
        # check if patient exists and has a recent appointment with name empty
        patient = db.query(Patient).filter(Patient.phone_number == from_number).first()
        if patient:
            # find the most recent appointment with empty patient name or patient.name is None
            appt = db.query(Appointment).filter(Appointment.patient_id == patient.id).order_by(Appointment.created_at.desc()).first()
            if appt and (not patient.name or patient.name.strip() == ""):
                # update patient name
                patient.name = body.strip()
                db.add(patient)
                db.commit()
                # send confirmation template
                send_template_message(to=from_number, template_name=settings.APPT_SCHEDULED_TEMPLATE,
                                      template_vars=[patient.name, doctor_name, appt.slot_time])
                return PlainTextResponse("Patient name saved and confirmation sent")

    # default fallback
    twilio_client.messages.create(from_=TWILIO_FROM, to=f"whatsapp:{from_number}",
                                  body="Sorry, I didn't understand that. Reply with 'Hi' to start.")
    return PlainTextResponse("fallback")
