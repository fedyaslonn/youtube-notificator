import asyncio

import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from charset_normalizer.md import getLogger

from bot_service.config import BOT_TOKEN

import aiohttp

from src.domain.authors.models import Author

import logging

from src.logic.commands.authors_logic import send_subscription_message
from src.logic.commands.videos_logic import send_video_notification_message

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message):
    await message.answer(f"Привет, {message.from_user.username}. "
           f"Добро пожаловать в YT-Notificator."
           f"Пропиши /info для получения списка команд."
           )

@dp.message(Command("info"))
async def info_handler(message: Message):
    await message.answer(f"Этот бот присылает пользователю уведомления о выходе нового ролика от авторов, на которых он подписался."
                         f"Пользователь может добавить автора через веб-клиент."
                         f"Команды:"
                         f"/start - начало работы бота"
                         f"/info - список команд"
                         f"/connect_to_server - подключиться к серверу")


@dp.message(Command("connect_to_server"))
async def get_user_info(message: Message):
    from src.logic.commands.users_logic import create_user_from_message
    user_info = message.from_user
    username = user_info.username if user_info.username else "anon"
    user_tag = str(user_info.id)

    response = await create_user_from_message(username, user_tag)
    print(f"Ответ {response}")

    if response and response["status"] == "success":
        await message.answer(f"Пользователь {username} был успешно создан!")
    else:
        await message.answer(f"Не удалось создать пользователя!")

async def notify_user_about_subscription(user_id: str, author_name: str, author_url: str):
    user_id = int(user_id)
    message = (f"Вы успешно подписались на автора {author_name}, url-автора: {author_url}")
    logger.info(f"Сообщение для отправки: {message}")

    if not message.strip():
        logger.error("Текст сообщения пустой. Прекращение отправки.")
        return

    await send_subscription_message(user_id=user_id, message=message)

async def notify_user_about_new_video(user_id: str, video_title: str, video_url: str, author_name: str):
    user_id = int(user_id)
    message = f"Новое видео: {video_title} - {video_url} у автора {author_name}"

    if not message.strip():
        logger.error("Текст сообщения пустой. Прекращение отпавки.")
        return

    await send_video_notification_message(user_id=user_id, message=message)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())