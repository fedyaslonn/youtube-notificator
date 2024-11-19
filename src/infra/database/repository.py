from abc import ABC, abstractmethod
from datetime import datetime
from distutils.util import execute
from logging import exception

from requests import session
from sqlalchemy import Result, asc, delete, desc, func, select, update, false
from sqlalchemy.testing.plugin.plugin_base import options
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import and_


from typing import Any, AsyncGenerator, Generic, Type, Optional

from src.domain.authors.models import AuthorWithFollowers, AuthorPublic, AuthorWithUnwatchedVideos, AuthorWithSubscriptions
from src.domain.videos.models import VideoPublic
from src.infra.database.tables import T, user_author
from src.infra.database.tables import User, Author, Video, Subscription
from sqlalchemy.exc import DatabaseError, NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.infra.database.session import get_session
from sqlalchemy import select, func, text

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class GenericRepository(Generic[T], ABC):
    @abstractmethod
    def get_by_id(self, id: int):
        raise NotImplementedError()

    @abstractmethod
    def get_all(self, limit: Optional[int] = None):
        raise NotImplementedError()

    @abstractmethod
    def create(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def update(self, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def delete(self, **kwargs):
        raise NotImplementedError()


class GenericSQLRepository(GenericRepository[T], ABC):
    def __init__(self, model_cls: Type[T], session: AsyncSession):
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, id: int):
        result = await self.session.get(self.model_cls, id)
        return result

    async def get_all(self, limit: Optional[int] = None):
        stmt = select(self.model_cls)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj: T):
        async with self.session.begin():
            self.session.add(obj)
            await self.session.commit()
            await self.session.refresh(obj)
        return obj

    async def update(self, obj: T, **kwargs):
        async with self.session.begin():
            if obj is None:
                raise NoResultFound("Объект не найден")

            for key, val in kwargs.items():
                setattr(obj, key, val)

            self.session.add(obj)
            await self.session.commit()
            await self.session.refresh(obj)

        return obj

    async def delete(self, obj: T):
        async with self.session.begin():
            await self.session.delete(obj)
            await self.session.commit()

    async def delete_by_id(self, id: int):
        async with self.session.begin():
            obj = await self.get_by_id(id)
            if obj:
                await self.session.delete(obj)
                await self.session.commit()


class UserRepositoryBase(GenericRepository[User], ABC):
    @abstractmethod
    async def get_by_username(self, username: str):
        raise NotImplementedError()

    @abstractmethod
    async def get_by_tag(self, tag: str):
        raise NotImplementedError()

class AuthorRepositoryBase(GenericRepository[Author], ABC):
    @abstractmethod
    async def get_by_name(self, author_name: str):
        raise NotImplementedError()

    @abstractmethod
    async def get_by_url(self, author_url: str):
        raise NotImplementedError()


class VideoRepositoryBase(GenericRepository[Video], ABC):
    @abstractmethod
    async def get_by_url(self, video_url: str):
        raise NotImplementedError()

    @abstractmethod
    async def get_by_title(self, title:str):
        raise NotImplementedError()

    @abstractmethod
    async def get_by_duration(self, duration: int):
        raise NotImplementedError()

    @abstractmethod
    async def get_by_date(self, date: datetime):
        raise NotImplementedError()

class SubscriptionRepositoryBase(GenericRepository[Subscription], ABC):
    @abstractmethod
    async def get_last_notified(self):
        raise NotImplementedError()

