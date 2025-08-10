import uuid
from typing import List, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Point
from pydantic import UUID4
from sqlalchemy import func, insert, select

from app.common import CRUD
from app.db import PostgresDatabase
from app.enums import SortOrder
from app.logging import logger
from app.models import (
    Activity,
    Building,
    Organization,
    Phone,
    organization_activity,
    organization_phone,
)
from app.schemas import (
    ActivityCreate,
    ActivityShema,
    BuildingCreate,
    BuildingSchema,
    OrganisationCreateUpdate,
    OrganisationSchema,
    PhoneCreate,
    PhoneSchema,
)
from settings import API_KEY

db = PostgresDatabase()
router = InferringRouter()


def api_key_auth(api_key: str = Header(..., alias="API-Key")):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка авторизации",
        )
    ...


@cbv(router)
class BuildingViews(CRUD):
    model = Building
    create_update_schema = BuildingCreate

    @router.get(
        "/buildings/nearby/",
        tags=["geo_methods"],
        response_model=List[BuildingSchema],
        summary="Поиск зданий в заданной области",
    )
    async def get_buildings_in_area(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius: Optional[float] = None,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lng: Optional[float] = None,
        max_lng: Optional[float] = None,
        api_key: str = Depends(api_key_auth),
    ):
        if radius is None and not all([min_lat, max_lat, min_lng, max_lng]):
            raise HTTPException(
                400, "Укажите либо radius, либо все границы прямоугольника"
            )
        if radius is not None and (lat is None or lng is None):
            raise HTTPException(
                400, "Для радиусного поиска нужны оба параметра: lat и lng"
            )
        geog_point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Geography)
        if radius is not None:
            stmt = select(Building).where(
                func.ST_DWithin(Building.location.cast(Geography), geog_point, radius)
            )
        else:
            stmt = select(Building).where(
                func.ST_Y(Building.location).between(min_lat, max_lat),
                func.ST_X(Building.location).between(min_lng, max_lng),
            )
        async with PostgresDatabase.get_session() as session:
            result = await session.execute(stmt)
            buildings = result.scalars().all()
        return buildings

    @router.post(
        "/buildings/",
        tags=["buildings"],
        response_model=BuildingSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Создать здание",
    )
    async def create_building(
        self, data: BuildingCreate, api_key: str = Depends(api_key_auth)
    ):
        location = func.ST_SetSRID(ST_Point(data.longitude, data.latitude), 4326)
        new = {"address": data.address, "location": location}
        building = await super().create(new)
        return building

    @router.get(
        "/buildings/",
        tags=["buildings"],
        response_model=List[BuildingSchema],
        status_code=status.HTTP_200_OK,
        summary="Список зданий",
    )
    async def list_buildings(
        self,
        skip: int = 0,
        limit: int = 100,
        filters=None,
        order_by: str = None,
        sort_order: str = SortOrder.DESC.value,
        api_key: str = Depends(api_key_auth),
    ):
        buildings = await super().get_list(
            skip=skip,
            limit=limit,
            filters=filters,
            order_by=order_by,
            sort_order=sort_order,
        )
        return buildings


@cbv(router)
class ActivitiesViews(CRUD):
    model = Activity
    create_update_schema = ActivityCreate

    @staticmethod
    async def _get_activities_from_parent(activity_uuid: UUID4):
        async with PostgresDatabase.get_session() as session:
            result = await session.execute(
                select(Activity).where(Activity.uuid == activity_uuid)
            )
            current_activity = result.scalars().first()
            if not current_activity:
                return set()

            activities = {current_activity}

            result = await session.execute(
                select(Activity).where(Activity.parent_uuid == activity_uuid)
            )
            children = result.scalars().all()

            for child in children:
                child_activities = await ActivitiesViews._get_activities_from_parent(
                    child.uuid
                )
                activities.update(child_activities)

        return activities

    @router.get(
        "/activities/{uuid}/get_nested_activities",
        tags=["activities"],
        response_model=List[ActivityShema],
        status_code=status.HTTP_200_OK,
        summary="Список вложенных деятельностей от родителя",
    )
    async def get_nested_activities(
        self, uuid: UUID4, api_key: str = Depends(api_key_auth)
    ):
        activities = await self._get_activities_from_parent(uuid)
        return list(activities)

    @router.post(
        "/activities/",
        tags=["activities"],
        response_model=ActivityShema,
        status_code=status.HTTP_201_CREATED,
        summary="Создать деятельность ",
    )
    async def create_activity(
        self, data: ActivityCreate, api_key: str = Depends(api_key_auth)
    ):
        activity = await super().create(data)
        return activity

    @router.get(
        "/activities/",
        tags=["activities"],
        response_model=List[ActivityShema],
        status_code=status.HTTP_200_OK,
        summary="Список деятельностей ",
    )
    async def list_activities(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = None,
        sort_order: str = SortOrder.DESC.value,
        api_key: str = Depends(api_key_auth),
    ):
        filters = {}
        m2m_filters = {}
        activities = await super().get_list(
            skip, limit, filters, m2m_filters, order_by, sort_order
        )
        return activities

    @router.get(
        "/activities/{uuid}",
        tags=["activities"],
        response_model=ActivityShema,
        status_code=status.HTTP_200_OK,
        summary="Получить деятельность ",
    )
    async def get_activitiy(self, uuid: UUID4, api_key: str = Depends(api_key_auth)):
        activity = await super().get(uuid)
        return JSONResponse(jsonable_encoder(activity), status_code=status.HTTP_200_OK)

    @router.patch(
        "/activities/{uuid}",
        tags=["activities"],
        response_model=ActivityShema,
        status_code=status.HTTP_200_OK,
        summary="Изменить деятельность ",
    )
    async def update_activitiy(
        self, uuid: UUID4, data: ActivityCreate, api_key: str = Depends(api_key_auth)
    ):
        activity = await super().update(uuid, data)
        return activity


