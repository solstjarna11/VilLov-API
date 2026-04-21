# app/main.py

import logging

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

try:
    from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
except ImportError:  # pragma: no cover
    ProxyHeadersMiddleware = None

from app.api.auth import router as auth_router
from app.api.contacts import router as contacts_router
from app.api.conversations import router as conversations_router
from app.api.keys import router as keys_router
from app.api.messages import router as messages_router
from app.config import ALLOWED_HOSTS, API_TITLE, API_VERSION, RUN_DB_CREATE_ALL
from app.db.database import Base, engine, get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(title=API_TITLE, version=API_VERSION)

if ProxyHeadersMiddleware is not None:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS if ALLOWED_HOSTS else ["*"],
)

app.include_router(auth_router)
app.include_router(contacts_router)
app.include_router(keys_router)
app.include_router(conversations_router)
app.include_router(messages_router)


@app.on_event("startup")
def startup() -> None:
    # Good enough for local dev / coursework demos.
    # For a fuller deployment setup, replace with Alembic migrations.
    if RUN_DB_CREATE_ALL:
        Base.metadata.create_all(bind=engine)


@app.get("/.well-known/apple-app-site-association", include_in_schema=False)
def apple_app_site_association():
    return JSONResponse(
        content={
            "webcredentials": {
                "apps": ["OUR_TEAM_ID.com.our.bundleid"]
            }
        },
        media_type="application/json",
    )


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


# Backward-compatible simple endpoint
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}