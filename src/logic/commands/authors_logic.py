import aiohttp

from src.settings.config import TELEGRAM_API_URL

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_subscription_message(user_id: int, message: str):
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