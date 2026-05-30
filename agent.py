"""Solstice Pilates AI Receptionist — LLM Agent with tool calling."""

import json
import time
from datetime import datetime, timedelta
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    STUDIO_NAME, STUDIO_HOURS, STUDIO_ADDRESS, STUDIO_PHONE,
    CLASS_TYPES, PRICING, TIMEZONE,
)
import calendar_service
import sheets_service

# --- Gemini Client ---
client = genai.Client(api_key=GEMINI_API_KEY)

# --- System Prompt ---
TODAY = datetime.now().strftime("%A, %B %d, %Y")
TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%A, %B %d, %Y")

SYSTEM_PROMPT = f"""You are the friendly AI receptionist for {STUDIO_NAME}, a small pilates studio.

Today is {TODAY}. The current timezone is {TIMEZONE}.

## Studio Info
- Address: {STUDIO_ADDRESS}
- Phone: {STUDIO_PHONE}
- Hours: {STUDIO_HOURS}

## Classes Offered
{json.dumps({k: {"name": v["name"], "description": v["description"], "duration": f"{v['duration_mins']} min"} for k, v in CLASS_TYPES.items()}, indent=2)}

## Pricing
{json.dumps(PRICING, indent=2)}

## Your Behavior
- Be warm, friendly, and concise — like a real receptionist, not a robot.
- Keep responses short. Don't over-explain.
- When someone asks about a class, ALWAYS check the calendar first. Never guess availability.
- When booking, you MUST collect the caller's name and phone number before confirming.
- When a class is full, proactively suggest alternatives on the same day.
- After completing a booking or resolving a query, ask "Anything else?" to keep the conversation going.
- Always confirm booking details back to the caller before finalizing.
- When cancelling, always look up by phone number.

## What You Handle
- Booking a class
- Changing or cancelling a booking
- Checking class availability
- Questions about pricing, hours, class types, location
- "I'm running late" — acknowledge it warmly, no action needed
- General studio questions

## What You Hand Off to a Human
For these, say something like "Let me get a manager on the line for you" or "I'll have someone from the team call you back about that":
- Billing complaints or charge disputes
- Refund requests
- Birthday party or private event inquiries
- Medical or injury concerns
- Anything you're unsure about

## Tool Usage
- Use get_classes_on_date to check availability. Pass dates as YYYY-MM-DD.
- Use find_alternative_classes when a class is full.
- Use book_class to confirm a booking (requires event_id, name, phone).
- Use cancel_booking to cancel (requires event_id and phone).
- Use find_contact to look up returning callers.
- Use create_contact to save new callers.
- Use log_call at the END of every conversation to record what happened.

## Date Handling
- "today" = {datetime.now().strftime("%Y-%m-%d")}
- "tomorrow" = {(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
- For other days, calculate from today. Today is {datetime.now().strftime("%A")}.
"""

