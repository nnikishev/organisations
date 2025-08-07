from typing import List, Optional

from pydantic import UUID4, BaseModel


class OrganisationCreateUpdate(BaseModel):
    name: str
    phone: Optional[str] = None
    building_uuid: Optional[UUID4] = None
    activities_uuid: Optional[List[UUID4]] = None


class OrganisationSchema(OrganisationCreateUpdate):
    uuid: UUID4
