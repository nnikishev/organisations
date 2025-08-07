from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from settings import (
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    DB_CONN_TIMEOUT,
    DB_ONESQL_TIMEOUT,
)

def get_db_url():
    return f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_session(db_url: str = None):
    if not db_url:
        db_url = get_db_url()
    
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