class AuthorRepository(GenericSQLRepository[Author], AuthorRepositoryBase):
    def __init__(self, session: AsyncSession):
        super().__init__(Author, session)

    
    async def get_by_name(self, name: str):
        try:
            stmt = select(Author).where(Author.author == name)
            result = await self.session.execute(stmt)
            author = result.scalar_one_or_none()
            return author

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получения автора по имени {str(e)}")

    
    async def get_by_url(self, author_url: str):
        try:
            stmt = select(Author).where(Author.author_url == author_url)
            result = await self.session.execute(stmt)
            author = result.scalar_one_or_none()
            return author

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получения автора по url {str(e)}")


    async def get_all_videos_by_author(self, author_id: int):
        try:
            stmt = select(Author).options(selectinload(Author.videos)).where(Author.id == author_id)
            result = await self.session.execute(stmt)
            author_info = result.scalars().all()

            if author_info:
                return author_info

            else:
                return []

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить все видео автора {str(e)}")

    async def get_by_video(self, video_url: str):
        try:
            stmt = select(Author).join(Video).options(selectinload(Author.videos)).where(Video.url == video_url)
            result = await self.session.execute(stmt)
            author_info = result.one_or_none()
            return author_info

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить автора по видео {str(e)}")

    async def get_authors_with_count_followers(self):
        try:
            cte_followers_count = (
                select(Subscription.author_id, func.count(Subscription.id).label("followers_count"))
                .group_by(Subscription.author_id)
                .cte("cte_followers_count")
            )

            stmt = (
                select(Author).add_columns(cte_followers_count.c.followers_count)
                .join(cte_followers_count, cte_followers_count.c.author_id == Author.id)
                .options(selectinload(Author.followers),
                         selectinload(Author.videos))
            )
            result = await self.session.execute(stmt)
            authors = result.all()

            author_data = [
                AuthorWithFollowers(
                    id=author.id,
                    author=author.author,
                    author_url=author.author_url,
                    followers_count=followers_count if followers_count is not None else 0,
                    videos=[VideoPublic(url=video.url, title=video.title, duration=video.duration,
                                        published_at=video.published_at) for video in author.videos]
                )
                for author, followers_count in authors
            ]
            return author_data

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить авторов с подписчиками: {str(e)}")


    async def count_all_followers(self, author_id: int):
        try:
            stmt = select(func.count(User.id)).select_from(user_author).where(user_author.c.author_id == author_id)
            result = await self.session.execute(stmt)
            followers = result.scalar()
            return followers or 0

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить число подписчиков {str(e)}")


    async def get_last_author(self):
        try:
            stmt = select(Author).order_by(Author.id.desc()).limit(1)
            result = await self.session.execute(stmt)
            last_author = result.scalar_one_or_none()
            return last_author

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить последнего автора {str(e)}")


    async def create_by_url(self, author_url: str):
        try:
            author_exists_stmt = select(Author).where(Author.author_url == author_url).exists()
            author_exists_query = select(author_exists_stmt)
            author_exists = await self.session.execute(author_exists_query)

            if not author_exists.scalar():
                new_author = Author(author_url=author_url)
                self.session.add(new_author)
                await self.session.commit()
                await self.session.refresh(new_author)
                return new_author
            else:
                raise SQLAlchemyError(f"Автор уже существует в БД")

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise SQLAlchemyError(f"Ошибка при создании автора {str(e)}")

    async def create_author(self, author: str, author_url: str, current_user: User):
        try:
            author_exists_stmt = (select(Author).options(selectinload(Author.videos), selectinload(Author.followers), selectinload(Author.subscriptions)).where(and_(Author.author == author, Author.author_url == author_url)))
            author_instance = (await self.session.execute(author_exists_stmt)).scalar_one_or_none()

            if author_instance is None:
                author_instance = Author(author=author, author_url=author_url)
                author_instance.followers.append(current_user)
                self.session.add(author_instance)
                await self.session.commit()
                new_subscription = Subscription(user_id=current_user.id, author_id=author_instance.id, last_notified_at=datetime.utcnow())
                self.session.add(new_subscription)
                await self.session.commit()
                await self.session.refresh(new_subscription)

            else:
                subscription_exists_stmt = select(Subscription).options(joinedload(Subscription.user), joinedload(Subscription.author)).where(
                    and_(Subscription.author_id == author_instance.id, Subscription.user_id == current_user.id)
                )
                subscription_instance = (await self.session.execute(subscription_exists_stmt)).scalar_one_or_none()

                if subscription_instance is None:
                    author_instance.followers.append(current_user)
                    new_subscription = Subscription(user_id=current_user.id,
                                                        author_id=author_instance.id,
                                                        last_notified_at=datetime.utcnow())
                    self.session.add(new_subscription)
                    await self.session.commit()
                    await self.session.refresh(new_subscription)
                else:
                    raise ValueError("Пользователь уже подписан на этого автора!")

            return author_instance

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise SQLAlchemyError(f"Ошибка при создании нового автора {str(e)}")


    async def delete_author(self, id: int):
        try:
            stmt = select(Author).where(Author.id == id)

            result = await self.session.execute(stmt)
            loaded_author = result.scalar_one_or_none()

            if loaded_author:
                await self.session.delete(loaded_author)
                await self.session.commit()
                return True
            return False

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке удаления автора {str(e)}")


    async def get_all_followers(self, author_id: int):
        try:
            stmt = (select(Author).join(Subscription).options(selectinload(Author.followers),
                                                              selectinload(Author.subscriptions))
                    .where(Author.id == author_id).order_by(Subscription.last_notified_at))

            result = await self.session.execute(stmt)
            loaded_info = result.scalar_one_or_none()

            if loaded_info:
                followers_ids = [follower.id for follower in loaded_info.followers]
                return AuthorWithSubscriptions(
                    id = loaded_info.id,
                    author = loaded_info.author,
                    author_url = loaded_info.author_url,
                    author_id = loaded_info.id,
                    last_notified_at=loaded_info.subscriptions.last_notified_at if loaded_info.subscriptions else None,
                    followers = followers_ids
                )

            else:
                return None

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить всех подписчиков автора, отсортированных по дате последнего уведомления {str(e)}")

    async def get_all_authors_with_more_10_videos(self):
        try:
            cte_videos_count = (
                select(Video.author_id, func.count(Video.id).label("video_count"))
                .group_by(Video.author_id)
                .where(Video.viewed == False)
                .having(func.count(Video.id) >= 10)
                .cte("cte_videos_count")
            )

            stmt = (
                select(Author).add_columns(cte_videos_count.c.video_count)
                .join(cte_videos_count, cte_videos_count.c.author_id == Author.id)
                .options(selectinload(Author.videos))
            )
            result = await self.session.execute(stmt)
            authors = result.all()

            author_data = [
                AuthorWithUnwatchedVideos(
                    id=author.id,
                    author=author.author,
                    author_url=author.author_url,
                    videos_count=video_count if video_count is not None else 0,
                    videos=[VideoPublic(url=video.url, title=video.title, duration=video.duration,
                                        published_at=video.published_at) for video in author.videos if not video.viewed]
                )
                for author, video_count in authors
            ]
            return author_data

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить авторов с более чем 10 видео: {str(e)}")

    async def get_authors_with_unwatched_videos(self):
        try:
            stmt = select(Author).options(selectinload(Author.videos))

            result = await self.session.execute(stmt)
            authors = result.scalars().all()
            return authors

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить авторов с непросмотренными видео: {str(e)}")

    async def get_authors_with_followers(self):
        try:
            stmt = select(Author).options(selectinload(Author.followers), selectinload(Author.videos))

            result = await self.session.execute(stmt)
            authors = result.scalars().all()

            author_data = [
                AuthorWithFollowers(
                    id=author.id,
                    author=author.author,
                    author_url=author.author_url,
                    followers_count=len(author.followers),
                    videos=[VideoPublic(url=video.url, title=video.title, duration=video.duration,
                                        published_at=video.published_at)
                            for video in author.videos]
                )
                for author in authors
            ]
            return author_data


        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить авторов с их подписчиками: {str(e)}")

