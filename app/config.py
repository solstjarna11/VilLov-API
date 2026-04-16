from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "villov_dev.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

API_TITLE = "VilLov Chat Dev Backend"
API_VERSION = "0.1.1"
DEV_RP_ID = "villov.local"
DEFAULT_SIGNIN_USER_ID = "user_alice"
DEFAULT_CHALLENGE = "dev-challenge-123"
TOKEN_TTL_DAYS = 30
CHALLENGE_TTL_MINUTES = 5
ACCESS_TOKEN_EXPIRE_DELTA = timedelta(days=TOKEN_TTL_DAYS)
CHALLENGE_EXPIRE_DELTA = timedelta(minutes=CHALLENGE_TTL_MINUTES)

# Real passkey / WebAuthn config
WEBAUTHN_RP_ID = "auth.villovchat.com"
WEBAUTHN_ORIGIN = "https://auth.villovchat.com"
WEBAUTHN_RP_NAME = "VilLov Chat"
