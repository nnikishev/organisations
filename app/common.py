from typing import Any, List, Optional, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel

from app.db import PostgresDatabase
from app.enums import SortOrder, StorageType
from app.logging import logger
from settings import MASTER_DB

T = TypeVar("T", bound=Any)
M = TypeVar("M", bound=BaseModel)


class CRUD:
    model = None
    create_update_schema = None
    lookup_field = "uuid"

    def __init__(self):
        match MASTER_DB:
            case StorageType.POSTGRES.value:
                self.db = PostgresDatabase()

    async def create(self, obj_in: M) -> T:
        try:
            return await self.db.create(obj_in, self.model)
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Ошибка создания {self.model.__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка создания {self.model.__name__}",
            )

    async def get(self, id: Any) -> Optional[T]:
        try:
            return await self.db.fetch_one(self.model, {self.lookup_field: id})
        except Exception as e:
            logger.error(f"Ошибка получения {self.model.__name__} {id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} не найден",
            )

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters=None,
        m2m_filters=None,
        name: str = None,
        order_by: str = None,
        sort_order: str = SortOrder.DESC.value,
    ) -> List[T]:
        try:
            return await self.db.fetch_many(
                self.model,
                filters=filters,
                m2m_filters=m2m_filters,
                name=name,
                skip=skip,
                limit=limit,
                order_by=order_by,
                sort_order=sort_order,
            )
        except Exception as e:
            logger.error(f"Ошибка получения списка {self.model.__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка получения списка  {self.model.__name__}",
            )

    async def update(self, id: Any, obj_in: M) -> Optional[T]:
        try:
            update_data = obj_in.model_dump(exclude_unset=True)
            return await self.db.update(
                self.model, {self.lookup_field: id}, update_data, return_updated=True
            )
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Ошибка обновления {self.model.__name__} {id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка обновления {self.model.__name__}",
            )

    async def delete(self, id: Any) -> bool:
        try:
            return await self.db.delete(self.model, {self.lookup_field: id})
        except Exception as e:
            logger.error(f"Ошибка удаления {self.model.__name__} {id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка удаления {self.model.__name__}",
            )
