import logging

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.keys import router as keys_router
from app.api.messages import router as messages_router
from app.config import API_TITLE, API_VERSION
from app.db.database import Base, SessionLocal, engine
from app.db.seed import seed_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(title=API_TITLE, version=API_VERSION)
app.include_router(auth_router)
app.include_router(keys_router)
app.include_router(conversations_router)
app.include_router(messages_router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_db(db)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
