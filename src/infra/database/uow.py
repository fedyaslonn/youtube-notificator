from contextlib import asynccontextmanager
from typing import Callable, Iterable, Coroutine

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database.repository import *
from src.infra.database.session import get_session

from abc import ABC

class UnitOfWorkBase(ABC):

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    async def commit(self):
        raise NotImplementedError()

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError()

class UnitOfWork(UnitOfWorkBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        self.users = UserRepository(self.session)
        self.authors = AuthorRepository(self.session)
        self.videos = VideoRepository(self.session)
        self.subscriptions = SubscriptionRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()


async def get_unit_of_work():
    async with get_session() as session:
        uow = UnitOfWork(session)
        async with uow:
            return uow