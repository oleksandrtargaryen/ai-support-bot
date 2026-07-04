from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import AppointmentStatus


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    service_id: int
    mechanic_id: int
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
