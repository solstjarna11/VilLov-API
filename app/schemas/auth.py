from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SessionToken(BaseModel):
    accessToken: str
    expiresAt: datetime

    model_config = ConfigDict(populate_by_name=True)


class PasskeyBeginRequest(BaseModel):
    pass


class PasskeyBeginResponse(BaseModel):
    challenge: str
    relyingPartyID: str
    userID: Optional[str] = None


class PasskeyFinishRequest(BaseModel):
    credentialID: str
    clientDataJSON: str
    authenticatorData: str
    signature: str
    userHandle: Optional[str] = None