class VideoRepository(GenericSQLRepository[Video], VideoRepositoryBase):
    def __init__(self, session: AsyncSession):
        super().__init__(Video, session)

    
    async def get_by_url(self, url: str):
        try:
            stmt = select(Video).where(Video.url == url)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить видео по url: {str(e)}")


    async def get_by_title(self, title: str):
        try:
            stmt = select(Video).where(Video.title == title)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить видео по названию: {str(e)}")
    
    async def get_by_duration(self, duration: str):
        try:
            stmt = select(Video).where(Video.duration == duration)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить видео по длине: {str(e)}")

    async def get_by_date(self, date: str):
        try:
            stmt = select(Video).options(joinedload(Video.author)).where(Video.published_at == date)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить видно по дате: {str(e)}")
    
    async def sort_all_videos_by_author_by_publication_date(self, author_id: int):
        try:
            stmt = (select(Video).join(Author).options(selectinload(Video.author)).where(Video.author_id == author_id)
            .order_by(desc(Video.published_at))
                )
            result = await self.session.execute(stmt)
            return result.scalars().all()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить видно по дате: {str(e)}")

    async def create_video(self, url: str, title: str, duration: str, published_at: str, author_id: int, user_id: int):
        try:
            video_exists_stmt = select(Video).options(joinedload(Video.author), joinedload(Video.user)).where(Video.url == url)
            video_instance = (await self.session.execute(video_exists_stmt)).scalar_one_or_none()

            if video_instance is None:
                new_video = Video(
                    url=url,
                    title=title,
                    duration=duration,
                    published_at=published_at,
                    author_id=author_id,
                    user_id=user_id
                )
                self.session.add(new_video)
                await self.session.commit()
                await self.session.refresh(new_video)
                return new_video

            else:
                raise ValueError(f"Видео уже существует в БД")

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке создать видео {str(e)}")
    
    async def delete_video(self, video_id: int):
        try:
            stmt = select(Video).where(Video.id == video_id)
            result = await self.session.execute(stmt)
            loaded_video = result.scalar_one_or_none()

            if loaded_video:
                await self.session.delete(loaded_video)
                await self.session.commit()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке удалить видео {str(e)}")


