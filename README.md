# 📘 VilLov-API — README.md

## Overview

**VilLov-API** is the backend service for the VilLov Private Messaging platform — a secure, end-to-end encrypted (E2EE) messaging system designed for privacy-sensitive users such as journalists, activists, and citizens.

The API acts strictly as a **coordination and relay layer**, providing:

- Passkey (WebAuthn) authentication  
- Public key distribution (identity + prekeys)  
- Ciphertext message relay  
- Minimal metadata storage  

It is explicitly designed so that **the server never has access to plaintext messages or private cryptographic keys**.

---

## Architecture Summary

- **Framework:** FastAPI (Python)
- **Deployment Model:** Stateless containerized services behind a load balancer
- **Trust Model:** Zero access to plaintext and private keys
- **Security Boundary:** All cryptographic operations occur on the client

### Backend Responsibilities

| Component | Responsibility |
|----------|----------------|
| Auth Service | Passkey registration & authentication |
| Credential Store | Stores public passkey credentials only |
| Key Directory | Stores public identity keys & prekeys |
| Relay Queue | Stores ciphertext messages for delivery |
| Metadata Store | Minimal routing metadata |
| Device Registry | Tracks user devices |

---

## Cryptographic Model

VilLov uses **two separate cryptographic domains**:

### 1. Authentication Keys (Passkeys)

- WebAuthn / passkey-based authentication  
- Private keys stored on user device (or dev fallback)  
- Server stores:
  - Public key  
  - Credential ID  
  - Signature counter  

### 2. Messaging Keys (E2EE)

- Generated and stored **only on client devices**  
- Includes:
  - Identity signing key  
  - Identity agreement key  
  - Signed prekeys  
  - One-time prekeys  

### Protocol Design

- X3DH-style asynchronous key agreement  
- Double Ratchet-style key evolution  
- AES-GCM authenticated encryption  
- HKDF-SHA256 key derivation  

---

## API Capabilities

### Authentication

- `POST /auth/register` — Register passkey  
- `POST /auth/login` — Authenticate via challenge-response  

### Key Management

- `POST /keys/upload` — Upload public identity & prekeys  
- `GET /keys/{user_id}` — Fetch recipient key bundle  

### Messaging

- `POST /messages/send` — Send ciphertext message  
- `GET /messages/queue` — Retrieve queued messages  

### Device Management

- Device registration and linking  
- Multi-device credential support  

---

## Security Properties

### Strong Guarantees

- **Confidentiality:** Server cannot decrypt messages  
- **Integrity:** AEAD (AES-GCM) ensures tamper detection  
- **Authenticity:** Signature + identity verification  
- **Forward Secrecy:** Double Ratchet key evolution  
- **Credential Minimisation:** No passwords stored  

### Residual Risks

- Metadata analysis (timing, communication patterns)  
- Endpoint compromise  
- User failure to verify identities  

---

## Development Passkey Fallback

Due to lack of an Apple Developer Account, a **development passkey system** is implemented.

### Dev Passkey Characteristics

- Locally generated P-256 key pair  
- Simulated WebAuthn challenge-response  
- App-controlled credential storage  

### Limitations

- No Secure Enclave protection  
- No origin/RP binding enforcement  
- User verification flags are simulated  
- Not phishing-resistant  

### Configuration

```env
ENABLE_DEVELOPMENT_PASSKEY_AUTH=true
```

Must be disabled in production.

---

## Comparison: Dev Passkey vs Real WebAuthn

| Property | Dev Passkey | Real WebAuthn |
|--------|------------|---------------|
| Key storage | App-controlled | Secure Enclave / OS |
| Phishing resistance | Weak | Strong |
| User verification | Simulated | Enforced |
| Origin binding | Manual | OS/browser enforced |
| Production-ready | no | yes |

---

## Security Considerations

### Recommended Improvements

- Disable dev passkey by default  
- Require user verification in WebAuthn  
- Hash session tokens in database  
- Remove `.env` secrets from repository  

### Metadata Exposure

The server stores:

- sender/recipient IDs  
- timestamps  
- delivery state  

This is minimized but still allows traffic analysis.

---

## Running the API

### Requirements

- Python 3.10+  
- PostgreSQL  
- Uvicorn  

### Setup

```bash
pip install -r requirements.txt
```

```bash
uvicorn main:app --reload
```

### Environment Variables

```env
DATABASE_URL=postgresql://...
ENABLE_DEVELOPMENT_PASSKEY_AUTH=true
SECRET_KEY=...
```

---

## Deployment

Recommended:

- Dockerized FastAPI service  
- Hosted on Render / similar platform  
- Behind load balancer  
- TLS termination at edge  

---

## Summary

VilLov-API provides a **zero-knowledge backend** that:

- Never accesses plaintext  
- Never stores private keys  
- Only coordinates authentication and encrypted message delivery  

---
