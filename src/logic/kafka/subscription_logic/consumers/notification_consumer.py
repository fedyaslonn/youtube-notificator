import os
import json
from aiokafka import AIOKafkaConsumer

from bot_service.presentation.bot.bot_routers import notify_user_about_subscription
from src.domain.authors.models import AuthorCreateRequestBody


import logging

from src.logic.commands.youtube_logic import get_last_video_by_channel_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger((__name__))


class NotificationConsumer:
    def __init__(self):
        self.consumer = AIOKafkaConsumer(
            os.getenv("KAFKA_NOTIFICATION_TOPIC"),
            bootstrap_servers=os.getenv("KAFKA_URI"),
            group_id=os.getenv("KAFKA_NOTIFICATION_GROUP"),
            enable_auto_commit=True,
            auto_offset_reset="earliest"
        )

    async def start(self):
        await self.consumer.start()

    async def stop(self):
        await self.consumer.stop()

    async def consume_notifications(self):
        logger.info(f"Начало чтения уведомлений из кафки")
        try:
            async for msg in self.consumer:
                notification_data = json.loads(msg.value.decode("utf-8"))
                user_id = notification_data.get("user_id")
                logger.info(f"Уведомление успешно получено из продьюсера {notification_data}")

                if user_id is None:
                    logger.exception(f"Получено сообщение без user_id, пропуск обработки")
                    continue

                author_data = AuthorCreateRequestBody(**notification_data)
                await notify_user_about_subscription(user_id=user_id, author_name=author_data.author, author_url=author_data.author_url)

                logger.info(f"Уведомление успешно доставлено {author_data}")

        except Exception as e:
            logger.exception('Ошибка в консьюмере уведомления', exc_info=e)
            raise RuntimeError(f"Ошибка при чтении уведомления {str(e)}")

        finally:
            await self.stop()
