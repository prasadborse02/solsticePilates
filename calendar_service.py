"""Google Calendar operations for Solstice Pilates."""

import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import CREDENTIALS_FILE, CALENDAR_ID, TIMEZONE

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
_calendar = build("calendar", "v3", credentials=_creds)


def _parse_booking_data(event):
    """Extract booking data from event description JSON."""
    description = event.get("description", "")
    try:
        data = json.loads(description)
        return data
    except (json.JSONDecodeError, TypeError):
        return {"maxCapacity": 8, "bookings": []}


def _format_time(dt_str):
    """Parse an ISO datetime string and return a readable time like '6:00 PM'."""
    dt = datetime.fromisoformat(dt_str)
    return dt.strftime("%-I:%M %p")


def _format_event(event):
    """Format a calendar event into a readable dict for the LLM."""
    data = _parse_booking_data(event)
    start = event["start"].get("dateTime", event["start"].get("date"))
    end = event["end"].get("dateTime", event["end"].get("date"))
    booked = len(data.get("bookings", []))
    capacity = data.get("maxCapacity", 8)
    return {
        "event_id": event["id"],
        "class_name": event.get("summary", "Unknown Class"),
        "start_time": _format_time(start),
        "end_time": _format_time(end),
        "date": datetime.fromisoformat(start).strftime("%A, %B %d"),
        "spots_taken": booked,
        "max_capacity": capacity,
        "spots_left": capacity - booked,
        "is_full": booked >= capacity,
    }


def get_classes_on_date(date_str: str) -> list[dict]:
    """Get all classes on a given date.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        List of class info dicts with availability.
    """
    start = datetime.fromisoformat(f"{date_str}T00:00:00")
    end = start + timedelta(days=1)

    events = _calendar.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start.isoformat() + "+05:30",
        timeMax=end.isoformat() + "+05:30",
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return [_format_event(e) for e in events.get("items", [])]


def get_class_details(event_id: str) -> dict:
    """Get full details of a specific class including who's booked.

    Args:
        event_id: Google Calendar event ID.

    Returns:
        Class info dict with bookings list.
    """
    event = _calendar.events().get(
        calendarId=CALENDAR_ID, eventId=event_id
    ).execute()

    info = _format_event(event)
    data = _parse_booking_data(event)
    info["bookings"] = data.get("bookings", [])
    return info


def book_class(event_id: str, name: str, phone: str) -> dict:
    """Book a person into a class."""
    # Reject placeholder names
    invalid = {"unknown", "n/a", "none", "john doe", "jane doe", "placeholder", ""}
    if name.lower().strip() in invalid or phone.lower().strip() in invalid:
        return {"success": False, "message": "Please ask the caller for their real name and phone number before booking."}

    event = _calendar.events().get(
        calendarId=CALENDAR_ID, eventId=event_id
    ).execute()

    data = _parse_booking_data(event)
    bookings = data.get("bookings", [])
    capacity = data.get("maxCapacity", 8)

    # Check if already booked
    for b in bookings:
        if b.get("phone") == phone:
            return {"success": False, "message": f"{name} is already booked in this class."}

    # Check capacity
    if len(bookings) >= capacity:
        return {"success": False, "message": "This class is full."}

    # Add booking
    bookings.append({"name": name, "phone": phone})
    data["bookings"] = bookings
    event["description"] = json.dumps(data, indent=2)

    _calendar.events().update(
        calendarId=CALENDAR_ID, eventId=event_id, body=event
    ).execute()

    spots_left = capacity - len(bookings)
    return {
        "success": True,
        "message": f"Booked {name} into the class. {spots_left} spot(s) remaining.",
    }


def cancel_booking(event_id: str, phone: str) -> dict:
    """Cancel a booking by phone number.

    Args:
        event_id: Google Calendar event ID.
        phone: Phone number of the person to remove.

    Returns:
        Result dict with success status and message.
    """
    event = _calendar.events().get(
        calendarId=CALENDAR_ID, eventId=event_id
    ).execute()

    data = _parse_booking_data(event)
    bookings = data.get("bookings", [])

    # Find and remove booking by phone
    updated = [b for b in bookings if b.get("phone") != phone]
    if len(updated) == len(bookings):
        return {"success": False, "message": "No booking found with that phone number."}

    removed_name = next(b["name"] for b in bookings if b.get("phone") == phone)
    data["bookings"] = updated
    event["description"] = json.dumps(data, indent=2)

    _calendar.events().update(
        calendarId=CALENDAR_ID, eventId=event_id, body=event
    ).execute()

    return {"success": True, "message": f"Cancelled booking for {removed_name}."}


def find_alternative_classes(class_type: str, date_str: str) -> list[dict]:
    """Find classes with open spots, useful when the requested class is full.

    Args:
        class_type: Type of class (e.g., 'Reformer', 'Mat Pilates').
        date_str: Date in YYYY-MM-DD format.

    Returns:
        List of available class dicts (only classes with spots left).
    """
    all_classes = get_classes_on_date(date_str)
    available = [
        c for c in all_classes
        if not c["is_full"] and class_type.lower() in c["class_name"].lower()
    ]
    return available
