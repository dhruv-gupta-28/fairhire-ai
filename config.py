"""
Configuration for FairHire AI
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.resolve()

# -----------------------------
# CORE PATHS
# -----------------------------
DEFAULT_DATASET_PATH = BASE_DIR / "data.csv"
UPLOAD_FOLDER = BASE_DIR / "uploads"
MODEL_FOLDER = BASE_DIR / "models"
REPORT_FOLDER = BASE_DIR / "reports"

# Ensure directories exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
REPORT_FOLDER.mkdir(parents=True, exist_ok=True)

# -----------------------------
# LOGGING
# -----------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "fairhire.log"

# -----------------------------
# GEMINI CONFIG
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -----------------------------
# FLASK CONFIG
# -----------------------------
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("CRITICAL ERROR: SECRET_KEY environment variable is missing!")

# -----------------------------
# DATABASE CONFIG
# -----------------------------
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("CRITICAL ERROR: MONGO_URI environment variable is missing!")

DB_NAME = os.getenv("DB_NAME", "fairhire")

# -----------------------------
# JWT CONFIG
# -----------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)

# -----------------------------
# ML CONFIG
# -----------------------------
MODEL_CACHE_MAX_SIZE = int(os.getenv("MODEL_CACHE_MAX_SIZE", 10))
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

# -----------------------------
# FILE UPLOAD CONFIG
# -----------------------------
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 5 * 1024 * 1024))  # 5MB default

# -----------------------------
# VALIDATION CHECKS
# -----------------------------
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY environment variable is missing!")

if len(JWT_SECRET_KEY) < 32:
    print("⚠️ WARNING: JWT_SECRET_KEY should be at least 32 characters long for security.")