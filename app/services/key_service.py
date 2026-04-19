# app/services/key_service.py

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

        consumed_opk = self.repo.get_and_consume_one_time_prekey(user_id)

        return RecipientKeyBundle(
            userID=bundle.user_id,
            identityKey=bundle.identity_key,
            identityAgreementKey=bundle.identity_agreement_key,
            signedPrekey=bundle.signed_prekey,
            signedPrekeySignature=bundle.signed_prekey_signature,
            oneTimePrekey=consumed_opk.prekey_public if consumed_opk else bundle.one_time_prekey,
            oneTimePrekeyId=consumed_opk.id if consumed_opk else None,
        )

    def upload_keys(self, request: UploadKeysRequest) -> RecipientKeyBundle:
        legacy_one_time_prekey = request.oneTimePrekey

        bundle = self.repo.upsert(
            user_id=request.userID,
            identity_key=request.identityKey,
            identity_agreement_key=request.identityAgreementKey,
            signed_prekey=request.signedPrekey,
            signed_prekey_signature=request.signedPrekeySignature,
            one_time_prekey=legacy_one_time_prekey,
        )

        if request.oneTimePrekeys:
            self.repo.create_one_time_prekeys(
                user_id=request.userID,
                prekeys=[(item.id, item.publicKey) for item in request.oneTimePrekeys],
            )

        return RecipientKeyBundle(
            userID=bundle.user_id,
            identityKey=bundle.identity_key,
            identityAgreementKey=bundle.identity_agreement_key,
            signedPrekey=bundle.signed_prekey,
            signedPrekeySignature=bundle.signed_prekey_signature,
            oneTimePrekey=bundle.one_time_prekey,
            oneTimePrekeyId=None,
        )