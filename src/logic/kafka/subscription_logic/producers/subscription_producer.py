from aiokafka import AIOKafkaProducer

import os

from src.domain.authors.models import Author, AuthorCreateRequestBody
from src.infra.database import uow
from src.infra.database.uow import UnitOfWork, get_unit_of_work
from src.settings.config import KafkaSettings

import json

import logging

logger = logging.getLogger((__name__))

class AuthorSubscriptionProducer:
    def __init__(self):
        kafka_uri = os.getenv("KAFKA_URI")
        self.producer = AIOKafkaProducer(bootstrap_servers=kafka_uri)

    async def __aenter__(self):
        try:
            await self.start()
            print("Producer entered successfully")
            return self
        except Exception as e:
            logger.exception("Проверка входа", exc_info=e)
            raise
    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def produce_author_subscription(self, user_id: str, uow: UnitOfWork):
        try:
            async with uow:
                sub_message = await uow.authors.get_last_author()
            new_author = AuthorCreateRequestBody(author=sub_message.author, author_url=sub_message.author_url)

            serialized_message = new_author.json().encode("utf-8")

            await self.producer.send_and_wait(
            topic=os.getenv("KAFKA_AUTHOR_SUBSCRIPTION_TOPIC"),
            value=serialized_message,
            key=user_id.encode('utf-8')
            )

        except Exception as e:
            logger.exception('Exception in produce_author...', exc_info=e)
            raise RuntimeError(f"Не получилось отправить сообщение о подписке {str(e)}")
