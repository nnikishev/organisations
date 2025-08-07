from typing import Any, Dict, List, Optional, Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import asc, delete, desc, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.abstractions import Database
from app.enums import SortOrder
from app.logging import logger
from settings import (
    DB_CONN_TIMEOUT,
    DB_HOST,
    DB_NAME,
    DB_ONESQL_TIMEOUT,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    PAGE_SIZE,
)

T = TypeVar("T")


class PostgresDatabase(Database):
    def __init__(self):
        self.lookup_field = "uuid"

    def get_db_url(self) -> str:
        return f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    def get_session(self, db_url: str = None) -> AsyncSession:
        if not db_url:
            db_url = self.get_db_url()

        engine = create_async_engine(
            db_url,
            echo=True,
            future=True,
            connect_args={
                "timeout": DB_CONN_TIMEOUT,
                "command_timeout": DB_ONESQL_TIMEOUT,
            },
        )
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        return async_session()

    async def create(self, new: Any, model: Type[T]) -> T:
        new_object = model(**new.dict(exclude_none=True))
        async with self.get_session() as session:
            try:
                session.add(new_object)
                await session.commit()
                await session.refresh(new_object)
                return new_object
            except IntegrityError as err:
                await session.rollback()
                logger.error(err)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{model.__name__} с данным именем уже существует",
                )
            except SQLAlchemyError as err:
                await session.rollback()
                logger.error(err)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"При добавлении {model.__name__} произошла ошибка. Подробнее: {err}",
                )

    async def fetch_one(self, model: Type[T], filters: Dict = None) -> Optional[T]:
        async with self.get_session() as session:
            stmt = select(model)
            if filters:
                stmt = stmt.filter_by(**filters)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def fetch_many(
        self,
        model: Type[T],
        filters: Dict = None,
        skip: int = 0,
        limit: int = PAGE_SIZE,
        order_by: str = None,
        sort_order: str = SortOrder.DESC.value,
    ) -> List[T]:
        async with self.get_session() as session:
            stmt = select(model).offset(skip).limit(limit)

            if filters:
                stmt = stmt.filter_by(**filters)

            if order_by:
                column = getattr(model, order_by, None)
                if column is not None:
                    if sort_order == SortOrder.DESC.value:
                        stmt = stmt.order_by(desc(column))
                    else:
                        stmt = stmt.order_by(asc(column))

            result = await session.execute(stmt)
            return result.scalars().all()

    async def update(
        self,
        model: Type[T],
        filters: Dict,
        update_data: Dict,
        return_updated: bool = False,
    ) -> Optional[T]:
        async with self.get_session() as session:
            try:
                stmt = update(model).filter_by(**filters).values(**update_data)

                if return_updated:
                    stmt = stmt.returning(model)
                    result = await session.execute(stmt)
                    updated_obj = result.scalars().first()
                    await session.commit()
                    return updated_obj
                else:
                    await session.execute(stmt)
                    await session.commit()
                    return None

            except IntegrityError as err:
                await session.rollback()
                logger.error(err)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ошибка при обновлении {model.__name__}. Подробнее: {err}",
                )
            except SQLAlchemyError as err:
                await session.rollback()
                logger.error(err)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ошибка при обновлении {model.__name__}. Подробнее: {err}",
                )

    async def delete(self, model: Type[T], filters: Dict) -> bool:
        async with self.get_session() as session:
            try:
                stmt = delete(model).filter_by(**filters)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
            except SQLAlchemyError as err:
                await session.rollback()
                logger.error(err)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ошибка при удалении {model.__name__}. Подробнее: {err}",
                )
