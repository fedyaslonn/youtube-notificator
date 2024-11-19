FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml ./pyproject.toml
COPY poetry.lock ./poetry.lock
COPY .env ./.env


RUN pip install poetry && \
    poetry export -f requirements.txt --output requirements.txt && \
    pip install -r requirements.txt

COPY . /app/src

ENV PYTHONPATH=/app/src

WORKDIR /app/src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

