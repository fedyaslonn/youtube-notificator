from fastapi import FastAPI, APIRouter, Request, status, Depends, HTTPException, Query
from pyparsing import with_class
from sqlalchemy.sql.functions import current_user

from src.domain.authors.models import AuthorPublic, AuthorCreateRequestBody, Author, AuthorWithFollowers, \
    AuthorWithSubscriptions
from src.domain.authors.utils import convert_to_author_public
from src.domain.videos.models import Video
from src.infra.database.uow import get_unit_of_work, UnitOfWork
from src.logic.authentication.authentication import get_current_user, oauth2_scheme

from src.logic.commands.youtube_logic import get_channel, get_last_video_by_channel_name

from src.domain.authors.models import AuthorPublic

from typing import Optional, List

import os
import sys

from src.logic.kafka.subscription_logic.producers.notification_producer import NotificationProducer
from src.logic.kafka.subscription_logic.producers.subscription_producer import AuthorSubscriptionProducer


author_router = APIRouter(prefix="/authors", tags=["Authors"])

@author_router.post("/create_author", response_model=AuthorPublic, status_code=status.HTTP_201_CREATED)
async def create_author(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), channel_name: str = Query(...)):
    try:
        async with uow:
            current_user = await get_current_user(token=token, uow=uow)
            channel_info = await get_channel(channel_name)

            new_author = await uow.authors.create_author(author=channel_info.author, author_url=channel_info.author_url, current_user=current_user)

            if new_author:
                async with AuthorSubscriptionProducer() as author_subscription_producer:
                    await author_subscription_producer.produce_author_subscription(user_id=str(current_user.id), uow=uow)
                async with NotificationProducer() as notification_producer:
                    await notification_producer.produce_notification(user_id=str(current_user.user_tag),
                                                                     uow=uow)
        return new_author

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@author_router.delete("/delete_author/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_author(id: int, token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            author_deleted = await uow.authors.delete_author(id=id)

            if not author_deleted:
                raise HTTPException(status_code=404, detail="Не удалось удалить автора")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось удалить пользователя {str(e)}")


@author_router.get("/get_by_name", response_model=AuthorPublic, status_code=status.HTTP_200_OK)
async def get_by_name(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), name: str = Query(...)):
    try:
        async with uow:
            author_by_name = await uow.authors.get_by_name(name=name)

            if not author_by_name:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Нет такого автора")

            return author_by_name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить автора по имении {str(e)}")


@author_router.get("/get_all_videos_by_author", response_model=List[Author], status_code=status.HTTP_200_OK)
async def get_all_videos_by_author(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), author_id: int = Query(...)):
    try:
        async with uow:
            author_videos = await uow.authors.get_all_videos_by_author(author_id=author_id)

            if not author_videos:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Автор не найден")

            return author_videos

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить все видео пользователя {str(e)}")

@author_router.get("/get_last_author", response_model=AuthorPublic, status_code=status.HTTP_200_OK)
async def get_last_author(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            last_author = await uow.authors.get_last_author()

            if not last_author:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Автор не найден")

            return last_author

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить последнее видео автора {str(e)}")

@author_router.get("/get_last_video", status_code=status.HTTP_200_OK)
async def get_last_video(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), channel_name: str = Query(...)):
    try:
        async with uow:
            last_video = await get_last_video_by_channel_name(channel_name=channel_name)

            if not last_video:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Видео не найдено")

        return last_video

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить последнее видео {str(e)}")

@author_router.get("/get_authors_with_count_followers", status_code=status.HTTP_200_OK)
async def get_authors_with_count_followers(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            authors_with_count_followers = await uow.authors.get_authors_with_count_followers()

            if not authors_with_count_followers:
                raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Авторы не найдены")

        return authors_with_count_followers

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить авторов с количеством подписчиков {str(e)}")


@author_router.get("/count_all_followers_by_author", response_model=int, status_code=status.HTTP_200_OK)
async def get_count_all_followers_by_author(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), author_id: int = Query(...)):
    try:
        async with uow:
            count_all_followers_by_author = await uow.authors.count_all_followers(author_id=author_id)

        return count_all_followers_by_author

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось посчитать количество подписчиков автора {str(e)}")


@author_router.get("/get_all_authors_with_more_10_videos", status_code=status.HTTP_200_OK)
async def get_all_authors_with_more_10_videos(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            authors_with_more_10_videos = await uow.authors.get_all_authors_with_more_10_videos()

        return authors_with_more_10_videos

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить всех авторов, количество видео которых больше 10 {str(e)}")

@author_router.get("/get_authors_with_unwatched_videos", response_model=List[AuthorPublic], status_code=status.HTTP_200_OK)
async def get_authors_with_unwatched_videos(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            authors_with_unwatched_videos = await uow.authors.get_authors_with_unwatched_videos()

        return authors_with_unwatched_videos

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить авторов с непросмотренными видео {str(e)}")

@author_router.get("/get_authors_with_followers", response_model=List[AuthorWithFollowers], status_code=status.HTTP_200_OK)
async def get_authors_with_followers(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work)):
    try:
        async with uow:
            authors_with_followers = await uow.authors.get_authors_with_followers()

        return authors_with_followers

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить авторов у которых есть подписчики {str(e)}")

@author_router.get("/get_all_followers", response_model=AuthorWithSubscriptions, status_code=status.HTTP_200_OK)
async def get_all_followers(token = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_unit_of_work), author_id: int = Query(...)):
    try:
        async with uow:
            author_with_followers = await uow.authors.get_all_followers(author_id=author_id)

        if not author_with_followers:
            raise HTTPException(status_code=404, detail="Автор с данным ID не найден")

        return author_with_followers

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить авторов вместе с подписчиками {str(e)}")