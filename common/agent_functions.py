import json
import re
import time
from datetime import datetime, timedelta
import asyncio
from .business_logic import (
    get_customer,
    get_customer_appointments,
    get_customer_orders,
    schedule_appointment,
    get_available_appointment_slots,
    prepare_agent_filler_message,
    prepare_farewell_message,
)


async def find_customer(params):
    """Look up a customer by phone, email, or ID."""
    phone = params.get("phone")
    email = params.get("email")
    customer_id = params.get("customer_id")

    result = await get_customer(phone=phone, email=email, customer_id=customer_id)
    return result


async def get_appointments(params):
    """Get appointments for a customer."""
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}

    result = await get_customer_appointments(customer_id)
    return result


async def get_orders(params):
    """Get orders for a customer."""
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}

    result = await get_customer_orders(customer_id)
    return result


async def create_appointment(params):
    """Schedule a new appointment."""
    customer_id = params.get("customer_id")
    date = params.get("date")
    service = params.get("service")

    if not all([customer_id, date, service]):
        return {"error": "customer_id, date, and service are required"}

    result = await schedule_appointment(customer_id, date, service)
    return result


async def check_availability(params):
    """Check available appointment slots."""
    start_date = params.get("start_date")
    end_date = params.get(
        "end_date", (datetime.fromisoformat(start_date) + timedelta(days=7)).isoformat()
    )

    if not start_date:
        return {"error": "start_date is required"}

    result = await get_available_appointment_slots(start_date, end_date)
    return result


async def agent_filler(websocket, params):
    """
    Handle agent filler messages while maintaining proper function call protocol.
    """
    result = await prepare_agent_filler_message(websocket, **params)
    return result


async def end_call(websocket, params):
    """
    End the conversation and close the connection.
    """
    farewell_type = params.get("farewell_type", "general")
    result = await prepare_farewell_message(websocket, farewell_type)
    return result


# Function definitions that will be sent to the Voice Agent API
FUNCTION_DEFINITIONS = [
    {
        "name": "agent_filler",
        "description": """Use this function to provide natural conversational filler before looking up information.
        ALWAYS call this function first with message_type='lookup' when you're about to look up customer information.
        After calling this function, you MUST immediately follow up with the appropriate lookup function (e.g., find_customer).""",
        "parameters": {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Type of filler message to use. Use 'lookup' when about to search for information.",
                    "enum": ["lookup", "general"],
                }
            },
            "required": ["message_type"],
        },
    },
    {
        "name": "find_customer",
        "description": """Look up a customer's account information. Use context clues to determine what type of identifier the user is providing:

        Customer ID formats:
        - Numbers only (e.g., '169', '42') → Format as 'CUST0169', 'CUST0042'
        - With prefix (e.g., 'CUST169', 'customer 42') → Format as 'CUST0169', 'CUST0042'
        
        Phone number recognition:
        - Standard format: '555-123-4567' → Format as '+15551234567'
        - With area code: '(555) 123-4567' → Format as '+15551234567'
        - Spoken naturally: 'five five five, one two three, four five six seven' → Format as '+15551234567'
        - International: '+1 555-123-4567' → Use as is
        - Always add +1 country code if not provided
        
        Email address recognition:
        - Spoken naturally: 'my email is john dot smith at example dot com' → Format as 'john.smith@example.com'
        - With domain: 'john@example.com' → Use as is
        - Spelled out: 'j o h n at example dot com' → Format as 'john@example.com'""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID. Format as CUSTXXXX where XXXX is the number padded to 4 digits with leading zeros. Example: if user says '42', pass 'CUST0042'",
                },
                "phone": {
                    "type": "string",
                    "description": """Phone number with country code. Format as +1XXXXXXXXXX:
                    - Add +1 if not provided
                    - Remove any spaces, dashes, or parentheses
                    - Convert spoken numbers to digits
                    Example: 'five five five one two three four five six seven' → '+15551234567'""",
                },
                "email": {
                    "type": "string",
                    "description": """Email address in standard format:
                    - Convert 'dot' to '.'
                    - Convert 'at' to '@'
                    - Remove spaces between spelled out letters
                    Example: 'j dot smith at example dot com' → 'j.smith@example.com'""",
                },
            },
        },
    },
    {
        "name": "get_appointments",
        "description": """Retrieve all appointments for a customer. Use this function when:
        - A customer asks about their upcoming appointments
        - A customer wants to know their appointment schedule
        - A customer asks 'When is my next appointment?'
        
        Always verify you have the customer's account first using find_customer before checking appointments.""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_orders",
        "description": """Retrieve order history for a customer. Use this function when:
        - A customer asks about their orders
        - A customer wants to check order status
        - A customer asks questions like 'Where is my order?' or 'What did I order?'
        
        Always verify you have the customer's account first using find_customer before checking orders.""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "create_appointment",
        "description": """Schedule a new appointment for a customer. Use this function when:
        - A customer wants to book a new appointment
        - A customer asks to schedule a service
        
        Before scheduling:
        1. Verify customer account exists using find_customer
        2. Check availability using check_availability
        3. Confirm date/time and service type with customer before booking""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                },
                "date": {
                    "type": "string",
                    "description": "Appointment date and time in ISO format (YYYY-MM-DDTHH:MM:SS). Must be a time slot confirmed as available.",
                },
                "service": {
                    "type": "string",
                    "description": "Type of service requested. Must be one of the following: Consultation, Follow-up, Review, or Planning",
                    "enum": ["Consultation", "Follow-up", "Review", "Planning"],
                },
            },
            "required": ["customer_id", "date", "service"],
        },
    },
    {
        "name": "check_availability",
        "description": """Check available appointment slots within a date range. Use this function when:
        - A customer wants to know available appointment times
        - Before scheduling a new appointment
        - A customer asks 'When can I come in?' or 'What times are available?'
        
        After checking availability, present options to the customer in a natural way, like:
        'I have openings on [date] at [time] or [date] at [time]. Which works better for you?'""",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO format (YYYY-MM-DDTHH:MM:SS). Usually today's date for immediate availability checks.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO format. Optional - defaults to 7 days after start_date. Use for specific date range requests.",
                },
            },
            "required": ["start_date"],
        },
    },
    {
        "name": "end_call",
        "description": """End the conversation and close the connection. Call this function when:
        - User says goodbye, thank you, etc.
        - User indicates they're done ("that's all I need", "I'm all set", etc.)
        - User wants to end the conversation
        
        Examples of triggers:
        - "Thank you, bye!"
        - "That's all I needed, thanks"
        - "Have a good day"
        - "Goodbye"
        - "I'm done"
        
        Do not call this function if the user is just saying thanks but continuing the conversation.""",
        "parameters": {
            "type": "object",
            "properties": {
                "farewell_type": {
                    "type": "string",
                    "description": "Type of farewell to use in response",
                    "enum": ["thanks", "general", "help"],
                }
            },
            "required": ["farewell_type"],
        },
    },
]

