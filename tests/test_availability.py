from datetime import date, datetime

from app.db.models import Mechanic
from app.services.availability import find_available_slots, find_free_mechanic
from app.services.booking import create_booking

# Monday
DAY = date(2026, 7, 6)
NOW = datetime(2026, 7, 5, 12, 0)


async def test_no_mechanics_means_no_slots(session, service, settings):
    slots = await find_available_slots(session, service.duration_min, DAY, settings, NOW)
    assert slots == []


async def test_full_day_grid_for_free_mechanic(session, service, mechanic, settings):
    slots = await find_available_slots(session, service.duration_min, DAY, settings, NOW)
    assert slots[0] == datetime(2026, 7, 6, 9, 0)
    # last slot where a 60-minute service still fits before 18:00
    assert slots[-1] == datetime(2026, 7, 6, 17, 0)
    assert len(slots) == 17


async def test_closed_day_has_no_slots(session, service, mechanic, settings):
    sunday = date(2026, 7, 5)
    slots = await find_available_slots(session, service.duration_min, sunday, settings, NOW)
    assert slots == []


async def test_past_slots_are_hidden(session, service, mechanic, settings):
    now = datetime(2026, 7, 6, 12, 0)
    slots = await find_available_slots(session, service.duration_min, DAY, settings, now)
    assert slots[0] == datetime(2026, 7, 6, 12, 30)


async def test_booked_interval_removes_overlapping_slots(session, service, mechanic, settings):
    await create_booking(session, 1, service.id, datetime(2026, 7, 6, 10, 0), settings, NOW)
    slots = await find_available_slots(session, service.duration_min, DAY, settings, NOW)
    # 9:30 and 10:30 starts would overlap the 10:00-11:00 booking
    assert datetime(2026, 7, 6, 9, 0) in slots
    assert datetime(2026, 7, 6, 9, 30) not in slots
    assert datetime(2026, 7, 6, 10, 0) not in slots
    assert datetime(2026, 7, 6, 10, 30) not in slots
    assert datetime(2026, 7, 6, 11, 0) in slots


async def test_second_mechanic_keeps_slot_open(session, service, mechanic, settings):
    session.add(Mechanic(name="Alice", specialization="brakes"))
    await session.commit()
    await create_booking(session, 1, service.id, datetime(2026, 7, 6, 10, 0), settings, NOW)
    slots = await find_available_slots(session, service.duration_min, DAY, settings, NOW)
    assert datetime(2026, 7, 6, 10, 0) in slots


async def test_find_free_mechanic_skips_busy_one(session, service, mechanic, settings):
    booked = await create_booking(
        session, 1, service.id, datetime(2026, 7, 6, 10, 0), settings, NOW
    )
    assert booked.mechanic_id == mechanic.id
    free = await find_free_mechanic(
        session, datetime(2026, 7, 6, 10, 0), datetime(2026, 7, 6, 11, 0)
    )
    assert free is None