# --- Tool Definitions ---
tools = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="get_classes_on_date",
            description="Get all classes scheduled on a given date with their availability (spots taken, spots left, full or not).",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "date_str": types.Schema(
                        type="STRING",
                        description="Date in YYYY-MM-DD format.",
                    ),
                },
                required=["date_str"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_class_details",
            description="Get full details of a specific class including the list of who is booked.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "event_id": types.Schema(
                        type="STRING",
                        description="The Google Calendar event ID.",
                    ),
                },
                required=["event_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="book_class",
            description="Book a person into a class. Requires the event ID, the caller's name, and their phone number.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "event_id": types.Schema(type="STRING", description="The Google Calendar event ID."),
                    "name": types.Schema(type="STRING", description="Caller's full name."),
                    "phone": types.Schema(type="STRING", description="Caller's phone number."),
                },
                required=["event_id", "name", "phone"],
            ),
        ),
        types.FunctionDeclaration(
            name="cancel_booking",
            description="Cancel a booking by phone number.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "event_id": types.Schema(type="STRING", description="The Google Calendar event ID."),
                    "phone": types.Schema(type="STRING", description="Phone number of the person to remove."),
                },
                required=["event_id", "phone"],
            ),
        ),
        types.FunctionDeclaration(
            name="find_alternative_classes",
            description="Find available classes of a given type on a date. Use when the requested class is full.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "class_type": types.Schema(type="STRING", description="Class type, e.g. 'Reformer', 'Mat Pilates', 'Tower'."),
                    "date_str": types.Schema(type="STRING", description="Date in YYYY-MM-DD format."),
                },
                required=["class_type", "date_str"],
            ),
        ),
        types.FunctionDeclaration(
            name="find_contact",
            description="Look up a contact in the system by phone number.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "phone": types.Schema(type="STRING", description="Phone number to search for."),
                },
                required=["phone"],
            ),
        ),
        types.FunctionDeclaration(
            name="create_contact",
            description="Create a new contact record for a caller.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "name": types.Schema(type="STRING", description="Caller's name."),
                    "phone": types.Schema(type="STRING", description="Caller's phone number."),
                },
                required=["name", "phone"],
            ),
        ),
        types.FunctionDeclaration(
            name="log_call",
            description="Log a summary of the call for a contact. Call this at the end of every conversation.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "phone": types.Schema(type="STRING", description="Caller's phone number."),
                    "summary": types.Schema(type="STRING", description="Brief summary of what the call was about."),
                },
                required=["phone", "summary"],
            ),
        ),
    ])
]

# --- Tool Execution ---
TOOL_FUNCTIONS = {
    "get_classes_on_date": calendar_service.get_classes_on_date,
    "get_class_details": calendar_service.get_class_details,
    "book_class": calendar_service.book_class,
    "cancel_booking": calendar_service.cancel_booking,
    "find_alternative_classes": calendar_service.find_alternative_classes,
    "find_contact": sheets_service.find_contact,
    "create_contact": sheets_service.create_contact,
    "log_call": sheets_service.log_call,
}


def execute_tool(function_call):
    """Execute a tool call and return the result."""
    name = function_call.name
    args = dict(function_call.args) if function_call.args else {}

    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}

    try:
        result = fn(**args)
        return result
    except Exception as e:
        return {"error": str(e)}


class ReceptionistAgent:
    """Conversational agent that manages a multi-turn chat with tool calling."""

    def __init__(self):
        self.history = []

    def chat(self, user_message: str) -> str:
        """Send a message and get a response, handling any tool calls.

        Args:
            user_message: The caller's message.

        Returns:
            The agent's text response.
        """
        self.history.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        ))

        # Loop: LLM may make multiple tool calls before responding with text
        while True:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=self.history,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            tools=tools,
                            temperature=0.3,
                        ),
                    )
                    break
                except Exception as e:
                    err = str(e)
                    if attempt < 2 and ("503" in err or "429" in err):
                        wait = 2 ** attempt  # 1s, 2s
                        print(f"  [retry] {err[:80]}... waiting {wait}s")
                        time.sleep(wait)
                        continue
                    raise

            # Check if the response has function calls
            has_function_call = False
            function_parts = []
            text_parts = []

            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.function_call:
                        has_function_call = True
                        function_parts.append(part)
                    if part.text:
                        text_parts.append(part.text)

            if not has_function_call:
                # No tool calls — just a text response
                assistant_text = response.candidates[0].content.parts[0].text
                self.history.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=assistant_text)],
                ))
                return assistant_text

            # Execute each function call and collect results
            self.history.append(response.candidates[0].content)

            result_parts = []
            for part in function_parts:
                fc = part.function_call
                print(f"  [tool] {fc.name}({dict(fc.args) if fc.args else {}})")
                result = execute_tool(fc)
                result_parts.append(types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                ))

            self.history.append(types.Content(
                role="user",
                parts=result_parts,
            ))
            # Loop continues — LLM will process the tool results


# --- CLI for quick testing ---
if __name__ == "__main__":
    agent = ReceptionistAgent()
    print(f"🏋️ {STUDIO_NAME} Receptionist")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        reply = agent.chat(user_input)
        print(f"Agent: {reply}\n")
