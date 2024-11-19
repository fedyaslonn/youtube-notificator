import os
import json
from aiokafka import AIOKafkaConsumer

class AuthorSubscription:
    def __init__(self):
        self.consumer = AIOKafkaConsumer(
            os.getenv("KAFKA_AUTHOR_SUBSCRIPTION_TOPIC"),
            bootstrap_servers=os.getenv("KAFKA_URI"),
            group_id=os.getenv("KAFKA_SUBSCRIPTION_GROUP"),
            enable_auto_commit=True,
            auto_offset_reset="earliest"
        )

    async def start(self):
        await self.consumer.start()

    async def stop(self):
        await self.consumer.stop()

    async def consume_author_subscription(self):
        try:
            async for msg in self.consumer:
                subscription_data = json.loads(msg.value.decode("utf-8"))
                user_id = subscription_data.get("user_id")
                author_name = subscription_data.get("author_name")

        except Exception as e:
            raise RuntimeError(f"Ошибка при чтении подписки {str(e)}")

        finally:
            await self.stop()