@cbv(router)
class OrganizationViews(CRUD):
    model = Organization
    create_update_schema = OrganisationCreateUpdate

    @router.get(
        "/organizations/nearby/",
        tags=["geo_methods"],
        response_model=List[OrganisationSchema],
        summary="Поиск организаций в заданной области",
    )
    async def get_organizations_in_area(
        self,
        lat: float,
        lng: float,
        radius: float = None,
        min_lat: float = None,
        max_lat: float = None,
        min_lng: float = None,
        max_lng: float = None,
        api_key: str = Depends(api_key_auth),
    ):
        buildings = await BuildingViews().get_buildings_in_area(
            lat=lat,
            lng=lng,
            radius=radius,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )

        if not buildings:
            return []

        building_uuids = [b.uuid for b in buildings]
        stmt = select(Organization).where(
            Organization.building_uuid.in_(building_uuids)
        )
        async with PostgresDatabase.get_session() as session:
            result = await session.execute(stmt)
        return result.scalars().all()

    @router.post(
        "/organizations/",
        tags=["organizations"],
        response_model=OrganisationSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Создать организацию",
    )
    async def create_organisation(
        self, data: OrganisationCreateUpdate, api_key: str = Depends(api_key_auth)
    ):
        async with PostgresDatabase.get_session() as session:
            organisation_uuid = uuid.uuid4()
            organisation = self.model(
                uuid=organisation_uuid, name=data.name, building_uuid=data.building_uuid
            )
            session.add(organisation)
            await session.flush()

            if data.activities:
                try:
                    activities = [
                        {"activity_id": phone, "organization_id": organisation_uuid}
                        for phone in data.activities
                    ]
                    await session.execute(insert(organization_activity), activities)

                except Exception as err:
                    logger.error(
                        f"Ошибка добавления телефона организации. Подробнее {err}"
                    )
                    raise HTTPException(
                        detail=f"Ошибка добавления телефона организации. Подробнее {err}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            if data.phones:
                try:
                    phones = [
                        {"phone_id": phone, "organization_id": organisation_uuid}
                        for phone in data.phones
                    ]
                    await session.execute(insert(organization_phone), phones)
                except Exception as err:
                    logger.error(
                        f"Ошибка добавления телефона организации. Подробнее {err}"
                    )
                    raise HTTPException(
                        detail=f"Ошибка добавления телефона организации. Подробнее {err}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            await session.commit()
            await session.refresh(organisation)
        return organisation

    @router.get(
        "/organizations/",
        tags=["organizations"],
        response_model=List[OrganisationSchema],
        status_code=status.HTTP_200_OK,
        summary="Список организаций",
    )
    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 100,
        building_uuid: UUID4 = None,
        activity_uuid: UUID4 = None,
        only_parent_activity: bool = True,
        name: str = None,
        phone_id: int = None,
        order_by: str = None,
        sort_order: str = SortOrder.DESC.value,
        api_key: str = Depends(api_key_auth),
    ):
        filters = {}
        m2m_filters = {}
        if building_uuid:
            filters["building_uuid"] = building_uuid
        if activity_uuid:
            if only_parent_activity:
                m2m_filters["activities"] = Activity.uuid == activity_uuid
            else:
                nested_activities = await ActivitiesViews._get_activities_from_parent(
                    activity_uuid
                )
                m2m_filters["activities"] = Activity.uuid.in_(
                    [a.uuid for a in nested_activities]
                )
        if phone_id:
            m2m_filters["phones"] = Phone.id == phone_id
        organisations = await super().get_list(
            skip, limit, filters, m2m_filters, name, order_by, sort_order
        )
        return organisations

    @router.get(
        "/organizations/{uuid}",
        tags=["organizations"],
        response_model=OrganisationSchema,
        status_code=status.HTTP_200_OK,
        summary="Список организаций",
    )
    async def get_organization(self, uuid: UUID4, api_key: str = Depends(api_key_auth)):
        organisation = await super().get(uuid)
        return organisation

    @router.patch(
        "/organizations/{uuid}",
        tags=["organizations"],
        response_model=OrganisationSchema,
        status_code=status.HTTP_200_OK,
        summary="Изменить организацию",
    )
    async def update_organization(
        self,
        uuid: UUID4,
        data: OrganisationCreateUpdate,
        api_key: str = Depends(api_key_auth),
    ):
        organisation = await super().update(uuid, data)
        return organisation


@cbv(router)
class PhonesViews(CRUD):
    model = Phone
    create_update_schema = PhoneCreate

    @router.post(
        "/phones/",
        tags=["phones"],
        response_model=PhoneSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Добавить телефон",
    )
    async def create_activity(
        self, data: PhoneCreate, api_key: str = Depends(api_key_auth)
    ):
        phone = await super().create(data)
        return phone
