from sqlalchemy.orm import Session

from app.db.repositories.key_bundle_repository import KeyBundleRepository
from app.schemas.keys import RecipientKeyBundle, UploadKeysRequest


class KeyService:
    def __init__(self, db: Session) -> None:
        self.repo = KeyBundleRepository(db)

    def get_bundle(self, user_id: str) -> RecipientKeyBundle | None:
        bundle = self.repo.get(user_id)
        if bundle is None:
            return None
        return RecipientKeyBundle(
            userID=bundle.user_id,
            identityKey=bundle.identity_key,
            signedPrekey=bundle.signed_prekey,
            signedPrekeySignature=bundle.signed_prekey_signature,
            oneTimePrekey=bundle.one_time_prekey,
        )

    def upload_keys(self, request: UploadKeysRequest) -> RecipientKeyBundle:
        bundle = self.repo.upsert(
            user_id=request.userID,
            identity_key=request.identityKey,
            signed_prekey=request.signedPrekey,
            signed_prekey_signature=request.signedPrekeySignature,
            one_time_prekey=request.oneTimePrekey,
        )
        return RecipientKeyBundle(
            userID=bundle.user_id,
            identityKey=bundle.identity_key,
            signedPrekey=bundle.signed_prekey,
            signedPrekeySignature=bundle.signed_prekey_signature,
            oneTimePrekey=bundle.one_time_prekey,
        )
