# Solstice Pilates AI Receptionist

An AI-powered receptionist for Solstice Pilates studio that handles class bookings, availability checks, cancellations, and general inquiries via text chat and voice calls.

## Features

- **Class Booking** — Check availability, book, and cancel classes
- **Smart Suggestions** — Suggests alternatives when a class is full
- **Contact Management** — Tracks callers in Google Sheets with call logs
- **Human Handoff** — Routes billing disputes, refunds, and special requests to staff
- **Voice Calls** — Real-time voice interaction via Vapi integration

## Tech Stack

- **Backend:** Python, Flask
- **LLM:** Google Gemini 2.0 Flash (text chat), OpenAI GPT-4.1 (voice via Vapi)
- **Calendar:** Google Calendar API
- **CRM:** Google Sheets API
- **Voice:** Vapi AI
- **Auth:** Google Service Account

## Project Structure

```
config.py              — Shared configuration (IDs, studio info, pricing)
calendar_service.py    — Google Calendar operations (availability, booking, cancellation)
sheets_service.py      — Google Sheets operations (contacts, call logging)
agent.py               — Gemini-powered agent with tool calling (Phase 1)
app.py                 — Flask server, chat UI, and Vapi webhook (Phase 1 + 2)
seed_calendar.py       — Seeds test classes into Google Calendar
```

## Setup

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

- Create a Google Cloud project and enable Calendar + Sheets APIs
- Create a Service Account and download the JSON key as `credentials.json`
- Create a `.env` file:

```
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Set up Google resources

- Create a Google Calendar named "Solstice Pilates"
- Create a Google Sheet named "Solstice Pilates Contacts" with headers: `Name | Phone | Email | Last Call Date | Call Log | Notes`
- Share both with the service account email (found in `credentials.json`)
- Update `CALENDAR_ID` and `SPREADSHEET_ID` in `config.py`

### 4. Seed test data

```bash
python seed_calendar.py
```

### 5. Run

```bash
python app.py
```

Open http://localhost:8080 — use **Text** mode for chat or **Voice** mode for Vapi calls.

## Phase 2: Voice (Vapi)

To enable voice calls:

1. Create a Vapi account at [vapi.ai](https://vapi.ai)
2. Create an assistant with the tools defined in the Vapi dashboard
3. Expose the server publicly (e.g., `cloudflared tunnel --url http://localhost:8080`)
4. Point each tool's Server URL to `https://your-tunnel-url/vapi/webhook`
5. Add your Vapi Public Key and Assistant ID in `app.py`
