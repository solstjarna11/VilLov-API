from sqlalchemy import update
from app.db.models import AuthSession
from tests.conftest import TestingSessionLocal
from datetime import UTC, datetime, timedelta

def test_register_begin_returns_challenge(client):
    response = client.post("/auth/passkey/register/begin")
    assert response.status_code == 200
    data = response.json()
    assert "challenge" in data
    assert "relyingPartyID" in data
    assert "userID" in data
    assert data["userID"] == "user_alice"

def test_login_begin_returns_challenge(client):
    response = client.post("/auth/passkey/login/begin")
    assert response.status_code == 200
    data = response.json()
    assert "challenge" in data
    assert "relyingPartyID" in data
    assert "userID" in data

def test_invalid_token_is_rejected(client):
    response = client.get("/messages/inbox", headers={"Authorization": "Bearer definitely invalid token"})
    assert response.status_code == 401

def test_register_finish_returns_session_token(client):
    begin_response = client.post("/auth/passkey/register/begin")
    assert begin_response.status_code == 200
    challenge = begin_response.json()["challenge"]

    finish_response = client.post(
        "/auth/passkey/register/finish",
        json={
            "challenge": challenge,
            "credentialID": "11111111-1111-1111-1111-111111111111",
            "userHandle": "user_alice",
            "deviceID": "device-user_alice-test",
            "deviceName": "Test iPhone",
            "platform": "ios",
            "transports": "internal",
            "clientDataJSON": "stub-client-data",
            "authenticatorData": "stub-auth-data",
            "signature": "stub-signature",
        },
    )

    assert finish_response.status_code == 200
    data = finish_response.json()
    assert "accessToken" in data
    assert "expiresAt" in data

def test_login_finish_returns_session_token_after_registration(client):
    register_begin = client.post("/auth/passkey/register/begin")
    challenge = register_begin.json()["challenge"]

    register_finish = client.post(
        "/auth/passkey/register/finish",
        json={
            "challenge": challenge,
            "credentialID": "22222222-2222-2222-2222-222222222222",
            "userHandle": "user_alice",
            "deviceID": "device-user_alice-login",
            "deviceName": "Login iPhone",
            "platform": "ios",
            "transports": "internal",
            "clientDataJSON": "stub-client-data",
            "authenticatorData": "stub-auth-data",
            "signature": "stub-signature",
        },
    )
    assert register_finish.status_code == 200

    login_begin = client.post("/auth/passkey/login/begin")
    assert login_begin.status_code == 200
    login_challenge = login_begin.json()["challenge"]

    login_finish = client.post(
        "/auth/passkey/login/finish",
        json={
            "challenge": login_challenge,
            "credentialID": "22222222-2222-2222-2222-222222222222",
            "userHandle": "user_alice",
            "deviceID": "device-user_alice-login",
            "deviceName": "Login iPhone",
            "platform": "ios",
            "clientDataJSON": "stub-client-data",
            "authenticatorData": "stub-auth-data",
            "signature": "stub-signature",
        },
    )

    assert login_finish.status_code == 200
    data = login_finish.json()
    assert "accessToken" in data
    assert "expiresAt" in data    
def test_invalid_challenge_is_rejected(client):
    response = client.post(
        "/auth/passkey/login/finish",
        json={
            "challenge": "invalid-challenge",
            "credentialID": "33333333-3333-3333-3333-333333333333",
            "userHandle": "user_alice",
            "deviceID": "device-user_alice-invalid",
            "deviceName": "Invalid iPhone",
            "platform": "ios",
            "clientDataJSON": "stub-client-data",
            "authenticatorData": "stub-auth-data",
            "signature": "stub-signature",
        },
    )
    assert response.status_code == 401

def test_expired_session_is_rejected(client):
    db= TestingSessionLocal()
    try:
        db.execute(update(AuthSession).where(AuthSession.access_token == "dev-token-user_alice")
                   .values(expires_at=datetime.now(UTC) - timedelta(days=1)))
        db.commit()
    finally:
        db.close()
    response=client.get("/messages/inbox",headers={"Authorization": "Bearer dev-token-user_alice"},)
    assert response.status_code == 401