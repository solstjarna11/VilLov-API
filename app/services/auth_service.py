# app/services/auth_service.py

import json
import logging
import secrets
from datetime import UTC, datetime, timedelta

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
    ) -> PasskeyRegistrationBeginResponse:
        user = self._get_user_or_raise(user_id)

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
            device_id=device_id,
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
        except InvalidRegistrationResponse as exc:
            raise ValueError(f"registration_verification_failed:{exc}") from exc

        verified_credential_id_bytes = self._extract_verified_credential_id_bytes(
            verification=verification,
            fallback_credential_id=request.credentialID,
        )
        stored_credential_id = self._encode_credential_id(verified_credential_id_bytes)
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
                    verification.credential_public_key
                ),
                sign_count=verification.sign_count,
                transports_or_metadata=transports_str,
                created_at=self._utc_now(),
            )
            self.db.add(credential)
        else:
            existing.user_id = user.user_id
            existing.device_id = device.device_id
            existing.public_key_material_or_placeholder = self._encode_public_key_bytes(
                verification.credential_public_key
            )
            existing.sign_count = verification.sign_count
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
        user = self._get_user_or_raise(user_id)

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
                    "Skipping malformed legacy credential_id during login begin "
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
        except InvalidAuthenticationResponse as exc:
            raise ValueError(f"authentication_verification_failed:{exc}") from exc

        credential.sign_count = verification.new_sign_count
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
        self.db.flush()

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
        if row.expires_at < self._utc_now():
            raise ValueError("challenge_expired")

        return row

    def _get_user_or_raise(self, user_id: str) -> User:
        user = self.db.execute(
            select(User).where(User.user_id == user_id)
        ).scalar_one_or_none()
        if user is None:
            raise ValueError("user_not_found")
        return user

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
        """
        Decode a stored credential ID into raw bytes.

        Current canonical format:
        - base64url string

        Legacy tolerance:
        - hex string, if older data was stored as hex
        - malformed values are ignored by returning None
        """
        if not credential_id:
            return None

        # Canonical path: base64url text -> bytes
        try:
            return self._decode_credential_id(credential_id)
        except Exception:
            pass

        # Legacy fallback: hex text -> bytes
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
        """
        Prefer the verified credential ID returned by the library.
        Fall back to decoding the client-supplied credential ID if needed.
        """
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