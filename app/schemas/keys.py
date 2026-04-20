# app/schemas/keys.py

from typing import Optional

from pydantic import BaseModel, Field


class OneTimePreKeyUpload(BaseModel):
    id: str
    publicKey: str


class RecipientKeyBundle(BaseModel):
    userID: str
    identityKey: str
    identityAgreementKey: str
    signedPrekeyId: str
    signedPrekey: str
    signedPrekeySignature: str
    oneTimePrekey: Optional[str] = None
    oneTimePrekeyId: Optional[str] = None


class UploadKeysRequest(BaseModel):
    userID: str
    identityKey: str
    identityAgreementKey: str
    signedPrekeyId: str
    signedPrekey: str
    signedPrekeySignature: str

    # New preferred field
    oneTimePrekeys: list[OneTimePreKeyUpload] = Field(default_factory=list)

    # Backward-compatible legacy field
    oneTimePrekey: Optional[str] = None


class OneTimePreKeyCountResponse(BaseModel):
    remaining: int