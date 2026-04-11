# VilLov Chat Dev Backend

Minimal FastAPI backend for the current VilLov Chat client stage.

## Scope

Implemented:

- passkey-style register/login flow with challenge validation
- database-backed session management
- bearer token authentication with session validation
- public key upload and retrieval
- ciphertext message relay with offline delivery
- authenticated key bundle lookup
- inbox fetch
- message acknowledgement
- seeded SQLite persistence

Deliberately not implemented yet:

- real WebAuthn / passkey verification
- real end-to-end cryptography
- real device linking
- production JWT/session handling
- disappearing message enforcement

## Stack

- FastAPI
- SQLAlchemy
- SQLite

## Project layout

```text
villov-backend/
├── app/
│   ├── api/
│   ├── db/
│   ├── dependencies/
│   ├── schemas/
│   ├── services/
│   ├── config.py
│   └── main.py
├── requirements.txt
├── README.md
└── villov_dev.db
```

## Run locally

```bash
cd villov-API
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Default base URL:

```text
http://127.0.0.1:8000
```

## Seeded users

- `user_alice`
- `user_bob`
- `user_charlie`

## Known development tokens

- `dev-token-user_alice`
- `dev-token-user_bob`
- `dev-token-user_charlie`

## Auth behavior

The backend implements a simplified passkey (WebAuthn-style) flow.

### Register
1. Client requests a challenge (`/auth/passkey/register/begin`)
2. Client responds with credential data (`/auth/passkey/register/finish`)
3. Server stores public credential material and creates a session

### Login
1. Client requests a challenge (`/auth/passkey/login/begin`)
2. Client signs challenge locally
3. Server verifies challenge and credential existence
4. Server creates a session and returns a bearer token

### Sessions

- Sessions are stored in the database
- Each request validates:
  - token existence
  - expiration time
  - revocation status

Invalid, expired, or revoked tokens are rejected with `401 Unauthorized`.

`POST /auth/passkey/begin`

- accepts `{}`
- returns a generated challenge stored on the server
- used for development compatibility

`POST /auth/passkey/finish`

- accepts client response with challenge and credential data
- validates challenge and credential existence
- does not perform real cryptographic verification (development mode)
- returns a bearer token linked to a database session

## Security Model

The backend follows a strict end-to-end encryption architecture.

Server:
- stores only public keys and ciphertext
- authenticates users
- relays messages

Client:
- generates keys
- encrypts messages
- decrypts messages

The server never:
- stores private keys
- decrypts messages
- accesses plaintext content

## Supported endpoints

- `POST /auth/passkey/begin`
- `POST /auth/passkey/finish`
- `GET /keys/{userID}/bundle`
- `POST /keys/upload`
- `POST /messages/send`
- `GET /messages/inbox`
- `POST /messages/ack`
- `GET /health`

## Example requests

### Begin sign-in

```bash
curl -X POST http://127.0.0.1:8000/auth/passkey/begin \
  -H 'Content-Type: application/json' \
  -d '{}'
```

### Finish sign-in

```bash
curl -X POST http://127.0.0.1:8000/auth/passkey/finish \
  -H 'Content-Type: application/json' \
  -d '{
    "credentialID": "stub-credential",
    "clientDataJSON": "stub-client-data",
    "authenticatorData": "stub-auth-data",
    "signature": "stub-signature",
    "userHandle": "user_alice"
  }'
```

### Fetch Bob's key bundle

```bash
curl http://127.0.0.1:8000/keys/user_bob/bundle \
  -H 'Authorization: Bearer dev-token-user_alice'
```

### Send ciphertext to Bob

```bash
curl -X POST http://127.0.0.1:8000/messages/send \
  -H 'Authorization: Bearer dev-token-user_alice' \
  -H 'Content-Type: application/json' \
  -d '{
    "recipientUserID": "user_bob",
    "messageID": "11111111-1111-1111-1111-111111111111",
    "conversationID": "22222222-2222-2222-2222-222222222222",
    "ciphertext": "stub-ciphertext",
    "header": "stub-header",
    "sentAt": "2026-03-26T12:00:00Z"
  }'
```

### Fetch Bob's inbox

```bash
curl http://127.0.0.1:8000/messages/inbox \
  -H 'Authorization: Bearer dev-token-user_bob'
```

### Acknowledge a message as Bob

```bash
curl -X POST http://127.0.0.1:8000/messages/ack \
  -H 'Authorization: Bearer dev-token-user_bob' \
  -H 'Content-Type: application/json' \
  -d '{
    "messageID": "11111111-1111-1111-1111-111111111111"
  }'
```

## Notes for the Swift client

- dates are ISO-8601 strings
- UUIDs are returned as strings
- authenticated endpoints require `Authorization: Bearer <token>`
- the backend preserves `messageID` as the envelope id

## Conversation identity

Authenticated endpoint:

- `POST /conversations/get-or-create`

Example:

```bash
curl -X POST http://127.0.0.1:8000/conversations/get-or-create \
  -H "Authorization: Bearer dev-token-user_alice" \
  -H "Content-Type: application/json" \
  -d '{"recipientUserID":"user_bob"}'
```

Response:

```json
{
  "conversationID": "<uuid>"
}
```

The same `conversationID` is returned for both Alice→Bob and Bob→Alice.
