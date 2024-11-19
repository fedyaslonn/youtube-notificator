import asyncio
import os
import json
from typing import List, Callable

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging

from requests import session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.subscriptions.models import Subscription, SubscriptionPublic
from src.infra.database.repository import SubscriptionRepository
from src.infra.database.uow import UnitOfWork, get_unit_of_work
from src.logic.commands.youtube_logic import get_last_video_by_channel_name, get_last_videos_by_subscription

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class VideoNotificationProducer:
    def __init__(self):
        kafka_uri = os.getenv("KAFKA_URI")
        self.producer = AIOKafkaProducer(bootstrap_servers=kafka_uri)

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def __aenter__(self):
        try:
            logger.info("Старт продьюсера VideoNotificationProducer")
            await self.start()
            return self

        except Exception as e:
            logger.exception(f"Ошибка при попытке запуска продьюсера VideoNotificationProducer", exc_info=e)
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.stop()

        except Exception as e:
            raise

    async def check_and_notify_for_new_videos(self):
        try:
            async with await get_unit_of_work() as uow:
                subscriptions = await uow.subscriptions.get_notifications()

                tasks = [self._process_subscription(subscription) for subscription in subscriptions]

                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Ошибка при проверке новых видео: {str(e)}", exc_info=e)

    async def produce_notification(self, sub_id: int, user_id: str, author_name: str, video_data: dict):
        from src.logic.commands.videos_logic import VideoNotificationService
        service = VideoNotificationService()
        try:
            notification_message = {
                "user_tag": user_id,
                "author_name": author_name,
                "video_url": video_data.get("url"),
                "video_title": video_data.get("title"),
                "published_at": video_data.get("published_at").isoformat() if isinstance(video_data.get("published_at"), datetime) else video_data.get("published_at"),
                "duration": str(video_data.get("duration")),
                "user_id": video_data.get("user_id"),
                "author_id": video_data.get("author_id"),
                "notified_at": datetime.utcnow().isoformat()
            }

            serialized_data = json.dumps(notification_message).encode("utf-8")
            await self.producer.send(
                topic=os.getenv("KAFKA_VIDEO_NOTIFICATION_TOPIC"),
                value=serialized_data,
                key=(user_id + author_name).encode("utf-8")
            )

            logger.info(f"Отправка сообщения с датой: {serialized_data}")


            logger.info(f"Сообщение отправлено для пользователя {user_id}, обновление подписки {sub_id}")

            await service.update_last_notified(sub_id=sub_id)
            logger.info(f"Подписка {sub_id} обновлена после отправки уведомления")

        except KafkaError as kafka_error:
            logger.error(f"Kafka ошибка: {kafka_error}")
        except Exception as e:
            logger.exception(f"Ошибка при отправке уведомления", exc_info=e)


    async def _process_subscription(self, subscription):
        try:
            logger.info(f"Получение подписки {subscription.id}")

            new_videos = await get_last_videos_by_subscription(
                subscription.author.author,
                subscription.last_notified_at
            )

            logger.info(f"Получение списка видео {new_videos}")

            tasks = []

            for video in new_videos:
                video_data = {
                    "url": video['url'],
                    "title": video['title'],
                    "published_at": video['published_at'],
                    "duration": video['duration'],
                    "user_id": subscription.user.id,
                    "author_id": subscription.author.id
                }

                tasks.append(self.produce_notification(
                    sub_id=subscription.id,
                    user_id=subscription.user.user_tag,
                    author_name=subscription.author.author,
                    video_data=video_data
                ))

            await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Ошибка при обработке подписки {subscription.id}: {str(e)}")