# ---------------------------------------------------------------------------
# Hotword detection
# ---------------------------------------------------------------------------

_current_hotword: str | None = None
_conversation_active: bool = False
_last_activity_time: float = 0.0
CONVERSATION_TIMEOUT = 30.0  # seconds of inactivity before returning to hotword-only mode


def set_hotword(hotword: str | None):
    global _current_hotword, _conversation_active, _last_activity_time
    _current_hotword = hotword.lower() if hotword else None
    _conversation_active = False
    _last_activity_time = 0.0


async def close_hotword_session(params):
    global _conversation_active
    _conversation_active = False
    return {"status": "closed"}


async def check_hotword(params):
    global _conversation_active, _last_activity_time
    transcript = params.get("transcript", "")
    hotword = _current_hotword
    now = time.time()

    if not hotword:
        return {"active": True, "query": transcript}

    # If we're in an active conversation and within the inactivity timeout,
    # pass through without requiring the hotword again
    if _conversation_active:
        if now - _last_activity_time < CONVERSATION_TIMEOUT:
            _last_activity_time = now
            return {"active": True, "query": transcript}
        else:
            # Inactivity timeout elapsed — reset to hotword-only mode
            _conversation_active = False

    # Check for hotword (tolerates punctuation between words e.g. "Hey, Saga.")
    words = hotword.split()
    pattern = r'\b' + r'[\s,\.!?\'\"]*'.join(re.escape(w) for w in words) + r'\b'
    match = re.search(pattern, transcript, re.IGNORECASE)

    if match:
        query = transcript[match.end():].strip().lstrip('.,!? ')
        _conversation_active = True
        _last_activity_time = now
        return {
            "active": True,
            "query": query or transcript,
        }
    else:
        return {
            "active": False,
            "instruction": "Hotword not detected. Do not speak. Stay silent.",
        }


CLOSE_HOTWORD_SESSION_DEFINITION = {
    "name": "close_hotword_session",
    "description": (
        "Call this function when the conversation triggered by the hotword is complete. "
        "Triggers when the user's question is fully answered and they indicate satisfaction "
        "(e.g. 'thanks', 'got it', 'okay', 'that's all', 'perfect', 'great'). "
        "After calling this, return to silent listening mode — do not speak further unless the hotword is said again."
    ),
    "parameters": {"type": "object", "properties": {}},
}

CHECK_HOTWORD_DEFINITION = {
    "name": "check_hotword",
    "description": (
        "MANDATORY: Call this function before responding to ANY user input. "
        "Pass ONLY the most recent utterance — not the full conversation history. "
        "If the result has active=false, do not speak at all — stay completely silent. "
        "If the result has active=true, respond naturally to the 'query' field only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "transcript": {
                "type": "string",
                "description": "The most recent thing the user just said (current utterance only, not history).",
            }
        },
        "required": ["transcript"],
    },
}


# Map function names to their implementations
FUNCTION_MAP = {
    "find_customer": find_customer,
    "get_appointments": get_appointments,
    "get_orders": get_orders,
    "create_appointment": create_appointment,
    "check_availability": check_availability,
    "agent_filler": agent_filler,
    "end_call": end_call,
    "check_hotword": check_hotword,
    "close_hotword_session": close_hotword_session,
}
