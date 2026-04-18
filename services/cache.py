import logging
from collections import OrderedDict
from typing import Any, Dict, Optional

from config import MODEL_CACHE_MAX_SIZE, MONGO_URI, DB_NAME

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModelCache:
    def __init__(self, max_size: int = MODEL_CACHE_MAX_SIZE, enable_persistence: bool = False):
        self.max_size = max_size
        self.store: Dict[str, Any] = OrderedDict()
        self.enable_persistence = enable_persistence and MONGO_AVAILABLE and bool(MONGO_URI)
        self.mongo_client = None
        self.collection = None

        if self.enable_persistence:
            try:
                self.mongo_client = MongoClient(MONGO_URI)
                self.collection = self.mongo_client[DB_NAME].get_collection("model_cache")
            except Exception as exc:
                logger.warning(f"Failed to initialize persistent cache: {exc}")
                self.enable_persistence = False

    def get(self, key: str) -> Optional[Any]:
        if key in self.store:
            value = self.store.pop(key)
            self.store[key] = value
            return value

        if self.enable_persistence and self.collection:
            doc = self.collection.find_one({"key": key})
            if doc:
                try:
                    self.set(key, doc["value"])
                    return doc["value"]
                except Exception:
                    return doc["value"]

        return None

    def set(self, key: str, value: Any) -> None:
        if key in self.store:
            self.store.pop(key)
        self.store[key] = value
        while len(self.store) > self.max_size:
            self.store.popitem(last=False)

        if self.enable_persistence and self.collection:
            try:
                self.collection.update_one(
                    {"key": key},
                    {"$set": {"value": value}},
                    upsert=True
                )
            except Exception as exc:
                logger.warning(f"Failed to persist cache entry: {exc}")

    def clear(self) -> None:
        self.store.clear()
        if self.enable_persistence and self.collection:
            try:
                self.collection.delete_many({})
            except Exception as exc:
                logger.warning(f"Failed to clear persistent cache: {exc}")
