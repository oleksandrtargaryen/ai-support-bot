from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.main import create_app
from app.services.booking import create_booking

HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture
async def client(db_factory):
    app = create_app()

    async def override_get_db():
        async with db_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_admin_api_requires_key(client):
    response = await client.get("/api/v1/services")
    assert response.status_code == 401


async def test_admin_api_rejects_wrong_key(client):
    response = await client.get("/api/v1/services", headers={"X-API-Key": "nope"})
    assert response.status_code == 401


async def test_service_crud(client):
    created = await client.post(
        "/api/v1/services",
        json={"name": "Brake check", "duration_min": 30, "price": "25.00"},
        headers=HEADERS,
    )
    assert created.status_code == 201
    service_id = created.json()["id"]

    listed = await client.get("/api/v1/services", headers=HEADERS)
    assert [s["name"] for s in listed.json()] == ["Brake check"]

    patched = await client.patch(
        f"/api/v1/services/{service_id}", json={"price": "30.00"}, headers=HEADERS
    )
    assert patched.json()["price"] == "30.00"

    deleted = await client.delete(f"/api/v1/services/{service_id}", headers=HEADERS)
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/services", headers=HEADERS)).json() == []


async def test_service_validation(client):
    response = await client.post(
        "/api/v1/services",
        json={"name": "Bad", "duration_min": -5, "price": "10"},
        headers=HEADERS,
    )
    assert response.status_code == 422


async def test_appointments_list_and_cancel(client, session, service, mechanic, settings):
    day = datetime.now() + timedelta(days=7)
    while day.weekday() != 0:
        day += timedelta(days=1)
    starts = day.replace(hour=10, minute=0, second=0, microsecond=0)
    appt = await create_booking(session, 1, service.id, starts, settings, datetime.now())

    listed = await client.get("/api/v1/appointments", headers=HEADERS)
    assert listed.status_code == 200
    assert [a["id"] for a in listed.json()] == [appt.id]

    cancelled = await client.delete(f"/api/v1/appointments/{appt.id}", headers=HEADERS)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    again = await client.delete(f"/api/v1/appointments/{appt.id}", headers=HEADERS)
    assert again.status_code == 409

    scheduled_only = await client.get(
        "/api/v1/appointments", params={"status_filter": "scheduled"}, headers=HEADERS
    )
    assert scheduled_only.json() == []


async def test_appointment_not_found(client):
    response = await client.delete("/api/v1/appointments/12345", headers=HEADERS)
    assert response.status_code == 404
