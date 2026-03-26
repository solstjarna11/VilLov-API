from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "villov_dev.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"
API_TITLE = "VilLov Chat Dev Backend"
API_VERSION = "0.1.0"
DEV_RP_ID = "villov.local"
DEFAULT_SIGNIN_USER_ID = "user_alice"
DEFAULT_CHALLENGE = "dev-challenge-123"
TOKEN_TTL_DAYS = 30
