"""Shared configuration for Solstice Pilates AI Receptionist."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Google API ---
CREDENTIALS_FILE = "credentials.json"
CALENDAR_ID = "ed92d2fca5bfdb180f154766465b5f78c822b566d8c125d74b3a8e2171f045b8@group.calendar.google.com"
SPREADSHEET_ID = "1gXAjnwZZP6HEjPL2WuuZqdlURronwJ40bnNM-Jv5Pnw"
TIMEZONE = "Asia/Kolkata"

# --- LLM ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MODEL_FAST = "llama-3.1-8b-instant"

# --- Studio Info ---
STUDIO_NAME = "Solstice Pilates"
STUDIO_HOURS = "Monday–Saturday: 7 AM – 8 PM, Sunday: 8 AM – 6 PM"
STUDIO_ADDRESS = "123 Sunrise Blvd, San Francisco, CA 94110"
STUDIO_PHONE = "(415) 555-0100"

CLASS_TYPES = {
    "reformer": {
        "name": "Reformer",
        "description": "Full-body workout on the Pilates reformer machine",
        "duration_mins": 60,
        "default_capacity": 8,
    },
    "morning_mat_pilates": {
        "name": "Morning Mat Pilates",
        "description": "Beginner-friendly mat-based Pilates class",
        "duration_mins": 60,
        "default_capacity": 12,
    },
    "tower_pilates": {
        "name": "Tower Pilates",
        "description": "Advanced class using the Pilates tower/Cadillac",
        "duration_mins": 60,
        "default_capacity": 6,
    },
}

PRICING = {
    "single_class": "$35",
    "5_class_pack": "$150 (saves $25)",
    "10_class_pack": "$280 (saves $70)",
    "monthly_unlimited": "$250/month",
    "drop_in": "$40",
}
