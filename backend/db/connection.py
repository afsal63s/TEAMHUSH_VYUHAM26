from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from config import get_settings

_client: AsyncMongoClient | None = None


def get_client() -> AsyncMongoClient:
    """One client per process; PyMongo connects lazily on first use."""
    global _client
    if _client is None:
        _client = AsyncMongoClient(get_settings().MONGO_URI)  # tz_aware=False: naive UTC datetimes
    return _client


def get_db() -> AsyncDatabase:
    return get_client()[get_settings().MONGO_DB]


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
