from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError, PendingRollbackError, DatabaseError, SQLAlchemyError
from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    async_scoped_session
)
from src.settings.config import DATABASE_URL


session_engine = create_async_engine(DATABASE_URL, echo=True)

async_session = async_sessionmaker(bind=session_engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def get_session():
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()