# app/services/auth_service.py

import json
import logging
import secrets
from datetime import UTC, datetime, timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import select
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.config import (
    CHALLENGE_TTL_MINUTES,
    ENABLE_DEVELOPMENT_PASSKEY_AUTH,
    TOKEN_TTL_DAYS,
    WEBAUTHN_ORIGIN,
    WEBAUTHN_RP_ID,
    WEBAUTHN_RP_NAME,
)
from app.db.models import AuthChallenge, AuthSession, Device, PasskeyCredential, User
from app.schemas.auth import (
    PasskeyAssertionBeginResponse,
    PasskeyAssertionFinishRequest,
    PasskeyRegistrationBeginResponse,
    PasskeyRegistrationFinishRequest,
    SessionToken,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def begin_register_passkey(
        self,
        user_id: str,
        device_id: str | None = None,
        display_name: str | None = None,
    ) -> PasskeyRegistrationBeginResponse:
        normalized_user_id = self._normalize_user_id(user_id)
        validated_display_name = self._validate_display_name(display_name)

        user = self._get_or_create_user(
            user_id=normalized_user_id,
            display_name=validated_display_name or normalized_user_id,
        )

        options = generate_registration_options(
            rp_id=WEBAUTHN_RP_ID,
            rp_name=WEBAUTHN_RP_NAME,
            user_id=user.user_id.encode("utf-8"),
            user_name=user.user_id,
            user_display_name=user.display_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        options_json = json.loads(options_to_json(options))
        challenge = options_json["challenge"]

        self._store_challenge(
            challenge=challenge,
            user_id=user.user_id,
            device_id=None,
            flow_type="register",
        )

        return PasskeyRegistrationBeginResponse(
            challenge=challenge,
            relyingPartyID=WEBAUTHN_RP_ID,
            userID=user.user_id,
            userName=user.user_id,
            displayName=user.display_name,
        )

    def finish_register_passkey(
        self,
        request: PasskeyRegistrationFinishRequest,
    ) -> SessionToken:
        challenge_row = self._get_valid_challenge_or_raise(
            challenge=request.challenge,
            flow_type="register",
        )

        if request.userHandle != challenge_row.user_id:
            raise PermissionError("challenge_user_mismatch")

        user = self._get_user_or_raise(challenge_row.user_id)
        resolved_device_id = request.deviceID or f"device-{user.user_id}-iphone"
        device = self._get_or_create_device(
            user_id=user.user_id,
            device_id=resolved_device_id,
            device_name=request.deviceName or f"{user.user_id} iPhone",
            platform=request.platform or "ios",
        )

        stored_credential_id, public_key_bytes, sign_count = self._verify_registration(
            request
        )
        transports_str = json.dumps(request.transports or [])

        existing = self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.credential_id == stored_credential_id
            )
        ).scalar_one_or_none()

        if existing is None:
            credential = PasskeyCredential(
                user_id=user.user_id,
                device_id=device.device_id,
                credential_id=stored_credential_id,
                public_key_material_or_placeholder=self._encode_public_key_bytes(
                    public_key_bytes
                ),
                sign_count=sign_count,
                transports_or_metadata=transports_str,
                created_at=self._utc_now(),
            )
            self.db.add(credential)
        else:
            existing.user_id = user.user_id
            existing.device_id = device.device_id
            existing.public_key_material_or_placeholder = self._encode_public_key_bytes(
                public_key_bytes
            )
            existing.sign_count = sign_count
            existing.transports_or_metadata = transports_str

        challenge_row.consumed_at = self._utc_now()
        token = self._create_session_token(user.user_id, device.device_id)
        self.db.commit()
        return token

    def begin_login_passkey(
        self,
        user_id: str,
        device_id: str | None = None,
    ) -> PasskeyAssertionBeginResponse:
        normalized_user_id = self._normalize_user_id(user_id)
        user = self._get_user_or_raise(normalized_user_id)

        stored_credentials = self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.user_id == user.user_id
            )
        ).scalars().all()

        allow_credentials: list[PublicKeyCredentialDescriptor] = []

        for credential in stored_credentials:
            credential_id_bytes = self._try_decode_credential_id(
                credential.credential_id
            )
            if credential_id_bytes is None:
                logger.warning(
                    "Skipping malformed credential_id during login begin "
                    "for user_id=%s passkey_credential_id=%s stored_credential_id=%r",
                    user.user_id,
                    credential.id,
                    credential.credential_id,
                )
                continue

            allow_credentials.append(
                PublicKeyCredentialDescriptor(id=credential_id_bytes)
            )

        options = generate_authentication_options(
            rp_id=WEBAUTHN_RP_ID,
            allow_credentials=allow_credentials if allow_credentials else None,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        options_json = json.loads(options_to_json(options))
        challenge = options_json["challenge"]

        self._store_challenge(
            challenge=challenge,
            user_id=user.user_id,
            device_id=device_id,
            flow_type="login",
        )

        return PasskeyAssertionBeginResponse(
            challenge=challenge,
            relyingPartyID=WEBAUTHN_RP_ID,
            userID=user.user_id,
        )

    def finish_login_passkey(
        self,
        request: PasskeyAssertionFinishRequest,
    ) -> SessionToken:
        challenge_row = self._get_valid_challenge_or_raise(
            challenge=request.challenge,
            flow_type="login",
        )

        if request.userHandle and request.userHandle != challenge_row.user_id:
            raise PermissionError("challenge_user_mismatch")

        credential = self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.credential_id == request.credentialID
            )
        ).scalar_one_or_none()

        if credential is None:
            raise ValueError("credential_not_found")

        if credential.user_id != challenge_row.user_id:
            raise PermissionError("credential_user_mismatch")

        new_sign_count = self._verify_authentication(
            request=request,
            credential=credential,
        )

        credential.sign_count = new_sign_count
        challenge_row.consumed_at = self._utc_now()

        resolved_device_id = request.deviceID or credential.device_id
        device = self._get_or_create_device(
            user_id=credential.user_id,
            device_id=resolved_device_id,
            device_name=request.deviceName or f"{credential.user_id} iPhone",
            platform=request.platform or "ios",
        )

        token = self._create_session_token(credential.user_id, device.device_id)
        self.db.commit()
        return token

    def _verify_registration(
        self,
        request: PasskeyRegistrationFinishRequest,
    ) -> tuple[str, bytes, int]:
        try:
            verification = verify_registration_response(
                credential={
                    "id": request.credentialID,
                    "rawId": request.credentialID,
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": request.clientDataJSON,
                        "attestationObject": request.attestationObject,
                    },
                },
                expected_challenge=request.challenge,
                expected_rp_id=WEBAUTHN_RP_ID,
                expected_origin=WEBAUTHN_ORIGIN,
                require_user_verification=False,
            )

            verified_credential_id_bytes = self._extract_verified_credential_id_bytes(
                verification=verification,
                fallback_credential_id=request.credentialID,
            )
            stored_credential_id = self._encode_credential_id(
                verified_credential_id_bytes
            )

            return (
                stored_credential_id,
                verification.credential_public_key,
                verification.sign_count,
            )

        except InvalidRegistrationResponse as exc:
            if not ENABLE_DEVELOPMENT_PASSKEY_AUTH:
                raise ValueError(f"registration_verification_failed:{exc}") from exc

            logger.warning(
                "Strict WebAuthn registration failed, falling back to development verification: %s",
                exc,
            )
            return self._verify_development_registration(request)

    def _verify_authentication(
        self,
        request: PasskeyAssertionFinishRequest,
        credential: PasskeyCredential,
    ) -> int:
        try:
            verification = verify_authentication_response(
                credential={
                    "id": request.credentialID,
                    "rawId": request.credentialID,
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": request.clientDataJSON,
                        "authenticatorData": request.authenticatorData,
                        "signature": request.signature,
                    },
                },
                expected_challenge=request.challenge,
                expected_rp_id=WEBAUTHN_RP_ID,
                expected_origin=WEBAUTHN_ORIGIN,
                credential_public_key=self._decode_public_key_bytes(
                    credential.public_key_material_or_placeholder
                ),
                credential_current_sign_count=credential.sign_count,
                require_user_verification=False,
            )
            return verification.new_sign_count

        except InvalidAuthenticationResponse as exc:
            if not ENABLE_DEVELOPMENT_PASSKEY_AUTH:
                raise ValueError(f"authentication_verification_failed:{exc}") from exc

            logger.warning(
                "Strict WebAuthn authentication failed, falling back to development verification: %s",
                exc,
            )
            return self._verify_development_authentication(
                request=request,
                credential=credential,
            )

    def _verify_development_registration(
        self,
        request: PasskeyRegistrationFinishRequest,
    ) -> tuple[str, bytes, int]:
        client_data = self._decode_base64url_json(request.clientDataJSON)
        attestation = self._decode_base64url_json(request.attestationObject)

        if client_data.get("type") != "webauthn.create":
            raise ValueError("dev_registration_invalid_type")

        if client_data.get("challenge") != request.challenge:
            raise ValueError("dev_registration_challenge_mismatch")

        if client_data.get("origin") != WEBAUTHN_ORIGIN:
            raise ValueError("dev_registration_origin_mismatch")

        if attestation.get("format") != "dev-passkey-v1":
            raise ValueError("dev_registration_invalid_attestation_format")

        if attestation.get("credentialID") != request.credentialID:
            raise ValueError("dev_registration_credential_mismatch")

        public_key_encoded = attestation.get("publicKey")
        if not isinstance(public_key_encoded, str):
            raise ValueError("dev_registration_missing_public_key")

        sign_count = attestation.get("signCount", 0)
        if not isinstance(sign_count, int):
            raise ValueError("dev_registration_invalid_sign_count")

        try:
            public_key_bytes = base64url_to_bytes(public_key_encoded)
        except Exception as exc:
            raise ValueError("dev_registration_invalid_public_key_encoding") from exc

        try:
            ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(),
                public_key_bytes,
            )
        except Exception as exc:
            raise ValueError("dev_registration_invalid_public_key") from exc

        stored_credential_id = request.credentialID

        return (
            stored_credential_id,
            public_key_bytes,
            sign_count,
        )

    def _verify_development_authentication(
        self,
        request: PasskeyAssertionFinishRequest,
        credential: PasskeyCredential,
    ) -> int:
        client_data_bytes = base64url_to_bytes(request.clientDataJSON)
        authenticator_data_bytes = base64url_to_bytes(request.authenticatorData)
        signature_bytes = base64url_to_bytes(request.signature)

        try:
            client_data = json.loads(client_data_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError("dev_auth_invalid_client_data") from exc

        try:
            authenticator_data = json.loads(authenticator_data_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError("dev_auth_invalid_authenticator_data") from exc

        if client_data.get("type") != "webauthn.get":
            raise ValueError("dev_auth_invalid_type")

        if client_data.get("challenge") != request.challenge:
            raise ValueError("dev_auth_challenge_mismatch")

        if client_data.get("origin") != WEBAUTHN_ORIGIN:
            raise ValueError("dev_auth_origin_mismatch")

        if authenticator_data.get("rpID") != WEBAUTHN_RP_ID:
            raise ValueError("dev_auth_rp_id_mismatch")

        if authenticator_data.get("userPresent") is not True:
            raise ValueError("dev_auth_user_not_present")

        sign_count = authenticator_data.get("signCount")
        if not isinstance(sign_count, int):
            raise ValueError("dev_auth_invalid_sign_count")

        if sign_count <= credential.sign_count:
            raise ValueError("dev_auth_sign_count_not_increasing")

        public_key_bytes = self._decode_public_key_bytes(
            credential.public_key_material_or_placeholder
        )

        try:
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(),
                public_key_bytes,
            )
        except Exception as exc:
            raise ValueError("dev_auth_invalid_stored_public_key") from exc

        signature_input = authenticator_data_bytes + client_data_bytes

        try:
            public_key.verify(
                signature_bytes,
                signature_input,
                ec.ECDSA(hashes.SHA256()),
            )
        except InvalidSignature as exc:
            raise ValueError("dev_auth_signature_invalid") from exc

        return sign_count

    def _decode_base64url_json(self, value: str) -> dict:
        try:
            decoded = base64url_to_bytes(value)
            return json.loads(decoded.decode("utf-8"))
        except Exception as exc:
            raise ValueError("invalid_base64url_json") from exc

    def _store_challenge(
        self,
        challenge: str,
        user_id: str,
        device_id: str | None,
        flow_type: str,
    ) -> None:
        row = AuthChallenge(
            challenge=challenge,
            flow_type=flow_type,
            user_id=user_id,
            device_id=device_id,
            created_at=self._utc_now(),
            expires_at=self._utc_now() + timedelta(minutes=CHALLENGE_TTL_MINUTES),
            consumed_at=None,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

    def _get_valid_challenge_or_raise(
        self,
        challenge: str,
        flow_type: str,
    ) -> AuthChallenge:
        row = self.db.execute(
            select(AuthChallenge).where(
                AuthChallenge.challenge == challenge,
                AuthChallenge.flow_type == flow_type,
            )
        ).scalar_one_or_none()

        if row is None:
            raise ValueError("challenge_not_found")
        if row.consumed_at is not None:
            raise ValueError("challenge_already_used")

        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at < self._utc_now():
            raise ValueError("challenge_expired")

        return row

    def _get_user_or_raise(self, user_id: str) -> User:
        user = self.db.execute(
            select(User).where(User.user_id == user_id)
        ).scalar_one_or_none()
        if user is None:
            raise ValueError("user_not_found")
        return user

    def _get_or_create_user(
        self,
        user_id: str,
        display_name: str,
    ) -> User:
        user = self.db.execute(
            select(User).where(User.user_id == user_id)
        ).scalar_one_or_none()

        if user is not None:
            if display_name and user.display_name != display_name:
                user.display_name = display_name
                user.updated_at = self._utc_now()
            return user

        now = self._utc_now()
        user = User(
            user_id=user_id,
            display_name=display_name,
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def _normalize_user_id(self, user_id: str) -> str:
        normalized = user_id.strip().lower()
        if not normalized:
            raise ValueError("user_id_required")
        if not normalized.replace("_", "").isalnum():
            raise ValueError("user_id_invalid")
        return normalized

    def _validate_display_name(self, display_name: str | None) -> str | None:
        if display_name is None:
            return None
        normalized = display_name.strip()
        if not normalized:
            return None
        if len(normalized) > 100:
            raise ValueError("display_name_too_long")
        return normalized

    def _get_or_create_device(
        self,
        user_id: str,
        device_id: str,
        device_name: str,
        platform: str,
    ) -> Device:
        device = self.db.execute(
            select(Device).where(Device.device_id == device_id)
        ).scalar_one_or_none()

        now = self._utc_now()

        if device is None:
            device = Device(
                device_id=device_id,
                user_id=user_id,
                device_name=device_name,
                platform=platform,
                created_at=now,
                last_seen_at=now,
                is_active=True,
            )
            self.db.add(device)
            self.db.flush()
            return device

        device.user_id = user_id
        device.device_name = device_name
        device.platform = platform
        device.last_seen_at = now
        device.is_active = True
        return device

    def _create_session_token(self, user_id: str, device_id: str) -> SessionToken:
        now = self._utc_now()
        expires_at = now + timedelta(days=TOKEN_TTL_DAYS)
        access_token = secrets.token_urlsafe(32)

        session = AuthSession(
            user_id=user_id,
            device_id=device_id,
            access_token=access_token,
            expires_at=expires_at,
            created_at=now,
            revoked_at=None,
        )
        self.db.add(session)

        return SessionToken(
            accessToken=access_token,
            expiresAt=expires_at,
        )

    @staticmethod
    def _encode_public_key_bytes(public_key: bytes) -> str:
        return public_key.hex()

    @staticmethod
    def _decode_public_key_bytes(public_key_hex: str) -> bytes:
        return bytes.fromhex(public_key_hex)

    @staticmethod
    def _encode_credential_id(credential_id: bytes) -> str:
        return bytes_to_base64url(credential_id)

    @staticmethod
    def _decode_credential_id(credential_id: str) -> bytes:
        return base64url_to_bytes(credential_id)

    def _try_decode_credential_id(self, credential_id: str) -> bytes | None:
        if not credential_id:
            return None

        try:
            return self._decode_credential_id(credential_id)
        except Exception:
            pass

        try:
            return bytes.fromhex(credential_id)
        except Exception:
            pass

        return None

    def _extract_verified_credential_id_bytes(
        self,
        verification,
        fallback_credential_id: str,
    ) -> bytes:
        verification_credential_id = getattr(verification, "credential_id", None)
        if isinstance(verification_credential_id, bytes):
            return verification_credential_id

        fallback_bytes = self._try_decode_credential_id(fallback_credential_id)
        if fallback_bytes is None:
            raise ValueError("registration_credential_id_invalid_format")
        return fallback_bytes

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)