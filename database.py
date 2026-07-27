from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    # Ping to verify connection
    await client.admin.command("ping")
    print(f"[TrackBucks] Connected to MongoDB: {settings.MONGO_DB}")

    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.watchlists.create_index("user_id", unique=True)
    await db.price_history.create_index([("asset_id", 1), ("recorded_at", -1)])
    await db.alert_log.create_index([("asset_id", 1), ("sent_at", -1)])


async def close_db():
    global client
    if client:
        client.close()
        print("[TrackBucks] MongoDB connection closed.")


def get_db():
    return db
