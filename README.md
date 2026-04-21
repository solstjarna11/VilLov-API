# VilLov Chat Backend

FastAPI backend for the  VilLov messaging application.

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
- SQLite backed persistence layer
- end-to-end cryptography


Deliberately not implemented yet:

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

## Deployment

Production base URL:

```text
auth.villovchat.com
```


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
- `POST /messages/delete`

### Misc

- `GET /health`

## Client integration flow

The deployed iOS client uses the backend in the following order:

1. Register or log in with the passkey flow
2. Upload the device’s public key bundle
3. Fetch contacts and existing conversations
4. Get or create a conversation with another user
5. Fetch the recipient public key bundle
6. Encrypt messages locally on-device
7. Send only ciphertext and metadata to the backend
8. Fetch inbox messages and decrypt locally on-device



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