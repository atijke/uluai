import os
from dotenv import load_dotenv


load_dotenv()


ENVIRONMENT_NAME = os.getenv('ENVIRONMENT_NAME')
TELETHON_LOG_LEVEL = os.getenv('TELETHON_LOG_LEVEL', 'INFO')
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
NGROK_DOMAIN = os.getenv('NGROK_DOMAIN', None)
NGROK_AUTHTOKEN = os.getenv('NGROK_AUTHTOKEN', None)
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
