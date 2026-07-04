from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ServiceCreate(BaseModel):
    name: str = Field(max_length=100)
    description: str = ""
    duration_min: int = Field(gt=0)
    price: Decimal = Field(ge=0)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    duration_min: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    duration_min: int
    price: Decimal
