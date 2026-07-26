from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException

from config import settings
from services.conversation_service import IncomingMessage, OutgoingMessage, handle_incoming_message


router = APIRouter(prefix="/wati", tags=["wati"])


def _normalize_whatsapp_user_id(value: str | None) -> int | None:
    if value is None:
        return None

    digits_only = "".join(character for character in str(value) if character.isdigit())
    if not digits_only:
        return None

    return int(digits_only)


def _extract_text(payload: dict[str, Any]) -> str:
    text = payload.get("text")
    if isinstance(text, str):
        return text.strip()

    nested_text = payload.get("text", {})
    if isinstance(nested_text, dict):
        body = nested_text.get("body")
        if isinstance(body, str):
            return body.strip()

    message = payload.get("message")
    if isinstance(message, str):
        return message.strip()

    data = payload.get("data", {})
    if isinstance(data, dict):
        candidate = data.get("text") or data.get("body") or data.get("message")
        if isinstance(candidate, str):
            return candidate.strip()

    return ""


def _extract_contact_phone(payload: dict[str, Any]) -> str | None:
    contact = payload.get("contact")
    if isinstance(contact, dict):
        phone_number = contact.get("phone_number") or contact.get("phone")
        if isinstance(phone_number, str) and phone_number.strip():
            return phone_number.strip()

    data = payload.get("data", {})
    if isinstance(data, dict):
        phone_number = data.get("phone") or data.get("phone_number")
        if isinstance(phone_number, str) and phone_number.strip():
            return phone_number.strip()

    return None


def validate_wati_webhook_secret(header_secret: str | None) -> None:
    if not settings.wati_webhook_secret:
        return

    if header_secret != settings.wati_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")


def parse_wati_update(update: dict[str, Any]) -> IncomingMessage | None:
    source_data = update.get("data") if isinstance(update.get("data"), dict) else update

    user_identifier = (
        source_data.get("waId")
        or source_data.get("whatsappNumber")
        or source_data.get("senderPhone")
        or source_data.get("from")
        or update.get("waId")
        or update.get("whatsappNumber")
        or update.get("senderPhone")
        or update.get("from")
    )

    user_id = _normalize_whatsapp_user_id(user_identifier)
    if user_id is None:
        return None

    text = _extract_text(source_data if isinstance(source_data, dict) else update)
    contact_phone = _extract_contact_phone(source_data if isinstance(source_data, dict) else update)

    return IncomingMessage(
        user_id=user_id,
        text=text,
        contact_phone=contact_phone,
        contact_user_id=user_id if contact_phone else None,
        source_user_id=user_id,
        is_start_command=text.casefold() in {"/start", "hi", "hello", "menu"},
        metadata={"platform": "wati", "raw_update": update},
    )


async def call_wati_api(payload: dict[str, Any]) -> None:
    if not settings.wati_base_url or not settings.wati_api_key:
        raise HTTPException(status_code=503, detail="WATI is not configured")

    send_message_url = f"{settings.wati_base_url.rstrip('/')}/api/v1/sendSessionMessage"
    headers = {
        "Authorization": f"Bearer {settings.wati_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(send_message_url, json=payload, headers=headers)
        response.raise_for_status()


def _extract_buttons_text(reply_markup: dict[str, Any]) -> str:
    """Extract button labels from either inline_keyboard or keyboard format as text."""
    lines: list[str] = []

    # Try inline_keyboard first (Telegram style)
    inline_rows = reply_markup.get("inline_keyboard")
    if inline_rows:
        for row in inline_rows:
            labels = [button.get("text", "") for button in row if button.get("text")]
            if labels:
                lines.append(" | ".join(labels))
        return "\n".join(lines)

    # Fall back to keyboard (ReplyKeyboardMarkup)
    keyboard_rows = reply_markup.get("keyboard")
    if keyboard_rows:
        for row in keyboard_rows:
            labels = [button.get("text", "") for button in row if button.get("text")]
            if labels:
                lines.append(" | ".join(labels))
        return "\n".join(lines)

    return ""


def build_wati_payload(user_id: int, message: OutgoingMessage) -> dict[str, Any]:
    text = message.text
    if message.reply_markup:
        buttons_text = _extract_buttons_text(message.reply_markup)
        if buttons_text:
            text = f"{text}\n\n{buttons_text}"

    payload = {
        "whatsappNumber": str(user_id),
        "messageText": text,
    }

    # Add location button if request_location is in reply_markup
    if message.reply_markup and message.reply_markup.get("keyboard"):
        for row in message.reply_markup.get("keyboard", []):
            for button in row:
                if button.get("request_location"):
                    # WATI supports location request buttons
                    payload["buttons"] = [
                        {
                            "text": button.get("text", "📍 Share Location"),
                            "type": "location"
                        }
                    ]
                    break

    return payload


async def send_wati_message(user_id: int, message: OutgoingMessage) -> None:
    payload = build_wati_payload(user_id, message)
    await call_wati_api(payload)


async def process_wati_update(update: dict[str, Any]) -> dict[str, bool]:
    incoming_message = parse_wati_update(update)
    if incoming_message is None:
        return {"ok": True}

    outgoing_messages = await handle_incoming_message(incoming_message)
    for outgoing_message in outgoing_messages:
        await send_wati_message(incoming_message.user_id, outgoing_message)

    return {"ok": True}


@router.post("/webhook")
async def wati_webhook(
    update: dict[str, Any],
    x_wati_webhook_secret: str | None = Header(default=None),
) -> dict[str, bool]:
    validate_wati_webhook_secret(x_wati_webhook_secret)
    return await process_wati_update(update)