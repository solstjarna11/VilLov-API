from sqlalchemy.orm import Session

from app.db.models import KeyBundle


class KeyBundleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: str) -> KeyBundle | None:
        return self.db.get(KeyBundle, user_id)

    def upsert(
        self,
        user_id: str,
        identity_key: str,
        signed_prekey: str,
        signed_prekey_signature: str,
        one_time_prekey: str | None,
    ) -> KeyBundle:
        bundle = self.db.get(KeyBundle, user_id)
        if bundle is None:
            bundle = KeyBundle(
                user_id=user_id,
                identity_key=identity_key,
                signed_prekey=signed_prekey,
                signed_prekey_signature=signed_prekey_signature,
                one_time_prekey=one_time_prekey,
            )
            self.db.add(bundle)
        else:
            bundle.identity_key = identity_key
            bundle.signed_prekey = signed_prekey
            bundle.signed_prekey_signature = signed_prekey_signature
            bundle.one_time_prekey = one_time_prekey
        self.db.commit()
        self.db.refresh(bundle)
        return bundle
