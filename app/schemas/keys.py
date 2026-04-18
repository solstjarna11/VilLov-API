# app/schemas/keys.py

from typing import Optional

from pydantic import BaseModel


class RecipientKeyBundle(BaseModel):
    userID: str
    identityKey: str
    signedPrekey: str
    signedPrekeySignature: str
    oneTimePrekey: Optional[str] = None


class UploadKeysRequest(BaseModel):
    userID: str
    identityKey: str
    signedPrekey: str
    signedPrekeySignature: str
    oneTimePrekey: Optional[str] = None
