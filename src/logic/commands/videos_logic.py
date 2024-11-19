import asyncio
from datetime import datetime
from typing import Optional

import aiohttp
from dependency_injector.providers import Callable
from fastapi.params import Depends
from sqlalchemy.util import await_only

from src.infra.database.repository import SubscriptionRepository, VideoRepository
from src.infra.database.uow import UnitOfWork, get_unit_of_work
from src.logic.commands.youtube_logic import get_last_videos_by_subscription
from src.logic.kafka.video_notification_logic.producers.video_notification_producer import VideoNotificationProducer
from src.settings.config import TELEGRAM_API_URL

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_video_notification_message(user_id: int, message: str):
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "chat_id": user_id,
                "text": message
            }
            async with session.post(TELEGRAM_API_URL, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Сообщение {message} успешно доставлено пользователю {user_id}")

                else:
                    logger.info(f"Ошибка при доставке сообщения {response.status} - {await response.text()}")

        except Exception as e:
            logger.exception(f"Ошибка при отправке сообщения пользователю", exc_info=e)

class VideoNotificationService:
    async def create_new_video(self, video_data: dict, uow: Optional[UnitOfWork] = None):
        url = video_data.get("url")
        title = video_data.get("title")
        duration = video_data.get("duration")
        published_at = video_data.get("published_at")
        author_id = video_data.get("author_id")
        user_id = video_data.get("user_id")

        if uow is None:
            async with await get_unit_of_work() as uow:
                check_if_video_exists = await uow.videos.get_by_url(url=url)
                if not check_if_video_exists:
                    new_video = await uow.videos.create_video(
                        url=url,
                        title=title,
                        duration=duration,
                        published_at=published_at,
                        author_id=author_id,
                        user_id=user_id
                    )
                    return new_video
                else:
                    raise ValueError(f"Это видео уже существует!")

    async def update_last_notified(self, sub_id: int, uow: Optional[UnitOfWork] = None):
        try:
            if uow is None:
                async with await get_unit_of_work() as uow:
                    subscription = await uow.subscriptions.get_by_id(sub_id)
                    logger.info(f"Обновление подписки {subscription.id}")
                    if subscription:
                        subscription.last_notified_at = datetime.utcnow()
                        await uow.commit()

        except Exception as e:
            logger.exception(f"Ошибка при попытке получить подписки по id", exc_info=e)

class VideoNotificationScheduler:
    from src.logic.kafka.video_notification_logic.producers.video_notification_producer import VideoNotificationProducer
    def __init__(self, interval_minutes: int = 10):
        self.producer = None
        self.interval_minutes = interval_minutes
        self.running = False

    async def start_schedule(self):
        self.running = True
        async with VideoNotificationProducer() as producer:
            self.producer = producer
            while self.running:
                await self.producer.check_and_notify_for_new_videos()
                await asyncio.sleep(self.interval_minutes * 60)

    async def stop(self):
        self.running = False


