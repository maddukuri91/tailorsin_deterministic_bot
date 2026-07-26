import logging
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from xml.sax.saxutils import escape as xml_escape

from config import settings
from services.conversation_service import IncomingMessage, OutgoingMessage, handle_incoming_message


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/twilio", tags=["twilio"])


def validate_twilio_signature() -> None:
    """Validate Twilio webhook signature if configured."""
    if not settings.twilio_auth_token:
        return
    
    # Note: Full signature validation requires storing the signature
    # For now, we'll do basic validation via header
    # In production, implement proper Twilio signature validation


def parse_twilio_update(form_data: dict[str, Any]) -> IncomingMessage | None:
    """Parse Twilio webhook form data into IncomingMessage."""
    from_number = form_data.get("From", "")
    
    # Extract phone number (Twilio format: whatsapp:+919876543210 or +919876543210)
    if from_number.startswith("whatsapp:"):
        user_id = int("".join(c for c in from_number.replace("whatsapp:", "") if c.isdigit()))
    else:
        user_id = int("".join(c for c in from_number if c.isdigit()))
    
    if not user_id:
        return None
    
    # Extract message text
    text = (form_data.get("Body") or "").strip()
    
    # Check for media (images, etc.)
    num_media = int(form_data.get("NumMedia", 0))
    
    return IncomingMessage(
        user_id=user_id,
        text=text,
        contact_phone=from_number.replace("whatsapp:", "") if "whatsapp" in from_number else from_number,
        contact_user_id=user_id,
        source_user_id=user_id,
        is_start_command=text.lower() in {"/start", "hi", "hello", "menu"},
        metadata={
            "platform": "twilio",
            "num_media": num_media,
            "message_sid": form_data.get("MessageSid"),
        },
    )




def build_twilio_response(messages: list[OutgoingMessage]) -> str:
    """Build TwiML response from outgoing messages."""
    # Twilio expects TwiML (XML) response
    # For multiple messages, we'll send the first one
    # Subsequent messages would need to be sent via REST API
    
    if not messages:
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    
    first_message = messages[0]
    text = xml_escape(first_message.text)
    
    # Convert reply_markup buttons to text menu for Twilio (SMS doesn't support buttons)
    if first_message.reply_markup:
        menu_text = _build_text_menu(first_message.reply_markup)
        if menu_text:
            text += "\n\n" + xml_escape(menu_text)
    
    # If there are more messages, append them (limited by Twilio)
    if len(messages) > 1:
        text += "\n\n---\n"
        for msg in messages[1:]:
            text += f"{xml_escape(msg.text)}\n"
    
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{text}</Message></Response>'
    return twiml


def _build_text_menu(reply_markup: dict[str, Any]) -> str:
    """Convert button markup to text menu for SMS platforms."""
    lines: list[str] = []
    lines.append("📋 Menu Options:")
    lines.append("")
    
    # Try inline_keyboard first (Telegram style)
    inline_rows = reply_markup.get("inline_keyboard")
    if inline_rows:
        counter = 1
        for row in inline_rows:
            for button in row:
                button_text = button.get("text", "")
                # Remove emoji prefix for cleaner SMS
                button_text = button_text.strip()
                if button_text:
                    lines.append(f"{counter}. {button_text}")
                    counter += 1
        return "\n".join(lines)
    
    # Fall back to keyboard (ReplyKeyboardMarkup)
    keyboard_rows = reply_markup.get("keyboard")
    if keyboard_rows:
        counter = 1
        for row in keyboard_rows:
            for button in row:
                button_text = button.get("text", "")
                button_text = button_text.strip()
                if button_text:
                    lines.append(f"{counter}. {button_text}")
                    counter += 1
        return "\n".join(lines)
    
    return ""


async def send_twilio_message(user_id: int, message: OutgoingMessage) -> None:
    """Send a message via Twilio REST API (for follow-up messages)."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio not configured, skipping message send")
        return
    
    # Determine if it's WhatsApp or SMS based on user_id format
    # This is a simplified approach - you may need to adjust based on your Twilio setup
    to_number = str(user_id)
    
    # Check if this is a WhatsApp number (you may need to adjust this logic)
    # For now, assume all Twilio messages are SMS unless configured otherwise
    from_number = settings.twilio_phone_number
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    
    payload = {
        "To": f"+{to_number}",
        "From": from_number,
        "Body": message.text,
    }
    
    # If WhatsApp is enabled, use WhatsApp format
    if settings.twilio_whatsapp_enabled:
        payload["To"] = f"whatsapp:+{to_number}"
        payload["From"] = f"whatsapp:{from_number}"
    
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            data=payload,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
        response.raise_for_status()


async def process_twilio_update(form_data: dict[str, Any]) -> str:
    """Process incoming Twilio webhook and return TwiML response."""
    incoming_message = parse_twilio_update(form_data)
    
    if incoming_message is None:
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    
    try:
        outgoing_messages = await handle_incoming_message(incoming_message)
        
        # Send first message via TwiML (immediate response)
        # Send subsequent messages via REST API (async)
        if outgoing_messages:
            twiml_response = build_twilio_response([outgoing_messages[0]])
            
            # Send remaining messages asynchronously
            if len(outgoing_messages) > 1:
                for msg in outgoing_messages[1:]:
                    try:
                        await send_twilio_message(incoming_message.user_id, msg)
                    except Exception:
                        logger.exception("Failed to send follow-up Twilio message")
            
            return twiml_response
    except Exception:
        logger.exception("Error processing Twilio update")
    
    return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


@router.post("/webhook")
async def twilio_webhook(request: Request) -> str:
    """Twilio webhook endpoint - accepts form data."""
    form_data = await request.form()
    form_dict = dict(form_data)
    
    # Validate Twilio signature (optional, recommended for production)
    # signature = request.headers.get("X-Twilio-Signature")
    # validate_twilio_signature(signature, form_dict)
    
    return await process_twilio_update(form_dict)


# Support legacy /webhook path (without /twilio prefix)
@router.post("/webhook/legacy")
async def twilio_webhook_legacy(request: Request) -> str:
    """Legacy webhook endpoint for backward compatibility."""
    form_data = await request.form()
    form_dict = dict(form_data)
    return await process_twilio_update(form_dict)
