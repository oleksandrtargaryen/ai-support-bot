from datetime import datetime

import pytest

from app.db.models import AppointmentStatus
from app.services.booking import (
    BookingError,
    cancel_booking,
    create_booking,
    list_client_bookings,
    reschedule_booking,
)

NOW = datetime(2026, 7, 5, 12, 0)
MONDAY_10 = datetime(2026, 7, 6, 10, 0)


async def test_create_booking(session, service, mechanic, settings):
    appt = await create_booking(session, 1, service.id, MONDAY_10, settings, NOW, "Ivan")
    assert appt.status == AppointmentStatus.SCHEDULED
    assert appt.mechanic_id == mechanic.id
    assert appt.ends_at == datetime(2026, 7, 6, 11, 0)
    assert appt.client.telegram_id == 1


@pytest.mark.parametrize(
    "starts_at, message",
    [
        (datetime(2026, 7, 3, 10, 0), "in the past"),
        (datetime(2026, 7, 6, 10, 15), "grid"),
        (datetime(2026, 7, 6, 8, 0), "working hours"),
        (datetime(2026, 7, 6, 17, 30), "working hours"),  # would end at 18:30
        (datetime(2026, 7, 12, 10, 0), "working hours"),  # Sunday
    ],
)
async def test_create_booking_rejects_invalid_times(
    session, service, mechanic, settings, starts_at, message
):
    with pytest.raises(BookingError, match=message):
        await create_booking(session, 1, service.id, starts_at, settings, NOW)


async def test_create_booking_unknown_service(session, mechanic, settings):
    with pytest.raises(BookingError, match="does not exist"):
        await create_booking(session, 1, 999, MONDAY_10, settings, NOW)


async def test_create_booking_conflict(session, service, mechanic, settings):
    await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    with pytest.raises(BookingError, match="No mechanic is available"):
        await create_booking(session, 2, service.id, MONDAY_10, settings, NOW)


async def test_cancel_booking(session, service, mechanic, settings):
    appt = await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    cancelled = await cancel_booking(session, 1, appt.id)
    assert cancelled.status == AppointmentStatus.CANCELLED
    assert await list_client_bookings(session, 1) == []


async def test_cancel_booking_of_another_client_is_hidden(session, service, mechanic, settings):
    appt = await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    with pytest.raises(BookingError, match="no appointment"):
        await cancel_booking(session, 2, appt.id)


async def test_cancel_twice(session, service, mechanic, settings):
    appt = await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    await cancel_booking(session, 1, appt.id)
    with pytest.raises(BookingError, match="already cancelled"):
        await cancel_booking(session, 1, appt.id)


async def test_reschedule_booking(session, service, mechanic, settings):
    appt = await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    new_time = datetime(2026, 7, 6, 15, 0)
    moved = await reschedule_booking(session, 1, appt.id, new_time, settings, NOW)
    assert moved.starts_at == new_time
    assert moved.ends_at == datetime(2026, 7, 6, 16, 0)
    assert moved.status == AppointmentStatus.SCHEDULED


async def test_reschedule_reuses_own_mechanic(session, service, mechanic, settings):
    """Shifting by 30 minutes overlaps the old slot - must not conflict with itself."""
    appt = await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    moved = await reschedule_booking(
        session, 1, appt.id, datetime(2026, 7, 6, 10, 30), settings, NOW
    )
    assert moved.mechanic_id == mechanic.id


async def test_reschedule_conflict_keeps_original(session, service, mechanic, settings):
    appt = await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    other = await create_booking(session, 2, service.id, datetime(2026, 7, 6, 14, 0), settings, NOW)
    assert other.mechanic_id == mechanic.id
    with pytest.raises(BookingError, match="No mechanic is available"):
        await reschedule_booking(session, 1, appt.id, datetime(2026, 7, 6, 14, 0), settings, NOW)
    await session.refresh(appt)
    assert appt.status == AppointmentStatus.SCHEDULED
    assert appt.starts_at == MONDAY_10


async def test_list_client_bookings(session, service, mechanic, settings):
    await create_booking(session, 1, service.id, MONDAY_10, settings, NOW)
    await create_booking(session, 1, service.id, datetime(2026, 7, 6, 13, 0), settings, NOW)
    bookings = await list_client_bookings(session, 1)
    assert [b.starts_at.hour for b in bookings] == [10, 13]
