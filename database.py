"""
Database models and connections for FairHire AI
"""

from pymongo import MongoClient
from pymongo.database import Database
from config import MONGO_URI, DB_NAME
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import os
import bcrypt
from bson import ObjectId
import time

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self._connected = False

    def connect(self):
        if self._connected:
            return
        try:
            self.client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=50
            )
            self.db = self.client[DB_NAME]
            self.client.admin.command('ping')
            self._connected = True
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            self._connected = False

    def ensure_connection(self):
        if not self._connected:
            self.connect()
        if not self._connected:
            raise RuntimeError("Database connection not available")

    def close(self):
        if self.client and self._connected:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")


db_manager = DatabaseManager()


def get_users_collection():
    db_manager.ensure_connection()
    return db_manager.db.users


def get_analyses_collection():
    db_manager.ensure_connection()
    return db_manager.db.analyses

def get_history_collection():
    db_manager.ensure_connection()
    return db_manager.db.history


def get_reports_collection():
    db_manager.ensure_connection()
    return db_manager.db.reports


def get_rate_limit_collection():
    db_manager.ensure_connection()
    return db_manager.db.rate_limits


def get_models_collection():
    db_manager.ensure_connection()
    return db_manager.db.models


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    if "user_id" in doc:
        doc["user_id"] = str(doc["user_id"])
    return doc


class RateLimit:
    @staticmethod
    def check(identifier: str, path: str, limit: int = 10, window: int = 60) -> bool:
        db_manager.ensure_connection()
        coll = get_rate_limit_collection()
        now = time.time()
        cutoff = now - window
        
        coll.delete_many({"identifier": identifier, "path": path, "timestamp": {"$lt": cutoff}})
        
        count = coll.count_documents({"identifier": identifier, "path": path})
        if count >= limit:
            return False
            
        coll.insert_one({"identifier": identifier, "path": path, "timestamp": now})
        return True


class User:
    @staticmethod
    def create(email: str, password: str, role: str = "user") -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()

        if get_users_collection().find_one({"email": email}):
            return None

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        user = {
            "email": email,
            "password": hashed.decode("utf-8"),
            "role": role,
            "created_at": datetime.utcnow(),
            "last_login": None
        }

        result = get_users_collection().insert_one(user)
        user["_id"] = result.inserted_id

        return _serialize(user)

    @staticmethod
    def find_by_email(email: str) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()
        user = get_users_collection().find_one({"email": email})
        return _serialize(user) if user else None

    @staticmethod
    def verify_password(email: str, password: str) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()

        raw_user = get_users_collection().find_one({"email": email})
        if not raw_user:
            return None

        if bcrypt.checkpw(password.encode("utf-8"), raw_user["password"].encode("utf-8")):
            get_users_collection().update_one(
                {"_id": raw_user["_id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return _serialize(raw_user)

        return None

    @staticmethod
    def find_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()
        try:
            user = get_users_collection().find_one({"_id": ObjectId(user_id)})
            return _serialize(user) if user else None
        except Exception:
            return None

    @staticmethod
    def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()
        try:
            user = get_users_collection().find_one({"_id": ObjectId(user_id)})
            if not user:
                return None
            serialized = _serialize(user)
            serialized.pop("password", None)
            return serialized
        except Exception:
            return None

    @staticmethod
    def update_profile(user_id: str, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()
        allowed_fields = ["name", "age", "gender", "phone", "location", "bio", "skills", "linkedin", "github"]
        update_data = {k: v for k, v in profile_data.items() if k in allowed_fields}
        update_data["updated_at"] = datetime.utcnow()

        try:
            get_users_collection().update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            return User.get_profile(user_id)
        except Exception:
            return None

    @staticmethod
    def update_resume_data(user_id: str, resume_data: Dict[str, Any]) -> bool:
        db_manager.ensure_connection()
        try:
            result = get_users_collection().update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"resume_data": resume_data}}
            )
            return result.modified_count > 0 or result.matched_count > 0
        except Exception as e:
            logger.error(f"Failed to update user resume data: {e}")
            return False

    @staticmethod
    def delete(user_id: str) -> bool:
        db_manager.ensure_connection()
        try:
            result = get_users_collection().delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return False

class Analysis:
    @staticmethod
    def create(user_id: str, dataset_info: Dict, fairness_score: float, results: Dict) -> Dict[str, Any]:
        db_manager.ensure_connection()

        analysis = {
            "user_id": ObjectId(user_id),
            "dataset_info": dataset_info,
            "fairness_score": fairness_score,
            "results": results,
            "created_at": datetime.utcnow()
        }

        result = get_analyses_collection().insert_one(analysis)
        analysis["_id"] = result.inserted_id

        return _serialize(analysis)

    @staticmethod
    def find_by_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        db_manager.ensure_connection()

        docs = get_analyses_collection().find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).limit(limit)

        return [_serialize(doc) for doc in docs]

    @staticmethod
    def find_by_id(analysis_id: str) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()
        try:
            doc = get_analyses_collection().find_one({"_id": ObjectId(analysis_id)})
            return _serialize(doc) if doc else None
        except Exception:
            return None


class Report:
    @staticmethod
    def create(user_id: str, file_path: str) -> Dict[str, Any]:
        db_manager.ensure_connection()

        report = {
            "user_id": ObjectId(user_id),
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "created_at": datetime.utcnow()
        }

        result = get_reports_collection().insert_one(report)
        report["_id"] = result.inserted_id

        return _serialize(report)

    @staticmethod
    def find_by_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        db_manager.ensure_connection()

        docs = get_reports_collection().find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).limit(limit)

        return [_serialize(doc) for doc in docs]

    @staticmethod
    def find_by_id(report_id: str) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()
        try:
            doc = get_reports_collection().find_one({"_id": ObjectId(report_id)})
            return _serialize(doc) if doc else None
        except Exception:
            return None


class Model:
    @staticmethod
    def save_model(user_id: str, model_path: str, version: str, metadata: Dict) -> Dict[str, Any]:
        db_manager.ensure_connection()

        model_doc = {
            "user_id": ObjectId(user_id),
            "model_path": model_path,
            "version": version,
            "metadata": metadata,
            "created_at": datetime.utcnow()
        }

        result = get_models_collection().insert_one(model_doc)
        model_doc["_id"] = result.inserted_id

        return _serialize(model_doc)

    @staticmethod
    def get_latest_model(user_id: str) -> Optional[Dict[str, Any]]:
        db_manager.ensure_connection()

        doc = get_models_collection().find_one(
            {"user_id": ObjectId(user_id)},
            sort=[("created_at", -1)]
        )

        return _serialize(doc) if doc else None

class History:
    @staticmethod
    def create(user_id: str, op_type: str, input_meta: Dict[str, Any], output_results: Dict[str, Any]) -> Dict[str, Any]:
        db_manager.ensure_connection()
        record = {
            "user_id": ObjectId(user_id),
            "type": op_type,
            "input_metadata": input_meta,
            "output_results": output_results,
            "created_at": datetime.utcnow()
        }
        result = get_history_collection().insert_one(record)
        record["_id"] = result.inserted_id
        return _serialize(record)

    @staticmethod
    def find_by_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        db_manager.ensure_connection()
        docs = get_history_collection().find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).limit(limit)
        return [_serialize(doc) for doc in docs]