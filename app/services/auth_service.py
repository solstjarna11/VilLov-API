# app/services/auth_service.py

import json
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

        existing = self.db.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.credential_id == request.credentialID
            )
        ).scalar_one_or_none()

        transports_str = json.dumps(request.transports or [])

        if existing is None:
            credential = PasskeyCredential(
                user_id=user.user_id,
                device_id=device.device_id,
                credential_id=request.credentialID,
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

        allow_credentials = [
            PublicKeyCredentialDescriptor(id=credential.credential_id)
            for credential in self.db.execute(
                select(PasskeyCredential).where(
                    PasskeyCredential.user_id == user.user_id
                )
            ).scalars().all()
        ]

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
    def _utc_now() -> datetime:
        return datetime.now(UTC)