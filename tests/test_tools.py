from datetime import datetime, timedelta

import pytest

import app.agent.tools as tools_module
import app.db.session as db_session
from app.agent.tools import (
    cancel_booking,
    check_availability,
    create_booking,
    list_services,
    my_bookings,
    reschedule_booking,
)

CONFIG = {"configurable": {"telegram_id": 1, "client_name": "Ivan"}}


def next_monday_at(hour: int, minute: int = 0) -> datetime:
    day = datetime.now() + timedelta(days=7)
    while day.weekday() != 0:
        day += timedelta(days=1)
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0)


@pytest.fixture(autouse=True)
def wire_tools(monkeypatch, db_factory, settings):
    monkeypatch.setattr(db_session, "session_factory", db_factory)
    monkeypatch.setattr(tools_module, "get_settings", lambda: settings)


async def test_list_services(service, mechanic):
    result = await list_services.ainvoke({})
    assert "Oil change" in result
    assert f"[id {service.id}]" in result


async def test_list_services_empty():
    assert "No services" in await list_services.ainvoke({})


async def test_check_availability(service, mechanic):
    day = next_monday_at(9).date()
    result = await check_availability.ainvoke({"service_id": service.id, "day": str(day)})
    assert "09:00" in result
    assert "17:00" in result


async def test_tools_hide_config_from_llm():
    schema = create_booking.get_input_schema().model_json_schema()
    assert "config" not in schema["properties"]
    assert set(schema["properties"]) == {"service_id", "starts_at"}


async def test_create_and_list_and_cancel_flow(service, mechanic):
    starts = next_monday_at(10)
    result = await create_booking.ainvoke(
        {"service_id": service.id, "starts_at": starts.isoformat()}, config=CONFIG
    )
    assert "Booked" in result
    assert "Oil change" in result

    listed = await my_bookings.ainvoke({}, config=CONFIG)
    assert "Oil change" in listed

    appointment_id = int(listed.split("#")[1].split(":")[0])
    cancelled = await cancel_booking.ainvoke({"appointment_id": appointment_id}, config=CONFIG)
    assert "Cancelled" in cancelled

    assert "no upcoming" in await my_bookings.ainvoke({}, config=CONFIG)


async def test_reschedule_tool(service, mechanic):
    starts = next_monday_at(10)
    created = await create_booking.ainvoke(
        {"service_id": service.id, "starts_at": starts.isoformat()}, config=CONFIG
    )
    appointment_id = int(created.split("#")[1].split(":")[0])
    moved = await reschedule_booking.ainvoke(
        {
            "appointment_id": appointment_id,
            "new_starts_at": next_monday_at(15).isoformat(),
        },
        config=CONFIG,
    )
    assert "Rescheduled" in moved
    assert "15:00" in moved


async def test_booking_error_surfaces_as_message(service, mechanic):
    """BookingError text must reach the agent, not crash the tool."""
    result = await create_booking.ainvoke(
        {"service_id": service.id, "starts_at": next_monday_at(3).isoformat()},
        config=CONFIG,
    )
    assert "working hours" in result


async def test_tools_are_scoped_to_telegram_user(service, mechanic):
    created = await create_booking.ainvoke(
        {"service_id": service.id, "starts_at": next_monday_at(10).isoformat()},
        config=CONFIG,
    )
    appointment_id = int(created.split("#")[1].split(":")[0])
    stranger = {"configurable": {"telegram_id": 999, "client_name": "Mallory"}}
    result = await cancel_booking.ainvoke({"appointment_id": appointment_id}, config=stranger)
    assert "no appointment" in result
