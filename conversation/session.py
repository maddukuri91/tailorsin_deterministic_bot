import json
import time
from dataclasses import dataclass, field
from typing import Any

import redis.asyncio as redis

from config import settings


@dataclass
class SessionState:
    chat_id: int
    mobile: str | None = None
    client_type: str | None = None
    customer_salutation: str | None = None
    awaiting_contact: bool = False
    has_seen_known_customer_menu: bool = False
    awaiting_registration_name: bool = False
    awaiting_registration_email: bool = False
    pending_registration_name: str | None = None
    awaiting_pickup_date: bool = False
    awaiting_pickup_time: bool = False
    awaiting_alteration_pickup_notes: bool = False
    pending_pickup_date: str | None = None
    pending_pickup_time: int | None = None
    pickup_mode: str | None = None
    awaiting_visit_date: bool = False
    awaiting_visit_time: bool = False
    pending_visit_date: str | None = None
    pending_visit_slots: list[str] = field(default_factory=list)
    awaiting_fabric_delivery_notes: bool = False
    awaiting_address_action: bool = False
    awaiting_address_add_line: bool = False
    awaiting_address_add_city: bool = False
    awaiting_address_add_pincode: bool = False
    awaiting_address_delete_id: bool = False
    awaiting_pickup_address: bool = False
    pending_pickup_address_id: int | None = None
    pending_address_ordered_ids: list[int] = field(default_factory=list)
    awaiting_alteration_order: bool = False
    pending_alteration_order_ids: list[int] = field(default_factory=list)
    pending_alteration_order_id: int | None = None
    pending_address_list_ids: list[int] = field(default_factory=list)
    awaiting_order_change_details: bool = False
    awaiting_order_change_select: bool = False
    pending_change_order_id: int | None = None
    pending_change_order_ids: list[int] = field(default_factory=list)
    awaiting_order_cancel_select: bool = False
    awaiting_order_cancel_reason: bool = False
    pending_cancel_order_id: int | None = None
    pending_cancel_order_ids: list[int] = field(default_factory=list)
    pending_address_line: str | None = None
    pending_address_city: str | None = None
    pending_address_pincode: str | None = None
    address_needed_for_pickup: bool = False
    awaiting_address_location: bool = False
    pending_address_lat: float | None = None
    pending_address_lng: float | None = None
    last_activity_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            k: getattr(self, k)
            for k in self.__dataclass_fields__  # type: ignore[attr-defined]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**valid)


_SESSIONS: dict[int, SessionState] = {}
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if settings.redis_url:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _redis_key(chat_id: int) -> str:
    return f"session:{chat_id}"


async def get_session(chat_id: int) -> SessionState:
    client = _get_redis()
    if client is not None:
        try:
            raw = await client.get(_redis_key(chat_id))
            if raw:
                return SessionState.from_dict(json.loads(raw))
        except Exception:
            pass

    session = _SESSIONS.get(chat_id)
    if session is None:
        session = SessionState(chat_id=chat_id)
        _SESSIONS[chat_id] = session
    return session


async def save_session(session: SessionState) -> None:
    client = _get_redis()
    if client is not None:
        try:
            await client.set(_redis_key(session.chat_id), json.dumps(session.to_dict()))
            return
        except Exception:
            pass
    _SESSIONS[session.chat_id] = session


async def reset_session(chat_id: int) -> SessionState:
    session = SessionState(chat_id=chat_id)
    await save_session(session)
    return session