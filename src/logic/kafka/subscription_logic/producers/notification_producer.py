import os

from aiokafka import AIOKafkaProducer

import json

import logging

from src.domain.authors.models import AuthorCreateRequestBody
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

class NotificationProducer:
    def __init__(self):
        kafka_uri = os.getenv("KAFKA_URI")
        self.producer = AIOKafkaProducer(bootstrap_servers=kafka_uri)

    async def __aenter__(self):
        try:
            await self.start()
            print("Producer entered successfully")
            return self
        except Exception as e:
            logger.exception('Ошибка в продьюсере уведомления...', exc_info=e)
            raise

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()


    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def produce_notification(self, user_id: str, uow: UnitOfWork):
        try:
            async with uow:
                sub_message = await uow.authors.get_last_author()

            notification_data = {
                "user_id": user_id,
                "author": sub_message.author,
                "author_url": sub_message.author_url
            }

            serialized_notification = json.dumps(notification_data).encode("utf-8")

            await self.producer.send_and_wait(
                topic=os.getenv("KAFKA_NOTIFICATION_TOPIC"),
                value=serialized_notification,
                key=user_id.encode("utf-8")
            )
            print("Уведомление отправлено успешно")

        except Exception as e:
            logger.exception('Exception in produce_author...', exc_info=e)
            raise RuntimeError(f"Не удалось отправить сообщение об уведомлении {str(e)}")