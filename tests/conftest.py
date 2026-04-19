# tests/conftest.py

import base64
import json
from collections.abc import Generator

from app.config import WEBAUTHN_ORIGIN, WEBAUTHN_RP_ID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = "sqlite://"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _b64url_json(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_bytes(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _pad_b64url(value: str) -> str:
    return value + "=" * ((4 - len(value) % 4) % 4)


def _make_dev_registration_finish(challenge: str, user_handle: str, device_id: str, credential_id: str):
    """
    Craft a registration payload that intentionally fails strict WebAuthn parsing,
    so AuthService falls back to _verify_development_registration(...).
    """
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    client_data_json = _b64url_json(
        {
            "type": "webauthn.create",
            "challenge": challenge,
            "origin": WEBAUTHN_ORIGIN,
        }
    )

    # Invalid real attestationObject, but valid dev fallback JSON payload.
    attestation_object = _b64url_json(
        {
            "format": "dev-passkey-v1",
            "credentialID": credential_id,
            "publicKey": _b64url_bytes(public_key_bytes),
            "signCount": 0,
        }
    )

    finish_payload = {
        "challenge": challenge,
        "credentialID": credential_id,
        "userHandle": user_handle,
        "deviceID": device_id,
        "deviceName": f"{user_handle}-device",
        "platform": "ios",
        "transports": ["internal"],
        "clientDataJSON": client_data_json,
        "attestationObject": attestation_object,
    }

    return finish_payload, private_key


def _make_dev_authentication_finish(
    challenge: str,
    user_handle: str,
    device_id: str,
    credential_id: str,
    private_key,
    sign_count: int = 1,
):
    """
    Craft a login payload that intentionally fails strict WebAuthn parsing,
    so AuthService falls back to _verify_development_authentication(...).
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    client_data = {
        "type": "webauthn.get",
        "challenge": challenge,
        "origin": WEBAUTHN_ORIGIN,
    }
    authenticator_data = {
        "rpID": WEBAUTHN_RP_ID,
        "userPresent": True,
        "signCount": sign_count,
    }

    client_data_bytes = json.dumps(client_data, separators=(",", ":")).encode("utf-8")
    authenticator_data_bytes = json.dumps(authenticator_data, separators=(",", ":")).encode("utf-8")
    signature_input = authenticator_data_bytes + client_data_bytes

    signature = private_key.sign(signature_input, ec.ECDSA(hashes.SHA256()))

    finish_payload = {
        "challenge": challenge,
        "credentialID": credential_id,
        "userHandle": user_handle,
        "deviceID": device_id,
        "deviceName": f"{user_handle}-device",
        "platform": "ios",
        "transports": ["internal"],
        "clientDataJSON": _b64url_bytes(client_data_bytes),
        "authenticatorData": _b64url_bytes(authenticator_data_bytes),
        "signature": _b64url_bytes(signature),
    }

    return finish_payload


def register_and_authenticate_user(
    client: TestClient,
    user_handle: str,
    device_id: str | None = None,
    credential_id: str | None = None,
) -> dict:
    device_id = device_id or f"device-{user_handle}-iphone"
    credential_id = credential_id or f"cred-{user_handle}"

    begin_resp = client.post(
        "/auth/passkey/register/begin",
        json={
            "userHandle": user_handle,
            "deviceID": device_id,
            "displayName": user_handle,
        },
    )
    assert begin_resp.status_code == 200, begin_resp.text
    begin_data = begin_resp.json()

    finish_payload, private_key = _make_dev_registration_finish(
        challenge=begin_data["challenge"],
        user_handle=user_handle,
        device_id=device_id,
        credential_id=credential_id,
    )

    finish_resp = client.post("/auth/passkey/register/finish", json=finish_payload)
    assert finish_resp.status_code == 200, finish_resp.text
    token_data = finish_resp.json()

    return {
        "user_id": user_handle,
        "device_id": device_id,
        "credential_id": credential_id,
        "access_token": token_data["accessToken"],
        "private_key": private_key,
    }


def login_user(
    client: TestClient,
    user_handle: str,
    credential_id: str,
    private_key,
    device_id: str | None = None,
    sign_count: int = 1,
) -> dict:
    device_id = device_id or f"device-{user_handle}-iphone"

    begin_resp = client.post(
        "/auth/passkey/login/begin",
        json={
            "userHandle": user_handle,
            "deviceID": device_id,
            "displayName": None,
        },
    )
    assert begin_resp.status_code == 200, begin_resp.text
    begin_data = begin_resp.json()

    finish_payload = _make_dev_authentication_finish(
        challenge=begin_data["challenge"],
        user_handle=user_handle,
        device_id=device_id,
        credential_id=credential_id,
        private_key=private_key,
        sign_count=sign_count,
    )

    finish_resp = client.post("/auth/passkey/login/finish", json=finish_payload)
    assert finish_resp.status_code == 200, finish_resp.text
    token_data = finish_resp.json()

    return {
        "access_token": token_data["accessToken"],
        "expires_at": token_data["expiresAt"],
    }


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def make_key_upload_request(user_id: str, opk_count: int = 3) -> dict:
    def b64(s: str) -> str:
        return base64.b64encode(s.encode("utf-8")).decode("utf-8")

    return {
        "userID": user_id,
        "identityKey": b64(f"{user_id}-signing-key"),
        "identityAgreementKey": b64(f"{user_id}-agreement-key"),
        "signedPrekey": b64(f"{user_id}-signed-prekey"),
        "signedPrekeySignature": b64(f"{user_id}-signed-prekey-signature"),
        "oneTimePrekeys": [
            {
                "id": f"{user_id}-opk-{i}",
                "publicKey": b64(f"{user_id}-opk-public-{i}"),
            }
            for i in range(opk_count)
        ],
    }