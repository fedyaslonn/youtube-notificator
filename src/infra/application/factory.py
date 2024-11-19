import asyncio
from contextlib import asynccontextmanager
from sched import scheduler

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database.uow import UnitOfWork, UnitOfWorkBase, get_unit_of_work
from src.logic.commands.videos_logic import VideoNotificationScheduler, VideoNotificationService
from src.logic.kafka.subscription_logic.consumers.notification_consumer import NotificationConsumer
from src.logic.kafka.subscription_logic.consumers.subscription_consumer import AuthorSubscription
from src.logic.kafka.video_notification_logic.consumers.video_notification_consumer import VideoNotificationConsumer
from src.logic.kafka.video_notification_logic.producers.video_notification_producer import VideoNotificationProducer

from src.settings.config import kafka_settings

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

notification_service = VideoNotificationService()
notification_consumer = NotificationConsumer()
subscription_consumer = AuthorSubscription()
video_notification_consumer = VideoNotificationConsumer()
video_notification_producer = VideoNotificationProducer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск метода lifespan...")
    try:

        video_notification_scheduler = VideoNotificationScheduler(interval_minutes=10)

        logger.info("Запуск консьюмеров...")
        await notification_consumer.start()
        await subscription_consumer.start()
        await video_notification_consumer.start()

        notification_task = asyncio.create_task(notification_consumer.consume_notifications())
        consumer_task = asyncio.create_task(subscription_consumer.consume_author_subscription())
        video_notification_task = asyncio.create_task(video_notification_consumer.consume_notification())

        video_notification_schedule_task = asyncio.create_task(
            video_notification_scheduler.start_schedule()
        )

        logger.info("Консьюмеры успешно запущены")

        yield
        logger.info("После yield в lifespan...")

    except Exception as e:
        logger.exception("Ошибка при запуске консьюмеров", exc_info=e)

    finally:
        logger.info("Завершение работы консьюмеров...")

        notification_task.cancel()
        consumer_task.cancel()
        video_notification_task.cancel()
        video_notification_schedule_task.cancel()

    try:
        await asyncio.gather(notification_task, consumer_task, video_notification_task,
                             video_notification_schedule_task)
    except asyncio.CancelledError:
        logger.info("Задачи консьюмеров отменены")
    finally:
        logger.info("Консьюмеры завершили выполнение")