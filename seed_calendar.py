"""Seed the Solstice Pilates calendar with test classes."""

import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "ed92d2fca5bfdb180f154766465b5f78c822b566d8c125d74b3a8e2171f045b8@group.calendar.google.com"
TIMEZONE = "Asia/Kolkata"

creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
calendar = build("calendar", "v3", credentials=creds)


def create_class(summary, start_dt, duration_mins=60, max_capacity=8, bookings=None):
    """Create a class event on the calendar.

    Bookings are stored as JSON in the description field:
    {"maxCapacity": 8, "bookings": [{"name": "Sara", "phone": "415-555-0190"}, ...]}
    """
    end_dt = start_dt + timedelta(minutes=duration_mins)
    booking_data = {
        "maxCapacity": max_capacity,
        "bookings": bookings or [],
    }
    event = {
        "summary": summary,
        "description": json.dumps(booking_data, indent=2),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
    }
    result = calendar.events().insert(
        calendarId=CALENDAR_ID, body=event, sendUpdates="none"
    ).execute()
    booked = len(bookings) if bookings else 0
    print(f"  ✓ {summary} | {start_dt.strftime('%a %b %d %I:%M %p')} | {booked}/{max_capacity} booked")
    return result


# --- Build schedule for the next 7 days ---
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

print("Seeding Solstice Pilates classes...\n")

for day_offset in range(7):
    day = today + timedelta(days=day_offset)
    day_name = day.strftime("%A %b %d")
    print(f"--- {day_name} ---")

    # Morning: 7 AM Mat Pilates (beginner-friendly, larger class)
    create_class(
        "Morning Mat Pilates",
        day.replace(hour=7),
        duration_mins=60,
        max_capacity=12,
        bookings=[
            {"name": "Alice Wong", "phone": "415-555-0101"},
            {"name": "Bob Chen", "phone": "415-555-0102"},
            {"name": "Carla Davis", "phone": "415-555-0103"},
        ] if day_offset < 3 else None,
    )

    # 10 AM Reformer
    create_class(
        "Reformer",
        day.replace(hour=10),
        duration_mins=60,
        max_capacity=8,
        bookings=[
            {"name": "Dana Lee", "phone": "415-555-0104"},
            {"name": "Evan Park", "phone": "415-555-0105"},
            {"name": "Fiona Grant", "phone": "415-555-0106"},
            {"name": "Grace Kim", "phone": "415-555-0107"},
            {"name": "Henry Tran", "phone": "415-555-0108"},
        ] if day_offset == 0
        else ([
            {"name": "Dana Lee", "phone": "415-555-0104"},
            {"name": "Evan Park", "phone": "415-555-0105"},
        ] if day_offset < 4 else None),
    )

    # 4 PM Tower Class (smaller, specialized)
    create_class(
        "Tower Pilates",
        day.replace(hour=16),
        duration_mins=60,
        max_capacity=6,
        bookings=[
            {"name": "Iris Moon", "phone": "415-555-0109"},
            {"name": "Jake Hill", "phone": "415-555-0110"},
        ] if day_offset % 2 == 0 else None,
    )

    # 6 PM Reformer (popular evening slot)
    six_pm_bookings = None
    if day_offset == 0:
        # TODAY's 6 PM is FULL (8/8)
        six_pm_bookings = [
            {"name": "Kate Bell", "phone": "415-555-0111"},
            {"name": "Liam Fox", "phone": "415-555-0112"},
            {"name": "Mia Cruz", "phone": "415-555-0113"},
            {"name": "Noah Patel", "phone": "415-555-0114"},
            {"name": "Olivia Shah", "phone": "415-555-0115"},
            {"name": "Pete Young", "phone": "415-555-0116"},
            {"name": "Quinn Adams", "phone": "415-555-0117"},
            {"name": "Rosa Diaz", "phone": "415-555-0118"},
        ]
    elif day_offset == 1:
        # TOMORROW's 6 PM has 1 spot left (7/8)
        six_pm_bookings = [
            {"name": "Kate Bell", "phone": "415-555-0111"},
            {"name": "Liam Fox", "phone": "415-555-0112"},
            {"name": "Mia Cruz", "phone": "415-555-0113"},
            {"name": "Noah Patel", "phone": "415-555-0114"},
            {"name": "Olivia Shah", "phone": "415-555-0115"},
            {"name": "Pete Young", "phone": "415-555-0116"},
            {"name": "Quinn Adams", "phone": "415-555-0117"},
        ]
    elif day_offset < 5:
        six_pm_bookings = [
            {"name": "Kate Bell", "phone": "415-555-0111"},
            {"name": "Liam Fox", "phone": "415-555-0112"},
            {"name": "Mia Cruz", "phone": "415-555-0113"},
        ]

    create_class(
        "Reformer",
        day.replace(hour=18),
        duration_mins=60,
        max_capacity=8,
        bookings=six_pm_bookings,
    )

    # 7 PM Reformer (alternative evening slot)
    create_class(
        "Reformer",
        day.replace(hour=19),
        duration_mins=60,
        max_capacity=8,
        bookings=[
            {"name": "Sam Torres", "phone": "415-555-0119"},
            {"name": "Uma Rao", "phone": "415-555-0120"},
        ] if day_offset < 3 else None,
    )

    print()

print("Done! Calendar seeded with 7 days of classes.")
print("\nKey test scenarios:")
print(f"  - Today's 6 PM Reformer: FULL (8/8)")
print(f"  - Tomorrow's 6 PM Reformer: Almost full (7/8, 1 spot)")
print(f"  - Today's 7 PM Reformer: Has space (2/8) — good alternative to suggest")
print(f"  - Morning Mat Pilates: Lots of room (3/12)")
