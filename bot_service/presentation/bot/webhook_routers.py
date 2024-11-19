import aiohttp
from fastapi import FastAPI, APIRouter, Depends
from aiogram import types, Bot, Dispatcher

import os
import sys

from bot_service.presentation.bot.bot_routers import bot, dp
from src.infra.database import uow
from src.infra.database.uow import UnitOfWork, get_unit_of_work
from src.logic.authentication.authentication import get_current_user

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from bot_service.config import BOT_TOKEN, NGROK_TOKEN_URL

import requests

NGROK_API_URL = "http://ngrok:4040/api/tunnels"
router = APIRouter()
WEBHOOK_PATH = f"/bot/{BOT_TOKEN}"
WEBHOOK_URL = f"{NGROK_TOKEN_URL}{WEBHOOK_PATH}"


async def get_ngrok_url():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(NGROK_API_URL) as response:
                data = await response.json()
                if response.status != 200:
                    raise Exception(f"Не удалось получить данные от NGROK API: {response.status}")

                if 'tunnels' not in data or not data['tunnels']:
                    raise Exception(f"Не удалось найти NGROK туннель")

                return data['tunnels'][0]['public_url']

    except Exception as e:
        raise Exception(f"{e}")


@router.on_event("startup")
async def on_startup():
    try:
        ngrok_url = await get_ngrok_url()
        webhook_url = f"{ngrok_url}{WEBHOOK_PATH}"

        await bot.set_webhook(url=webhook_url)

    except Exception as e:
        raise Exception(f"{e}")

@router.post(WEBHOOK_PATH)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    Dispatcher.set_current(dp)
    Bot.set_current(bot)
    await dp._process_update(telegram_update)

@router.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()

