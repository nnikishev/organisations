import uuid
from typing import List

from fastapi import Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from pydantic import UUID4
from sqlalchemy import insert, select

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

    @router.post(
        "/buildings/",
        tags=["buildings"],
        response_model=BuildingSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Создать здание",
    )
    async def create_building(self, data: BuildingCreate):
        building = await super().create(data)
        return JSONResponse(
            jsonable_encoder(building), status_code=status.HTTP_201_CREATED
        )

    @router.get(
        "/buildings/",
        tags=["buildings"],
        response_model=BuildingSchema,
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
    ):
        buildings = await super().get_list(skip, limit, filters, order_by, sort_order)
        return JSONResponse(jsonable_encoder(buildings), status_code=status.HTTP_200_OK)


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
    async def get_nested_activities(self, uuid: UUID4):
        activities = await self._get_activities_from_parent(uuid)
        return list(activities)

    @router.post(
        "/activities/",
        tags=["activities"],
        response_model=ActivityShema,
        status_code=status.HTTP_201_CREATED,
        summary="Создать деятельность ",
    )
    async def create_activity(self, data: ActivityCreate):
        activity = await super().create(data)
        return JSONResponse(
            jsonable_encoder(activity), status_code=status.HTTP_201_CREATED
        )

    @router.get(
        "/activities/",
        tags=["activities"],
        response_model=ActivityShema,
        status_code=status.HTTP_200_OK,
        summary="Список деятельностей ",
    )
    async def list_activities(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = None,
        sort_order: str = SortOrder.DESC.value,
    ):
        filters = {}
        m2m_filters = {}
        activities = await super().get_list(
            skip, limit, filters, m2m_filters, order_by, sort_order
        )
        return JSONResponse(
            jsonable_encoder(activities), status_code=status.HTTP_200_OK
        )

    @router.get(
        "/activities/{uuid}",
        tags=["activities"],
        response_model=ActivityShema,
        status_code=status.HTTP_200_OK,
        summary="Получить деятельность ",
    )
    async def get_activitiy(self, uuid: UUID4):
        activity = await super().get(uuid)
        return JSONResponse(jsonable_encoder(activity), status_code=status.HTTP_200_OK)

    @router.patch(
        "/activities/{uuid}",
        tags=["activities"],
        response_model=ActivityShema,
        status_code=status.HTTP_200_OK,
        summary="Изменить деятельность ",
    )
    async def update_activitiy(self, uuid: UUID4, data: ActivityCreate):
        activity = await super().update(uuid, data)
        return JSONResponse(jsonable_encoder(activity), status_code=status.HTTP_200_OK)


@cbv(router)
class OrganizationViews(CRUD):
    model = Organization
    create_update_schema = OrganisationCreateUpdate

    @router.post(
        "/organizations/",
        tags=["organizations"],
        response_model=OrganisationSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Создать организацию",
    )
    async def create_organisation(self, data: OrganisationCreateUpdate):
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
        return JSONResponse(
            jsonable_encoder(organisation), status_code=status.HTTP_201_CREATED
        )

    @router.get(
        "/organizations/",
        tags=["organizations"],
        response_model=OrganisationSchema,
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
        return JSONResponse(
            jsonable_encoder(organisations), status_code=status.HTTP_200_OK
        )

    @router.get(
        "/organizations/{uuid}",
        tags=["organizations"],
        response_model=OrganisationSchema,
        status_code=status.HTTP_200_OK,
        summary="Список организаций",
    )
    async def get_organization(self, uuid: UUID4):
        organisation = await super().get(uuid)
        return JSONResponse(
            jsonable_encoder(organisation), status_code=status.HTTP_200_OK
        )

    @router.patch(
        "/organizations/{uuid}",
        tags=["organizations"],
        response_model=OrganisationSchema,
        status_code=status.HTTP_200_OK,
        summary="Изменить организацию",
    )
    async def update_organization(self, uuid: UUID4, data: OrganisationCreateUpdate):
        organisation = await super().update(uuid, data)
        return JSONResponse(
            jsonable_encoder(organisation), status_code=status.HTTP_200_OK
        )


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
    async def create_activity(self, data: PhoneCreate):
        phone = await super().create(data)
        return JSONResponse(
            jsonable_encoder(phone), status_code=status.HTTP_201_CREATED
        )
