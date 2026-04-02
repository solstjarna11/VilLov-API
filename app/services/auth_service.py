import secrets
from datetime import UTC, datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import DEFAULT_CHALLENGE, DEFAULT_SIGNIN_USER_ID, DEV_RP_ID, TOKEN_TTL_DAYS

from app.db.repositories.user_repository import UserRepository
from app.db.seed import issue_dev_token
from app.schemas.auth import (
    PasskeyBeginResponse,
    PasskeyFinishRequest,
    SessionToken,
)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.user_repo = UserRepository(db)
    
    def _generate_challenge(self)-> str:
        return secrets.token_urlsafe(32)
    
    def _generate_access_token(self) -> tuple[str, datetime]:
        access_token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(days=TOKEN_TTL_DAYS)
        return access_token, expires_at
    
    def begin_register_passkey(self,*,user_id: str = DEFAULT_SIGNIN_USER_ID,device_id: str | None = None,) -> PasskeyBeginResponse:
        user = self.user_repo.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        challenge = self._generate_challenge()
        self.user_repo.create_challenge(
            challenge=challenge,
            flow_type="register",
            user_id=user_id,
            device_id=device_id,
        )

        return PasskeyBeginResponse(
            challenge=challenge,
            relyingPartyID=DEV_RP_ID,
            userID=user_id,
        )
    
    def begin_login_passkey(self,*,user_id: str = DEFAULT_SIGNIN_USER_ID,device_id: str | None = None,) -> PasskeyBeginResponse:
        user = self.user_repo.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        challenge = self._generate_challenge()
        self.user_repo.create_challenge(
            challenge=challenge,
            flow_type="login",
            user_id=user_id,
            device_id=device_id,
        )

        return PasskeyBeginResponse(
            challenge=challenge,
            relyingPartyID=DEV_RP_ID,
            userID=user_id,
        )
    
    def finish_register_passkey(self, request: PasskeyFinishRequest) -> SessionToken:
        user_id = request.userHandle or DEFAULT_SIGNIN_USER_ID
        challenge_row = self.user_repo.get_active_challenge(request.challenge, "register")
        if challenge_row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired registration")

        if challenge_row.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Challenge does not belong to this user",
            )

        credential_id = request.credentialID
        if self.user_repo.get_credential(credential_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Credential already registered",
            )

        device_id = request.deviceID or f"device-{user_id}-passkey"
        device = self.user_repo.create_or_update_device(
            user_id=user_id,
            device_id=device_id,
            device_name=request.deviceName or f"{user_id} device",
            platform=request.platform or "ios",
        )

        self.user_repo.create_credential(
            user_id=user_id,
            device_id=device.device_id,
            credential_id=credential_id,
            public_key_material_or_placeholder="stub-public-key",
            transports_or_metadata=request.transports,
        )

        access_token, expires_at = self._generate_access_token()
        self.user_repo.create_session(
            access_token=access_token,
            user_id=user_id,
            device_id=device.device_id,
            expires_at=expires_at,
        )

        self.user_repo.consume_challenge(challenge_row)

        return SessionToken(accessToken=access_token, expiresAt=expires_at)
    
    def finish_login_passkey(self, request: PasskeyFinishRequest) -> SessionToken:
        user_id = request.userHandle or DEFAULT_SIGNIN_USER_ID

        challenge_row = self.user_repo.get_active_challenge(request.challenge, "login")
        if challenge_row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired login challenge",
            )

        if challenge_row.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Challenge does not belong to this user",
            )

        credential_id = request.credentialID
        credential = self.user_repo.get_credential(credential_id)
        if credential is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found",
            )

        device_id = request.deviceID or credential.device_id
        device = self.user_repo.create_or_update_device(
            user_id=user_id,
            device_id=device_id,
            device_name=request.deviceName or f"{user_id} device",
            platform=request.platform or "ios",
        )

        access_token, expires_at = self._generate_access_token()
        self.user_repo.create_session(
            access_token=access_token,
            user_id=user_id,
            device_id=device.device_id,
            expires_at=expires_at,
        )

        self.user_repo.consume_challenge(challenge_row)

        return SessionToken(accessToken=access_token, expiresAt=expires_at)




    def begin_passkey(self) -> PasskeyBeginResponse:
        return self.begin_login_passkey()

    def finish_passkey(self, _request: PasskeyFinishRequest) -> SessionToken:
        return self.finish_login_passkey(_request)
