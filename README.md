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
- contacts and conversation directory APIs
- seeded SQLite persistence

Deliberately not implemented yet:

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
auth.villovchat.com
```

## Known development tokens

- `dev-token-user_alice`
- `dev-token-user_bob`
- `dev-token-user_charlie`

## Auth behavior

The backend implements a simplified passkey (WebAuthn-style) flow.

### Register

1. Client requests a challenge (`/auth/passkey/register/begin`)
   - accepts optional `userHandle` and `deviceID`
2. Client responds with credential data (`/auth/passkey/register/finish`)
3. Server stores public credential material and creates a session

### Login

1. Client requests a challenge (`/auth/passkey/login/begin`)
   - accepts optional `userHandle` and `deviceID`
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

### Legacy endpoints (dev compatibility)

`POST /auth/passkey/begin`  
`POST /auth/passkey/finish`

These map to the login flow and are retained for compatibility.

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

### Auth

- `POST /auth/passkey/login/begin`
- `POST /auth/passkey/login/finish`
- `POST /auth/passkey/register/begin`
- `POST /auth/passkey/register/finish`

### Contacts & Conversations

- `GET /contacts`
- `GET /conversations`
- `POST /conversations/get-or-create`

### Keys & Messaging

- `GET /keys/{userID}/bundle`
- `POST /keys/upload`
- `POST /messages/send`
- `GET /messages/inbox`
- `POST /messages/ack`

### Misc

- `GET /health`

## Example requests

### Begin login (Bob)

```bash
curl -X POST http://127.0.0.1:8000/auth/passkey/login/begin \
  -H 'Content-Type: application/json' \
  -d '{
    "userHandle": "user_bob",
    "deviceID": "device-user_bob-iphone"
  }'
```

### Finish login

```bash
curl -X POST http://127.0.0.1:8000/auth/passkey/login/finish \
  -H 'Content-Type: application/json' \
  -d '{
    "credentialID": "credential-user_bob-primary",
    "clientDataJSON": "stub-client-data",
    "authenticatorData": "stub-auth-data",
    "signature": "stub-signature",
    "userHandle": "user_bob",
    "deviceID": "device-user_bob-iphone"
  }'
```

### Fetch contacts

```bash
curl http://127.0.0.1:8000/contacts \
  -H 'Authorization: Bearer dev-token-user_alice'
```

### Fetch conversations

```bash
curl http://127.0.0.1:8000/conversations \
  -H 'Authorization: Bearer dev-token-user_alice'
```

Example response:

```json
[
  {
    "conversationID": "c31d58bf-ab98-4c75-8c82-900def70c8af",
    "participantAUserID": "user_alice",
    "participantBUserID": "user_bob",
    "createdAt": "2026-04-12T22:21:09.043405Z"
  }
]
```

### Get or create conversation

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

### Fetch inbox

```bash
curl http://127.0.0.1:8000/messages/inbox \
  -H 'Authorization: Bearer dev-token-user_bob'
```

### Acknowledge message

```bash
curl -X POST http://127.0.0.1:8000/messages/ack \
  -H 'Authorization: Bearer dev-token-user_bob' \
  -H 'Content-Type: application/json' \
  -d '{
    "messageID": "11111111-1111-1111-1111-111111111111"
  }'
```

## Notes for the Swift client

- dates are ISO-8601 UTC strings with `Z` suffix  
  (e.g. `2026-04-12T22:21:09.043405Z`)
- UUIDs are returned as strings
- authenticated endpoints require `Authorization: Bearer <token>`
- the backend preserves `messageID` as the envelope id

## Conversation identity

The same `conversationID` is returned for both directions:

- Alice → Bob
- Bob → Alice

This ensures a single shared conversation per user pair.