from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import certifi

client: AsyncIOMotorClient = None
db = None

FALLBACK_URI = "mongodb://localhost:27017"


async def connect_db():
    global client, db

    # Try primary URI (Atlas or whatever is configured)
    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=10000,
        )
        db = client[settings.MONGO_DB]
        await client.admin.command("ping")
        print(f"[Portfolytics] Connected to MongoDB (primary): {settings.MONGO_DB}")
    except Exception as primary_err:
        print(f"[Portfolytics] Primary MongoDB connection failed: {primary_err}")

        # Fall back to local MongoDB
        if FALLBACK_URI not in settings.MONGODB_URI:
            print(f"[Portfolytics] Trying local MongoDB fallback...")
            try:
                client = AsyncIOMotorClient(FALLBACK_URI, serverSelectionTimeoutMS=5000)
                db = client[settings.MONGO_DB]
                await client.admin.command("ping")
                print(f"[Portfolytics] Connected to LOCAL MongoDB fallback: {settings.MONGO_DB}")
            except Exception as fallback_err:
                print(f"[Portfolytics] Local MongoDB also unavailable: {fallback_err}")
                raise RuntimeError(
                    "Could not connect to any MongoDB instance. "
                    "Check your network/Atlas settings or start local MongoDB."
                ) from fallback_err
        else:
            raise

    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.watchlists.create_index("user_id", unique=True)
    await db.price_history.create_index([("asset_id", 1), ("recorded_at", -1)])
    await db.alert_log.create_index([("asset_id", 1), ("sent_at", -1)])


async def close_db():
    global client
    if client:
        client.close()
        print("[Portfolytics] MongoDB connection closed.")


def get_db():
    return db

