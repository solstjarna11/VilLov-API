from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SessionToken(BaseModel):
    accessToken: str
    expiresAt: datetime

    model_config = ConfigDict(populate_by_name=True)


class PasskeyBeginRequest(BaseModel):
    userHandle: str | None = None
    deviceID: str | None = None


class PasskeyBeginResponse(BaseModel):
    challenge: str
    relyingPartyID: str
    userID: Optional[str] = None


class PasskeyFinishRequest(BaseModel):
    challenge: str
    credentialID: str
    userHandle: str | None = None
    deviceID: str | None = None
    deviceName: str | None = None
    platform: str | None = None
    transports: str | None = None
    clientDataJSON: str | None = None
    authenticatorData: str | None = None
    signature: str | None = None