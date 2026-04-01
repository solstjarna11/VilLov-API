# VilLov Chat Dev Backend

Minimal FastAPI backend for the current VilLov Chat client stage.

## Scope

Implemented:

- stub passkey begin/finish flow
- opaque bearer token issuance
- authenticated key bundle lookup
- ciphertext message relay
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
cd villov-backend
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

`POST /auth/passkey/begin`

- accepts `{}`
- always returns a fixed development challenge

`POST /auth/passkey/finish`

- accepts the client stub payload
- does not verify cryptographically
- returns a bearer token
- defaults to `user_alice`, but if `userHandle` matches a seeded user it will return that user’s token

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