class SubscriptionRepository(GenericSQLRepository[Subscription], SubscriptionRepositoryBase):
    def __init__(self, session: AsyncSession):
        super().__init__(Subscription, session)

    
    async def get_author(self, author_id: int, user_id: int):
        try:
            stmt = (select(Subscription).join(Author)
                .options(selectinload(Subscription.author)).where(author_id == Subscription.author_id,
                                               Subscription.user_id == user_id))
            result = await self.session.execute(stmt)
            author = result.scalar_one_or_none()
            return author

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить автора с подписками {str(e)}")

    
    async def get_user(self, user_id: int):
        try:
            stmt = (select(Subscription).join(User).options(selectinload(Subscription.user)).
                    where(Subscription.user_id == user_id))
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            return user

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить пользователя по подписке {str(e)}")
    
    async def get_notifications(self):
        try:
            stmt = (select(Subscription).options(selectinload(Subscription.author),selectinload(Subscription.user))
                    .order_by(Subscription.last_notified_at.desc()))
            result = await self.session.execute(stmt)
            subscriptions = result.scalars().all()

            logger.info(f"Полученные подписки {subscriptions}")
            return subscriptions

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить уведомления {str(e)}")
    
    async def get_last_notified(self):
        try:
            stmt = select(Subscription).order_by(Subscription.last_notified_at.desc()).limit(1)
            result = await self.session.execute(stmt)
            subscription = result.scalar_one_or_none()
            return subscription

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка пр попытке получить последнее уведомление {str(e)}")
    
    async def create_subscription(self, user_id:int , author_id: int):
        try:
            subscription_exists_stmt = select(Subscription).options(joinedload(Subscription.author), joinedload(Subscription.user)).where(and_(Subscription.author_id == author_id,
                                                                                             Subscription.user_id == user_id))
            subscription_instance = (await self.session.execute(subscription_exists_stmt)).scalar_one_or_none()

            if subscription_instance is None:
                new_subscription = Subscription(user_id=user_id, author_id=author_id, last_notified_at=datetime.utcnow())
                self.session.add(new_subscription)
                await self.session.commit()
                await self.session.refresh(new_subscription)
                return new_subscription

            else:
                raise ValueError(f"Подписка уже существует!")
        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке создать подписку {str(e)}")

    async def get_author_info_by_subscription(self, sub_id: int):
        try:
            stmt = (select(Subscription.author.author, Subscription.last_notified_at)
                    .options(joinedload(Subscription.author)).where(Subscription.id == sub_id))
            result = await self.session.execute(stmt)
            row = result.fetchone()

            if row:
                return row.author, row.last_notified_at

            else:
                return None, None

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при получении данных подписки: {str(e)}")

    async def delete_subscription(self, id: int):
        try:
            stmt = select(Subscription).where(id == Subscription.id)
            result = await self.session.execute(stmt)
            loaded_subscription = result.scalar_one_or_none()

            if loaded_subscription:
                await self.session.delete(loaded_subscription)
                await self.session.commit()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке удаления подписки {str(e)}")

