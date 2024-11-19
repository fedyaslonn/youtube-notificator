from datetime import datetime
import os
from typing import Optional

from aiokafka import AIOKafkaConsumer
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot_service.presentation.bot.bot_routers import notify_user_about_new_video
from src.domain.videos.models import VideoCreateRequestBody, Video
from src.infra.database.repository import SubscriptionRepository
from src.infra.database.uow import UnitOfWork
from src.logic.commands.videos_logic import send_video_notification_message, VideoNotificationService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class VideoNotificationConsumer:
    def __init__(self, service: Optional[VideoNotificationService] = None):
        self.consumer = AIOKafkaConsumer(
            os.getenv("KAFKA_VIDEO_NOTIFICATION_TOPIC"),
            bootstrap_servers=os.getenv("KAFKA_URI"),
            group_id=os.getenv("KAFKA_VIDEO_NOTIFICATION_GROUP"),
            enable_auto_commit=True,
            auto_offset_reset="earliest"
        )
        self.service = service or VideoNotificationService()

    async def start(self):
        await self.consumer.start()

    async def stop(self):
        await self.consumer.stop()

    async def consume_notification(self):
        logger.info("Начало отправки уведомления о выходе нового видео")
        try:
            async for msg in self.consumer:
                logger.info("Получено новое сообщение из топика Kafka")
                notification_data = json.loads(msg.value.decode('utf-8'))
                logger.debug(f"Декодированные данные: {notification_data}")

                user_tag = notification_data.get('user_tag')
                logger.info(f"Получено сообщение от видео продьюсера")
                if not user_tag:
                    logger.error("Получено сообщение без user_tag, пропуск обработки")
                    continue

                video_data = {
                    "title": notification_data.get("video_title"),
                    "url": notification_data.get("video_url"),
                    "author_name": notification_data.get("author_name"),
                    "duration": notification_data.get("duration"),
                    "published_at": notification_data.get("published_at"),
                    "notified_at": notification_data.get("notified_at"),
                    "author_id": notification_data.get("author_id"),
                    "user_id": notification_data.get("user_id")
                }

                await self.service.create_new_video(video_data=video_data)
                await notify_user_about_new_video(user_id=user_tag,
                                                  video_title=video_data.get("title"),
                                                  video_url=video_data.get("url"),
                                                  author_name=notification_data.get("author_name"))

        except Exception as e:
            logger.exception("Ошибка в консьюмере уведомлений о выходе видео", exc_info=e)
            raise RuntimeError(f"Ошибка при чтении уведомлений {str(e)}")

        finally:
            await self.stop()
