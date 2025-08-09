from typing import List, Optional

from pydantic import UUID4, BaseModel


class OrganisationCreateUpdate(BaseModel):
    name: Optional[str] = None
    phones: Optional[List[int]] = []
    building_uuid: Optional[UUID4] = None
    activities: Optional[List[UUID4]] = []


class OrganisationSchema(OrganisationCreateUpdate):
    uuid: UUID4
    activities: Optional[List["ActivityShema"]] = []
    phones: Optional[List["PhoneSchema"]] = []
    building: Optional["BuildingSchema"] = {}

    class Config:
        from_attributes = True


class PhoneCreate(BaseModel):
    number: str


class PhoneSchema(PhoneCreate):
    id: int

    class Config:
        from_attributes = True


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


class BuildingSchema(BaseModel):
    address: str
    uuid: UUID4
    latitude: float
    longitude: float

    class Config:
        from_attributes = True
