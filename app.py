from fastapi import FastAPI

from src.infra.application import factory
from bot_service.presentation.bot.webhook_routers import router as bot_router

