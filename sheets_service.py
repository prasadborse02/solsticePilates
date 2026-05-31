"""Google Sheets operations for Solstice Pilates contacts/CRM."""

from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import CREDENTIALS_FILE, SPREADSHEET_ID

IST = timezone(timedelta(hours=5, minutes=30))

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
_sheets = build("sheets", "v4", credentials=_creds)

# Column layout: A=Name, B=Phone, C=Email, D=Last Call Date, E=Call Log, F=Notes
SHEET_RANGE = "Contacts"


def _get_all_rows():
    """Read all rows from the Contacts sheet."""
    result = _sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_RANGE}!A:F",
    ).execute()
    return result.get("values", [])


def find_contact(phone: str) -> dict | None:
    """Look up a contact by phone number.

    Args:
        phone: Phone number to search for.

    Returns:
        Contact dict if found, None otherwise.
    """
    rows = _get_all_rows()
    # Row 0 is headers
    for i, row in enumerate(rows[1:], start=2):
        # Pad row to 6 columns
        row += [""] * (6 - len(row))
        if row[1] == phone:
            return {
                "row_number": i,
                "name": row[0],
                "phone": row[1],
                "email": row[2],
                "last_call_date": row[3],
                "call_log": row[4],
                "notes": row[5],
            }
    return None


def create_contact(name: str, phone: str) -> dict:
    """Create a new contact in the sheet.

    Args:
        name: Caller's name.
        phone: Caller's phone number.

    Returns:
        Result dict with the created contact info.
    """
    # Check if contact already exists
    existing = find_contact(phone)
    if existing:
        return {"success": False, "message": f"Contact already exists: {existing['name']}"}

    today = datetime.now(IST).strftime("%Y-%m-%d %I:%M %p")
    _sheets.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_RANGE}!A:F",
        valueInputOption="USER_ENTERED",
        body={"values": [[name, phone, "", today, "", ""]]},
    ).execute()

    return {"success": True, "message": f"Created contact for {name}."}


def log_call(phone: str, summary: str) -> dict:
    """Log a call summary for a contact (looked up by phone).

    Args:
        phone: Phone number of the caller.
        summary: Brief summary of what the call was about.

    Returns:
        Result dict.
    """
    contact = find_contact(phone)
    if not contact:
        return {"success": False, "message": "Contact not found. Create contact first."}

    row = contact["row_number"]
    today = datetime.now(IST).strftime("%Y-%m-%d %I:%M %p")

    # Append to existing call log
    existing_log = contact.get("call_log", "")
    new_entry = f"[{today}] {summary}"
    updated_log = f"{existing_log}\n{new_entry}".strip() if existing_log else new_entry

    _sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_RANGE}!D{row}:E{row}",
        valueInputOption="USER_ENTERED",
        body={"values": [[today, updated_log]]},
    ).execute()

    return {"success": True, "message": f"Call logged for {contact['name']}."}
