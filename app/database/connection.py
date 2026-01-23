import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "invoice_db")

# MongoDB Client
client: AsyncIOMotorClient = None
db = None
_client_loop = None


async def connect_to_mongo():
    """Connect to MongoDB with loop-awareness to avoid 'Event loop is closed' errors."""
    global client, db
    global _client_loop
    import asyncio
    
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        return # Not in an event loop

    # Motor clients bind to the event loop active at creation. Recreate only when
    # the running loop changes (e.g., Celery using asyncio.run creates a fresh loop).
    recreate = (client is None) or (_client_loop is not current_loop)

    if recreate:
        if client:
            try:
                client.close()
            except:
                pass
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        _client_loop = current_loop
    
    # Create indexes only once if they don't exist
    # Use a global flag to skip index creation after the very first successful run
    if not hasattr(connect_to_mongo, "_indexes_created"):
        try:
            await db.users.create_index("email", unique=True)
            await db.users.create_index("username", unique=True)
            await db.users.create_index("api_key", sparse=True)
            await db.invoices.create_index([("user_id", 1), ("created_at", -1)])
            await db.invoices.create_index("task_id", unique=True, sparse=True)
            await db.invoices.create_index("status")
            await db.webhooks.create_index("user_id")
            await db.batch_jobs.create_index("user_id")
            connect_to_mongo._indexes_created = True
            print("Connected to MongoDB and verified indexes.")
        except Exception as e:
            print(f"Index creation warning: {e}")


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")


def get_database():
    """Get database instance."""
    return db


# Collections
def get_users_collection():
    return db.users


def get_invoices_collection():
    return db.invoices


def get_invoice_items_collection():
    return db.invoice_items


def get_webhooks_collection():
    return db.webhooks


def get_batch_jobs_collection():
    return db.batch_jobs


def get_metrics_collection():
    return db.processing_metrics
