from motor.motor_asyncio import AsyncIOMotorClient
from config.env import MONGO_URI


def get_mongo_db_client():
    if not MONGO_URI:
        return None

    client = AsyncIOMotorClient(
        MONGO_URI,
        connectTimeoutMS=1440000,
        serverSelectionTimeoutMS=1440000
    )
    
    return client.get_default_database()
