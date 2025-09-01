# config.py
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field("sqlite:///./appointments.db", env="DATABASE_URL")
    TWILIO_ACCOUNT_SID: str = Field(..., env="TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = Field(..., env="TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER: str = Field("whatsapp:+14155238886", env="TWILIO_WHATSAPP_NUMBER")
    GREETING_TEMPLATE_NAME: str = Field("greeting_message", env="GREETING_TEMPLATE_NAME")
    TEMPLATE_LANG: str = Field("en", env="TEMPLATE_LANG")
    APPT_SCHEDULED_TEMPLATE: str = Field("appointment_scheduled", env="APPT_SCHEDULED_TEMPLATE")
    APPT_RESCHEDULED_TEMPLATE: str = Field("appointment_rescheduled", env="APPT_RESCHEDULED_TEMPLATE")
    APPT_CANCELLED_TEMPLATE: str = Field("appointment_cancelled", env="APPT_CANCELLED_TEMPLATE")

    class Config:
        env_file = ".env"

settings = Settings()
