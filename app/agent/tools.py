from datetime import date, datetime

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.config import get_settings
from app.db.models import Appointment
from app.db.session import get_session
from app.services import booking
from app.services.availability import find_available_slots


def _telegram_id(config: RunnableConfig) -> int:
    return config["configurable"]["telegram_id"]


def _format_appointment(appt: Appointment) -> str:
    return (
        f"#{appt.id}: {appt.service.name} on {appt.starts_at:%A %Y-%m-%d at %H:%M} "
        f"with {appt.mechanic.name} ({appt.status.value})"
    )


@tool
async def list_services() -> str:
    """List all services the car service offers, with duration and price."""
    async with get_session() as session:
        services = await booking.list_services(session)
    if not services:
        return "No services are configured yet."
    return "\n".join(
        f"[id {s.id}] {s.name} - {s.duration_min} min, ${s.price}. {s.description}"
        for s in services
    )


@tool
async def check_availability(service_id: int, day: date) -> str:
    """Get free time slots for a service on a given day (YYYY-MM-DD)."""
    settings = get_settings()
    async with get_session() as session:
        try:
            service = await booking.get_service(session, service_id)
        except booking.BookingError as exc:
            return str(exc)
        slots = await find_available_slots(
            session, service.duration_min, day, settings, datetime.now()
        )
    if not slots:
        return f"No free slots for {service.name} on {day}."
    times = ", ".join(f"{s:%H:%M}" for s in slots)
    return f"Free slots for {service.name} on {day}: {times}"


@tool
async def create_booking(service_id: int, starts_at: datetime, config: RunnableConfig) -> str:
    """Book a service at the given start time (ISO format, e.g. 2026-07-06T10:00)."""
    settings = get_settings()
    async with get_session() as session:
        try:
            appt = await booking.create_booking(
                session,
                telegram_id=_telegram_id(config),
                service_id=service_id,
                starts_at=starts_at,
                settings=settings,
                now=datetime.now(),
                client_name=config["configurable"].get("client_name", ""),
            )
        except booking.BookingError as exc:
            return str(exc)
        return f"Booked. {_format_appointment(appt)}"


@tool
async def my_bookings(config: RunnableConfig) -> str:
    """List the client's upcoming appointments."""
    async with get_session() as session:
        appointments = await booking.list_client_bookings(session, _telegram_id(config))
        if not appointments:
            return "You have no upcoming appointments."
        return "\n".join(_format_appointment(a) for a in appointments)


@tool
async def cancel_booking(appointment_id: int, config: RunnableConfig) -> str:
    """Cancel one of the client's appointments by its id."""
    async with get_session() as session:
        try:
            appt = await booking.cancel_booking(session, _telegram_id(config), appointment_id)
        except booking.BookingError as exc:
            return str(exc)
        return f"Cancelled appointment #{appt.id}."


@tool
async def reschedule_booking(
    appointment_id: int, new_starts_at: datetime, config: RunnableConfig
) -> str:
    """Move one of the client's appointments to a new start time (ISO format)."""
    settings = get_settings()
    async with get_session() as session:
        try:
            appt = await booking.reschedule_booking(
                session,
                telegram_id=_telegram_id(config),
                appointment_id=appointment_id,
                new_starts_at=new_starts_at,
                settings=settings,
                now=datetime.now(),
            )
        except booking.BookingError as exc:
            return str(exc)
        return f"Rescheduled. {_format_appointment(appt)}"


BOOKING_TOOLS = [
    list_services,
    check_availability,
    create_booking,
    my_bookings,
    cancel_booking,
    reschedule_booking,
]
