from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import Appointment, AppointmentStatus, Client, Service
from app.services.availability import find_free_mechanic, is_within_working_hours


class BookingError(Exception):
    """Business-rule violation with a message safe to show to the client."""


async def get_or_create_client(session: AsyncSession, telegram_id: int, name: str = "") -> Client:
    client = (
        await session.execute(select(Client).where(Client.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if client is None:
        client = Client(telegram_id=telegram_id, name=name)
        session.add(client)
        await session.flush()
    return client


async def list_services(session: AsyncSession) -> list[Service]:
    return list((await session.execute(select(Service).order_by(Service.id))).scalars())


async def get_service(session: AsyncSession, service_id: int) -> Service:
    service = await session.get(Service, service_id)
    if service is None:
        raise BookingError(f"Service with id {service_id} does not exist.")
    return service


async def list_client_bookings(session: AsyncSession, telegram_id: int) -> list[Appointment]:
    result = await session.execute(
        select(Appointment)
        .join(Client)
        .where(Client.telegram_id == telegram_id, Appointment.status == AppointmentStatus.SCHEDULED)
        .options(selectinload(Appointment.service), selectinload(Appointment.mechanic))
        .order_by(Appointment.starts_at)
    )
    return list(result.scalars())


async def _get_client_booking(
    session: AsyncSession, telegram_id: int, appointment_id: int
) -> Appointment:
    appointment = (
        await session.execute(
            select(Appointment)
            .join(Client)
            .where(Appointment.id == appointment_id, Client.telegram_id == telegram_id)
            .options(selectinload(Appointment.service), selectinload(Appointment.mechanic))
        )
    ).scalar_one_or_none()
    if appointment is None:
        raise BookingError(f"You have no appointment with id {appointment_id}.")
    return appointment


def _validate_slot(starts_at: datetime, ends_at: datetime, settings: Settings, now: datetime):
    if starts_at <= now:
        raise BookingError("The requested time is in the past.")
    if starts_at.minute % settings.slot_step_minutes or starts_at.second or starts_at.microsecond:
        raise BookingError(
            f"Appointments start on a {settings.slot_step_minutes}-minute grid, "
            "e.g. 10:00 or 10:30."
        )
    if not is_within_working_hours(starts_at, ends_at, settings):
        raise BookingError(
            "The requested time is outside working hours (Mon-Sat "
            f"{settings.work_day_start:%H:%M}-{settings.work_day_end:%H:%M})."
        )


async def create_booking(
    session: AsyncSession,
    telegram_id: int,
    service_id: int,
    starts_at: datetime,
    settings: Settings,
    now: datetime,
    client_name: str = "",
) -> Appointment:
    service = await get_service(session, service_id)
    ends_at = starts_at + timedelta(minutes=service.duration_min)
    _validate_slot(starts_at, ends_at, settings, now)

    mechanic = await find_free_mechanic(session, starts_at, ends_at)
    if mechanic is None:
        raise BookingError("No mechanic is available at that time. Try another slot.")

    client = await get_or_create_client(session, telegram_id, client_name)
    appointment = Appointment(
        client_id=client.id,
        service_id=service.id,
        mechanic_id=mechanic.id,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    session.add(appointment)
    await session.commit()
    await session.refresh(appointment, ["service", "mechanic"])
    return appointment


async def cancel_booking(
    session: AsyncSession, telegram_id: int, appointment_id: int
) -> Appointment:
    appointment = await _get_client_booking(session, telegram_id, appointment_id)
    if appointment.status != AppointmentStatus.SCHEDULED:
        raise BookingError(f"Appointment {appointment_id} is already {appointment.status.value}.")
    appointment.status = AppointmentStatus.CANCELLED
    await session.commit()
    return appointment


async def reschedule_booking(
    session: AsyncSession,
    telegram_id: int,
    appointment_id: int,
    new_starts_at: datetime,
    settings: Settings,
    now: datetime,
) -> Appointment:
    appointment = await _get_client_booking(session, telegram_id, appointment_id)
    if appointment.status != AppointmentStatus.SCHEDULED:
        raise BookingError(f"Appointment {appointment_id} is {appointment.status.value}.")

    new_ends_at = new_starts_at + timedelta(minutes=appointment.service.duration_min)
    _validate_slot(new_starts_at, new_ends_at, settings, now)

    # Free the old slot while searching so the same mechanic can be reused.
    appointment.status = AppointmentStatus.CANCELLED
    await session.flush()
    mechanic = await find_free_mechanic(session, new_starts_at, new_ends_at)
    if mechanic is None:
        appointment.status = AppointmentStatus.SCHEDULED
        await session.commit()
        raise BookingError("No mechanic is available at the new time. Try another slot.")

    appointment.status = AppointmentStatus.SCHEDULED
    appointment.mechanic_id = mechanic.id
    appointment.starts_at = new_starts_at
    appointment.ends_at = new_ends_at
    await session.commit()
    await session.refresh(appointment, ["service", "mechanic"])
    return appointment
