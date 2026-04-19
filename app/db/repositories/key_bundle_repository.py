# app/db/repositories/key_bundle_repository.py

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import KeyBundle, OneTimePreKey


class KeyBundleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: str) -> KeyBundle | None:
        return self.db.get(KeyBundle, user_id)

    def upsert(
        self,
        user_id: str,
        identity_key: str,
        identity_agreement_key: str,
        signed_prekey: str,
        signed_prekey_signature: str,
        one_time_prekey: str | None,
    ) -> KeyBundle:
        bundle = self.db.get(KeyBundle, user_id)
        if bundle is None:
            bundle = KeyBundle(
                user_id=user_id,
                identity_key=identity_key,
                identity_agreement_key=identity_agreement_key,
                signed_prekey=signed_prekey,
                signed_prekey_signature=signed_prekey_signature,
                one_time_prekey=one_time_prekey,
            )
            self.db.add(bundle)
        else:
            bundle.identity_key = identity_key
            bundle.identity_agreement_key = identity_agreement_key
            bundle.signed_prekey = signed_prekey
            bundle.signed_prekey_signature = signed_prekey_signature
            # Keep legacy compatibility behavior only.
            bundle.one_time_prekey = one_time_prekey

        self.db.commit()
        self.db.refresh(bundle)
        return bundle

    def create_one_time_prekeys(
        self,
        user_id: str,
        prekeys: list[tuple[str, str]],
    ) -> None:
        if not prekeys:
            return

        rows = [
            OneTimePreKey(
                id=prekey_id,
                user_id=user_id,
                prekey_public=public_key,
                is_consumed=False,
            )
            for prekey_id, public_key in prekeys
        ]
        self.db.add_all(rows)
        self.db.commit()

    def get_and_consume_one_time_prekey(self, user_id: str) -> OneTimePreKey | None:
        stmt = (
            select(OneTimePreKey)
            .where(
                OneTimePreKey.user_id == user_id,
                OneTimePreKey.is_consumed.is_(False),
            )
            .order_by(OneTimePreKey.created_at.asc())
            .with_for_update(skip_locked=True)
        )

        with self.db.begin():
            row = self.db.execute(stmt).scalar_one_or_none()
            if row is None:
                return None

            row.is_consumed = True
            row.consumed_at = datetime.now(UTC)
            self.db.flush()
            self.db.refresh(row)
            return row

    def count_remaining_one_time_prekeys(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(OneTimePreKey).where(
            OneTimePreKey.user_id == user_id,
            OneTimePreKey.is_consumed.is_(False),
        )
        return int(self.db.execute(stmt).scalar_one())