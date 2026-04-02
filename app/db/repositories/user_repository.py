from datetime import datetime, UTC, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import TOKEN_TTL_DAYS
from app.db.models import User, AuthSession, AuthChallenge, Device, PasskeyCredential


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user(self, user_id: str) -> User | None:
        statement = select(User).where(User.user_id==user_id)
        return self.db.execute(statement).scalar_one_or_none()
    
    def list_users(self) -> list[User]:
        return list(self.db.scalars(select(User). order_by(User.user_id)).all())
    
    def get_device(self, device_id: str) -> Device | None:
        statement = select(Device).where(Device.device_id == device_id)
        return self.db.execute(statement).scalar_one_or_none()
    
    def create_or_update_device(self,*,user_id: str, device_id: str, device_name: str, platform: str,) -> Device:
        now = datetime.now(UTC)
        device = self.get_device(device_id)
        if device is None:
            device = Device(user_id=user_id, device_id=device_id, device_name=device_name, platform=platform, created_at=now, last_seen_at=now, is_active=True,)
            self.db.add(device)
        else:
            device.user_id=user_id
            device.device_name=device_name
            device.last_seen_at=now
            device.is_active=True
        self.db.commit()
        self.db.refresh(device)
        return device
    
    def get_credential(self, credential_id: str) -> PasskeyCredential | None:
        stmt = select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_credential(self,*,user_id: str,device_id: str,credential_id: str,public_key_material_or_placeholder: str,transports_or_metadata: str | None = None,) -> PasskeyCredential:
        existing = self.get_credential(credential_id)
        if existing is not None:
            return existing

        credential = PasskeyCredential(
            user_id=user_id,
            device_id=device_id,
            credential_id=credential_id,
            public_key_material_or_placeholder=public_key_material_or_placeholder,
            sign_count=0,
            transports_or_metadata=transports_or_metadata,
        )
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        return credential
    
    def create_challenge(self,*,challenge: str,flow_type: str,user_id: str,device_id: str | None,ttl_minutes: int = 10,) -> AuthChallenge:
        now = datetime.now(UTC)
        challenge_row = AuthChallenge(
            challenge=challenge,
            flow_type=flow_type,
            user_id=user_id,
            device_id=device_id,
            created_at=now,
            expires_at=now + timedelta(minutes=ttl_minutes),
            consumed_at=None,
        )
        self.db.add(challenge_row)
        self.db.commit()
        self.db.refresh(challenge_row)
        return challenge_row
    
    def get_active_challenge(self, challenge: str, flow_type: str) -> AuthChallenge | None:
        row = self.db.execute(
            select(AuthChallenge).where(
                AuthChallenge.challenge == challenge,
                AuthChallenge.flow_type == flow_type,
            )
        ).scalar_one_or_none()

        if row is None:
            return None

        now = datetime.now(UTC)
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if row.consumed_at is not None or expires_at <= now:
            return None

        return row
    
    def consume_challenge(self, challenge_row: AuthChallenge) -> None:
        challenge_row.consumed_at = datetime.now(UTC)
        self.db.commit()



    def create_or_update_token(self, access_token: str, user_id: str, expires_at: datetime, device_id: str | None = None,) -> AuthSession:
        session = self.get_session_by_token(access_token)
        if session is None:
            session = AuthSession(user_id=user_id,
                device_id=device_id,
                access_token=access_token,
                expires_at=expires_at,
                created_at=datetime.now(UTC),
                revoked_at=None,)
            self.db.add(session)
        else:
            session.user_id = user_id
            session.device_id = device_id
            session.expires_at = expires_at
            session.revoked_at = None
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def create_session(self,*,access_token: str, user_id: str, device_id: str | None,expires_at: datetime,) -> AuthSession:
        session=AuthSession(access_token=access_token,
            user_id=user_id,
            device_id=device_id,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
            revoked_at=None,)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session_by_token(self, access_token: str) -> AuthSession | None:
        statement = select(AuthSession).where(AuthSession.access_token == access_token)
        return self.db.execute(statement).scalar_one_or_none()

    def get_user_id_by_token(self, access_token: str) -> str | None:
        session = self.get_session_by_token(access_token)
        if session is None:
            return None
        now=datetime.now(UTC)
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if session.revoked_at is not None or expires_at <= now:
            return None

        return session.user_id

    def list_users(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.user_id)).all())
