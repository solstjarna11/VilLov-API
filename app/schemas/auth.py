# app/schemas/auth.py

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


class PasskeyRegistrationBeginResponse(BaseModel):
    challenge: str
    relyingPartyID: str
    userID: str
    userName: str
    displayName: str


class PasskeyAssertionBeginResponse(BaseModel):
    challenge: str
    relyingPartyID: str
    userID: Optional[str] = None


class PasskeyRegistrationFinishRequest(BaseModel):
    challenge: str
    credentialID: str
    userHandle: str | None = None
    deviceID: str | None = None
    deviceName: str | None = None
    platform: str | None = None
    transports: list[str] | None = None
    clientDataJSON: str
    attestationObject: str


class PasskeyAssertionFinishRequest(BaseModel):
    challenge: str
    credentialID: str
    userHandle: str | None = None
    deviceID: str | None = None
    deviceName: str | None = None
    platform: str | None = None
    transports: list[str] | None = None
    clientDataJSON: str
    authenticatorData: str
    signature: str


# Optional legacy aliases if we want to keep older route code compiling temporarily
PasskeyBeginResponse = PasskeyAssertionBeginResponse
PasskeyFinishRequest = PasskeyAssertionFinishRequest