class UserRepository(GenericSQLRepository[User], UserRepositoryBase):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_all(self, limit: Optional[int] = None):
        try:
            stmt = select(User).options(selectinload(User.authors), selectinload(User.subscriptions))
            if limit is not None:
                stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return result.scalars().all()

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при получении списка пользователей {str(e)}")

    async def get_user(self, username: str, user_tag: str):
        try:
            stmt = select(User).where(and_(User.username == username, User.user_tag == user_tag))
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            return user

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при получении пользователя {str(e)}")

    async def get_by_username(self, username: str):
        try:
            stmt = select(User).where(User.username == username)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            return user

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить пользователя по именя {str(e)}")
    
    async def get_by_tag(self, tag: str):
        try:
            stmt = select(User).where(User.user_tag == tag)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            return user

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить пользователя по тегу {str(e)}")

    async def count_subscriptions(self, user_id: int):
        try:
            stmt = select(func.count(Subscription.id)).where(User.id == user_id)
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise SQLAlchemyError(f"Ошибка при попытке посчитать количество подписчиков пользователя {str(e)}")

    async def get_users_with_count_subscriptions(self):
        try:
            cte_subs_count = (
                select(Subscription.user_id, func.count(Subscription.id).label("subs_count"))
                .group_by(Subscription.user_id)
                .cte("cte_subscriptions_count")
            )

            stmt = (
                select(User)
                .outerjoin(cte_subs_count, cte_subs_count.c.user_id == User.id)
                .options(selectinload(User.subscriptions))
            )

            result = await self.session.execute(stmt)
            users = result.scalars().all()
            return users

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить всех пользователей вместе с количеством их подписок {str(e)}")

    async def get_users_with_authors_with_count_subcscriptions(self):
        try:
            cte_subs_count = (
                select(Subscription.user_id, func.count(Subscription.id).label("subs_count"))
                .group_by(Subscription.user_id)
                .cte("cte_subscriptions_count")
            )

            stmt = (
                select(User).options(selectinload(User.authors))
                .outerjoin(cte_subs_count, cte_subs_count.c.user_id == User.id)
                .options(selectinload(User.subscriptions)
            ))
            result = await self.session.execute(stmt)
            users = result.scalars().all()
            return users

        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Ошибка при попытке получить всех пользователей вместе с количеством их подписок и авторами {str(e)}")

    async def create_user(self, username: str, user_tag: str):
        try:
            user_exists_stmt = select(User).options(selectinload(User.authors), selectinload(User.videos), selectinload(User.subscriptions)).where(and_(User.username == username, User.user_tag == user_tag))
            user_instance = (await self.session.execute(user_exists_stmt)).scalar_one_or_none()

            if user_instance is None:
                new_user = User(username=username, user_tag=user_tag)
                self.session.add(new_user)
                await self.session.commit()
                await self.session.refresh(new_user)

                return new_user

            else:
                logger.info(f"Ошибка при создании пользователя, пользователь уже существует")
                raise SQLAlchemyError(f"Пользователь уже существует в БД")

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception(f"Ошибка при создании пользователя", exc_info=e)
            raise SQLAlchemyError(f"Ошибка при создании пользователя {str(e)}")
    
    async def delete_user(self, id: int):
        try:
            stmt = select(User).where(User.id == id)
            result = await self.session.execute(stmt)
            loaded_user = result.scalar_one_or_none()

            if loaded_user:
                await self.session.delete(loaded_user)
                await self.session.commit()
                return True
            return False

        except SQLAlchemyError as e:
            await self.session.rollback()
            raise SQLAlchemyError(f"Ошибка при попытке удаления пользователя {str(e)}")
