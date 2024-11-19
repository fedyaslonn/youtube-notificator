import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../bot_service/')))

from presentation.bot.webhook_routers import get_ngrok_url

from src.infra.database.repository import UserRepository
from src.domain.users.models import UserCreateRequestBody

import aiohttp


async def create_user_from_message(username: str, user_tag: str):
    ngrok_url = await get_ngrok_url()
    url = f"{ngrok_url}/users/create_user"
    user_data = UserCreateRequestBody(username=username, user_tag=user_tag)
    print(f"Отправка данных: {user_data.dict()} на {url}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=user_data.dict()) as response:
                print(f"Ответ от сервера: статус {response.status}, текст {await response.text()}")
                if response.status == 201:
                    return await response.json()
                else:
                    print(f"Не получилось создать пользователя.")
                    return None

        except aiohttp.ClientError as e:
            print(f"Ошибка {str(e)}")
            return None
