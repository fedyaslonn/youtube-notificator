from pydantic import BaseModel
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

class DBSettings(BaseSettings):
    host: str = DB_HOST
    port: str = DB_PORT
    name: str = DB_NAME
    user: str = DB_USER
    password: str = DB_PASS

class Settings(BaseSettings):
    db: DBSettings = DBSettings()

settings = Settings()

KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC")

class KafkaSettings(BaseSettings):
    topic: str = KAFKA_TOPIC

kafka_settings = KafkaSettings()

NGROK_TUNNEL_URL = os.environ.get("NGROK_TUNNEL_URL")

class NgrokSettings(BaseSettings):
    token_url: str = NGROK_TUNNEL_URL

ngrok_settings = NgrokSettings()

jwt_algorithm = os.environ.get("ALGORITHM")
access_token_expire_minutes = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))
refresh_token_expire_days = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS"))

secret_key = os.environ.get("SECRET_KEY")
refresh_secret_key = os.environ.get("REFRESH_SECRET_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}/sendMessage"