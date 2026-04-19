# app/db/models.py

from datetime import datetime, UTC

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

USERS_USER_ID_FK = "users.user_id"
DEVICES_DEVICE_ID_FK = "devices.device_id"


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    device_name: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey(DEVICES_DEVICE_ID_FK), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    public_key_material_or_placeholder: Mapped[str] = mapped_column(Text, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transports_or_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey(DEVICES_DEVICE_ID_FK), nullable=True, index=True)
    access_token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User")
    device = relationship("Device")


class KeyBundle(Base):
    __tablename__ = "key_bundles"

    user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), primary_key=True)
    identity_key: Mapped[str] = mapped_column(Text, nullable=False)
    signed_prekey: Mapped[str] = mapped_column(Text, nullable=False)
    signed_prekey_signature: Mapped[str] = mapped_column(Text, nullable=False)
    # Deprecated compatibility field. New flows should use OneTimePreKey rows.
    one_time_prekey: Mapped[str | None] = mapped_column(Text, nullable=True)


class OneTimePreKey(Base):
    __tablename__ = "one_time_prekeys"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    prekey_public: Mapped[str] = mapped_column(Text, nullable=False)
    is_consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    flow_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey(DEVICES_DEVICE_ID_FK), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("participant_a_user_id", "participant_b_user_id", name="uq_conversation_participants"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    participant_a_user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    participant_b_user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class MessageEnvelope(Base):
    __tablename__ = "message_envelopes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sender_user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    recipient_user_id: Mapped[str] = mapped_column(ForeignKey(USERS_USER_ID_FK), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    header: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)