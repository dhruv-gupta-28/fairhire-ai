"""
Authentication and authorization for FairHire AI
"""

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from flask import jsonify
from database import User
from config import JWT_SECRET_KEY
import logging
from functools import wraps
from datetime import timedelta

logger = logging.getLogger(__name__)

jwt = JWTManager()


def init_jwt(app):
    app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = False
    app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    jwt.init_app(app)


def login_user(email: str, password: str):
    user = User.verify_password(email, password)

    if not user:
        return None

    access_token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={
            "email": user["email"],
            "role": user["role"]
        }
    )

    return {
        "access_token": access_token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"]
        }
    }


def register_user(email: str, password: str, role: str = "user"):
    user = User.create(email, password, role)

    if not user:
        return None

    access_token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={
            "email": user["email"],
            "role": user["role"]
        }
    )

    return {
        "access_token": access_token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"]
        }
    }


def _check_role(required_roles):
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.find_by_id(user_id)

            if not user:
                return jsonify({"error": "User not found"}), 401

            if user.get("role") not in required_roles:
                return jsonify({"error": "Access denied"}), 403

            return f(*args, **kwargs)

        return wrapper
    return decorator


def admin_required(f):
    return _check_role(["admin"])(f)


def recruiter_required(f):
    return _check_role(["admin", "recruiter"])(f)


def user_required(f):
    return _check_role(["admin", "recruiter", "user"])(f)