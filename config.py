import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "7477560586:AAHhOszWlArl4x2ea6JCb7CXYmR6C0Wi2CM")

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Multiverse_user:Multiverse123@multiverse.pgqfvsu.mongodb.net/?appName=Multiverse")
DB_NAME = "multiverse_bot"

# Upstash Redis (REST API)
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "https://enormous-opossum-102046.upstash.io")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "gQAAAAAAAY6eAAIocDEyZDY3ZjUzYjE1ZGQ0YzIzYmM4ZjgwYmMzZGY5MzI0YXAxMTAyMDQ2")

# Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dlvzhfun5")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "332349478262569")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "ddQq7ctXdAXxD02rVSWXIy-pZ6o")

# Webhook / Server
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # Set to Render URL in production
PORT = int(os.getenv("PORT", 8443))

# Game constants
MAX_STAMINA = 100
STAMINA_REGEN_AMOUNT = 5
STAMINA_REGEN_SECONDS = 1800  # 30 minutes
GACHA_SINGLE_COST = 100
GACHA_TEN_COST = 900
PITY_THRESHOLD = 50
FREE_MISSIONS_PER_DAY = 3
OFFLINE_XP_RATE = 1  # XP per hour
