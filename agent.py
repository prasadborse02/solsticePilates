"""Solstice Pilates AI Receptionist — LLM Agent with tool calling (Groq)."""

import json
import time
from datetime import datetime, timedelta
from groq import Groq

from config import (
    GROQ_API_KEY, GROQ_MODEL,
    STUDIO_NAME, STUDIO_HOURS, STUDIO_ADDRESS, STUDIO_PHONE,
    CLASS_TYPES, PRICING, TIMEZONE,
)
import calendar_service
import sheets_service

# --- Groq Client ---
client = Groq(api_key=GROQ_API_KEY)

# --- System Prompt ---
TODAY = datetime.now().strftime("%A, %B %d, %Y")
TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%A, %B %d, %Y")

SYSTEM_PROMPT = f"""You are the receptionist for {STUDIO_NAME}. Be warm, concise. Today={datetime.now().strftime("%Y-%m-%d")} ({datetime.now().strftime("%A")}). Tomorrow={(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}.

Studio: {STUDIO_ADDRESS} | {STUDIO_PHONE} | {STUDIO_HOURS}
Pricing: Single $35, 5-pack $150, 10-pack $280, Unlimited $250/mo, Drop-in $40
Classes: Reformer (10AM/6PM/7PM, 8 spots), Morning Mat Pilates (7AM, 12 spots), Tower Pilates (4PM, 6 spots)

CRITICAL RULES:
1. NEVER call book_class, create_contact, or log_call until the caller has told you their real name and phone number. If you don't have them, ASK FIRST. Using "unknown", "N/A", or any placeholder is FORBIDDEN.
2. ALWAYS use get_classes_on_date before answering availability. Never guess.
3. If class full, suggest alternatives same day.
4. Cancel by phone number only.
5. Handoff to human: billing disputes, refunds, birthday parties, medical concerns. Before handing off, ask for name and phone so the team can call back.
6. Keep responses to 1-2 sentences."""

# --- Tool Definitions (OpenAI-compatible format) ---
tools = [
    {"type": "function", "function": {"name": "get_classes_on_date", "description": "Get classes with availability on a date.", "parameters": {"type": "object", "properties": {"date_str": {"type": "string", "description": "YYYY-MM-DD"}}, "required": ["date_str"]}}},
    {"type": "function", "function": {"name": "book_class", "description": "Book a person into a class.", "parameters": {"type": "object", "properties": {"event_id": {"type": "string"}, "name": {"type": "string"}, "phone": {"type": "string"}}, "required": ["event_id", "name", "phone"]}}},
    {"type": "function", "function": {"name": "cancel_booking", "description": "Cancel a booking by phone.", "parameters": {"type": "object", "properties": {"event_id": {"type": "string"}, "phone": {"type": "string"}}, "required": ["event_id", "phone"]}}},
    {"type": "function", "function": {"name": "find_alternative_classes", "description": "Find open classes of a type on a date.", "parameters": {"type": "object", "properties": {"class_type": {"type": "string"}, "date_str": {"type": "string"}}, "required": ["class_type", "date_str"]}}},
    {"type": "function", "function": {"name": "find_contact", "description": "Look up contact by phone.", "parameters": {"type": "object", "properties": {"phone": {"type": "string"}}, "required": ["phone"]}}},
    {"type": "function", "function": {"name": "create_contact", "description": "Create new contact.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "phone": {"type": "string"}}, "required": ["name", "phone"]}}},
    {"type": "function", "function": {"name": "log_call", "description": "Log call summary. Use at end of conversation.", "parameters": {"type": "object", "properties": {"phone": {"type": "string"}, "summary": {"type": "string"}}, "required": ["phone", "summary"]}}},
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


class ReceptionistAgent:
    """Conversational agent that manages a multi-turn chat with tool calling."""

    def __init__(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_message: str) -> str:
        """Send a message and get a response, handling any tool calls."""
        self.messages.append({"role": "user", "content": user_message})

        while True:
            for attempt in range(3):
                try:
                    response = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=self.messages,
                        tools=tools,
                        tool_choice="auto",
                        temperature=0.3,
                    )
                    break
                except Exception as e:
                    err = str(e)
                    if attempt < 2 and ("429" in err or "503" in err):
                        wait = 2 ** attempt
                        print(f"  [retry] {err[:80]}... waiting {wait}s")
                        time.sleep(wait)
                        continue
                    raise

            choice = response.choices[0]

            if not choice.message.tool_calls:
                assistant_text = choice.message.content or ""
                self.messages.append({"role": "assistant", "content": assistant_text})
                return assistant_text

            # Process tool calls
            tool_calls_msg = {"role": "assistant", "content": None, "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in choice.message.tool_calls
            ]}
            self.messages.append(tool_calls_msg)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                print(f"  [tool] {fn_name}({fn_args})")

                fn = TOOL_FUNCTIONS.get(fn_name)
                if fn:
                    try:
                        result = fn(**fn_args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })


# --- CLI for quick testing ---
if __name__ == "__main__":
    agent = ReceptionistAgent()
    print(f"{STUDIO_NAME} Receptionist")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        reply = agent.chat(user_input)
        print(f"Agent: {reply}\n")
