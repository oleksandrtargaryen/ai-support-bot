from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.db.models import Appointment, AppointmentStatus
from app.schemas.appointment import AppointmentRead

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("")
async def list_appointments(
    db: DbSession, status_filter: AppointmentStatus | None = None
) -> list[AppointmentRead]:
    query = select(Appointment).order_by(Appointment.starts_at)
    if status_filter is not None:
        query = query.where(Appointment.status == status_filter)
    appointments = (await db.execute(query)).scalars()
    return [AppointmentRead.model_validate(a) for a in appointments]


@router.delete("/{appointment_id}")
async def cancel_appointment(appointment_id: int, db: DbSession) -> AppointmentRead:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    if appointment.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Appointment is already {appointment.status.value}"
        )
    appointment.status = AppointmentStatus.CANCELLED
    await db.commit()
    return AppointmentRead.model_validate(appointment)
