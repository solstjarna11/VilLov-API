# app/config.py

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Prefer a shared database URL from the environment (e.g. Render Postgres).
# Fall back to local SQLite for development.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DB_PATH = BASE_DIR / "villov_dev.db"
    DATABASE_URL = f"sqlite:///{DB_PATH}"

API_TITLE = os.getenv("API_TITLE", "VilLov Chat Dev Backend")
API_VERSION = os.getenv("API_VERSION", "0.1.3")

TOKEN_TTL_DAYS = int(os.getenv("TOKEN_TTL_DAYS", "30"))
CHALLENGE_TTL_MINUTES = int(os.getenv("CHALLENGE_TTL_MINUTES", "5"))

ACCESS_TOKEN_EXPIRE_DELTA = timedelta(days=TOKEN_TTL_DAYS)
CHALLENGE_EXPIRE_DELTA = timedelta(minutes=CHALLENGE_TTL_MINUTES)

# Development fallback for passkey auth must be disabled in deployed environments.
ENABLE_DEVELOPMENT_PASSKEY_AUTH = (
    os.getenv("ENABLE_DEVELOPMENT_PASSKEY_AUTH", "true").strip().lower() == "true"
)

# Real passkey / WebAuthn config
WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID", "auth.villovchat.com")
WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "https://auth.villovchat.com")
WEBAUTHN_RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "VilLov Chat")

# App/runtime flags
RUN_DB_CREATE_ALL = os.getenv("RUN_DB_CREATE_ALL", "true").strip().lower() == "true"

# Reverse proxy / host settings
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

# Convenience helper
IS_SQLITE = DATABASE_URL.startswith("sqlite")