from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.db.models import Service
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate
from app.services import booking

router = APIRouter(prefix="/services", tags=["services"])


@router.get("")
async def list_services(db: DbSession) -> list[ServiceRead]:
    return [ServiceRead.model_validate(s) for s in await booking.list_services(db)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceCreate, db: DbSession) -> ServiceRead:
    service = Service(**payload.model_dump())
    db.add(service)
    await db.commit()
    return ServiceRead.model_validate(service)


@router.patch("/{service_id}")
async def update_service(service_id: int, payload: ServiceUpdate, db: DbSession) -> ServiceRead:
    service = await db.get(Service, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    await db.commit()
    return ServiceRead.model_validate(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(service_id: int, db: DbSession) -> None:
    service = await db.get(Service, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    await db.delete(service)
    await db.commit()
