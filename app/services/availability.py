from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Appointment, AppointmentStatus, Mechanic


def is_within_working_hours(starts_at: datetime, ends_at: datetime, settings: Settings) -> bool:
    if starts_at.weekday() in settings.closed_weekdays:
        return False
    if starts_at.date() != ends_at.date():
        return False
    return starts_at.time() >= settings.work_day_start and ends_at.time() <= settings.work_day_end


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


async def _scheduled_appointments(
    session: AsyncSession, day_start: datetime, day_end: datetime
) -> list[Appointment]:
    result = await session.execute(
        select(Appointment).where(
            Appointment.status == AppointmentStatus.SCHEDULED,
            Appointment.starts_at < day_end,
            Appointment.ends_at > day_start,
        )
    )
    return list(result.scalars())


async def find_free_mechanic(
    session: AsyncSession, starts_at: datetime, ends_at: datetime
) -> Mechanic | None:
    """Return a mechanic with no scheduled appointment overlapping the interval."""
    mechanics = list((await session.execute(select(Mechanic))).scalars())
    appointments = await _scheduled_appointments(session, starts_at, ends_at)
    busy_by_mechanic: dict[int, list[Appointment]] = {}
    for appt in appointments:
        busy_by_mechanic.setdefault(appt.mechanic_id, []).append(appt)
    for mechanic in mechanics:
        busy = busy_by_mechanic.get(mechanic.id, [])
        if not any(_overlaps(starts_at, ends_at, a.starts_at, a.ends_at) for a in busy):
            return mechanic
    return None


async def find_available_slots(
    session: AsyncSession,
    duration_min: int,
    day: date,
    settings: Settings,
    now: datetime,
) -> list[datetime]:
    """All slot start times on `day` where at least one mechanic is free."""
    if day.weekday() in settings.closed_weekdays:
        return []

    day_start = datetime.combine(day, settings.work_day_start)
    day_end = datetime.combine(day, settings.work_day_end)
    duration = timedelta(minutes=duration_min)
    step = timedelta(minutes=settings.slot_step_minutes)

    mechanics = list((await session.execute(select(Mechanic))).scalars())
    if not mechanics:
        return []
    appointments = await _scheduled_appointments(session, day_start, day_end)
    busy_by_mechanic: dict[int, list[Appointment]] = {}
    for appt in appointments:
        busy_by_mechanic.setdefault(appt.mechanic_id, []).append(appt)

    slots: list[datetime] = []
    cursor = day_start
    while cursor + duration <= day_end:
        if cursor > now:
            for mechanic in mechanics:
                busy = busy_by_mechanic.get(mechanic.id, [])
                if not any(
                    _overlaps(cursor, cursor + duration, a.starts_at, a.ends_at) for a in busy
                ):
                    slots.append(cursor)
                    break
        cursor += step
    return slots
