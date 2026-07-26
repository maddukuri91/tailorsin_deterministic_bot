import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    wati_base_url = os.getenv("WATI_BASE_URL", "")
    wati_api_key = os.getenv("WATI_API_KEY", "")
    wati_webhook_secret = os.getenv("WATI_WEBHOOK_SECRET", "")
    redis_url = os.getenv("REDIS_URL", "")
    http_timeout = float(os.getenv("HTTP_TIMEOUT", "20"))


settings = Settings()