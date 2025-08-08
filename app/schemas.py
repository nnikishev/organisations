from typing import List, Optional

from pydantic import UUID4, BaseModel


class OrganisationCreateUpdate(BaseModel):
    name: Optional[str] = None
    phones: Optional[List[int]] = []
    building_uuid: Optional[UUID4] = None
    activities: Optional[List[UUID4]] = []


class OrganisationSchema(OrganisationCreateUpdate):
    uuid: UUID4
    activities: List["ActivityShema"]
    phones: List["PhoneSchema"]
    building: "BuildingSchema"

    class Config:
        orm_mode = True


class PhoneCreate(BaseModel):
    number: str


class PhoneSchema(PhoneCreate):
    id: int

    class Config:
        orm_mode = True


class ActivityCreate(BaseModel):
    name: str
    parent_uuid: Optional[UUID4] = None


class ActivityShema(ActivityCreate):
    uuid: UUID4

    class Config:
        orm_mode = True


class BuildingCreate(BaseModel):
    address: str
    latitude: float
    longitude: float


class BuildingSchema(BuildingCreate):
    uuid: UUID4

    class Config:
        orm_mode = True
