FROM python:3.10-slim

WORKDIR /bot_service

COPY pyproject.toml ./pyproject.toml
COPY poetry.lock ./poetry.lock
COPY .env ./.env

RUN pip install poetry && \
    poetry export -f requirements.txt --output requirements.txt && \
    pip install -r requirements.txt



COPY . /bot_service

ENV PYTHONPATH=/bot_service

CMD ["python", "bot_service/presentation/bot/bot_routers.py", "run"]