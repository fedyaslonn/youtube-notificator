import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
NGROK_TOKEN_URL = os.environ.get("NGROK_TOKEN_URL")
