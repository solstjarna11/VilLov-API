from app.db.models import KeyBundle, OneTimePreKey


def test_authenticated_key_upload_succeeds(client, db_session):
    alice = register_and_authenticate_user(client, "alice")

    payload = make_key_upload_request("alice", opk_count=2)
    response = client.post(
        "/keys/upload",
        json=payload,
        headers=auth_headers(alice["access_token"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["userID"] == "alice"
    assert body["identityKey"] == payload["identityKey"]
    assert body["identityAgreementKey"] == payload["identityAgreementKey"]
    assert body["signedPrekey"] == payload["signedPrekey"]
    assert body["signedPrekeySignature"] == payload["signedPrekeySignature"]

    stored_bundle = db_session.get(KeyBundle, "alice")
    assert stored_bundle is not None
    assert stored_bundle.identity_key == payload["identityKey"]
    assert stored_bundle.identity_agreement_key == payload["identityAgreementKey"]
    assert stored_bundle.signed_prekey == payload["signedPrekey"]
    assert stored_bundle.signed_prekey_signature == payload["signedPrekeySignature"]

    stored_opks = (
        db_session.query(OneTimePreKey)
        .filter(OneTimePreKey.user_id == "alice")
        .all()
    )
    assert len(stored_opks) == 2
    assert all(not row.is_consumed for row in stored_opks)


def test_fetch_bundle_for_another_user_returns_bundle_and_consumes_one_opk(client, db_session):
    alice = register_and_authenticate_user(client, "alice")
    bob = register_and_authenticate_user(client, "bob")

    upload_payload = make_key_upload_request("alice", opk_count=3)
    upload_resp = client.post(
        "/keys/upload",
        json=upload_payload,
        headers=auth_headers(alice["access_token"]),
    )
    assert upload_resp.status_code == 200, upload_resp.text

    fetch_resp = client.get(
        "/keys/alice/bundle",
        headers=auth_headers(bob["access_token"]),
    )
    assert fetch_resp.status_code == 200, fetch_resp.text
    bundle = fetch_resp.json()

    assert bundle["userID"] == "alice"
    assert bundle["identityKey"] == upload_payload["identityKey"]
    assert bundle["identityAgreementKey"] == upload_payload["identityAgreementKey"]
    assert bundle["signedPrekey"] == upload_payload["signedPrekey"]
    assert bundle["signedPrekeySignature"] == upload_payload["signedPrekeySignature"]
    assert bundle["oneTimePrekey"] is not None
    assert bundle["oneTimePrekeyId"] is not None

    consumed = (
        db_session.query(OneTimePreKey)
        .filter(
            OneTimePreKey.user_id == "alice",
            OneTimePreKey.id == bundle["oneTimePrekeyId"],
        )
        .one()
    )
    assert consumed.is_consumed is True
    assert consumed.consumed_at is not None


def test_unauthorized_upload_for_another_user_is_rejected(client):
    alice = register_and_authenticate_user(client, "alice")
    bob = register_and_authenticate_user(client, "bob")

    payload = make_key_upload_request("alice", opk_count=1)
    response = client.post(
        "/keys/upload",
        json=payload,
        headers=auth_headers(bob["access_token"]),
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Cannot upload keys for another user"


def test_opk_is_consumed_exactly_once_across_multiple_fetches(client, db_session):
    alice = register_and_authenticate_user(client, "alice")
    bob = register_and_authenticate_user(client, "bob")

    payload = make_key_upload_request("alice", opk_count=2)
    upload_resp = client.post(
        "/keys/upload",
        json=payload,
        headers=auth_headers(alice["access_token"]),
    )
    assert upload_resp.status_code == 200, upload_resp.text

    fetch_1 = client.get("/keys/alice/bundle", headers=auth_headers(bob["access_token"]))
    fetch_2 = client.get("/keys/alice/bundle", headers=auth_headers(bob["access_token"]))

    assert fetch_1.status_code == 200, fetch_1.text
    assert fetch_2.status_code == 200, fetch_2.text

    bundle_1 = fetch_1.json()
    bundle_2 = fetch_2.json()

    assert bundle_1["oneTimePrekeyId"] is not None
    assert bundle_2["oneTimePrekeyId"] is not None
    assert bundle_1["oneTimePrekeyId"] != bundle_2["oneTimePrekeyId"]

    consumed_rows = (
        db_session.query(OneTimePreKey)
        .filter(
            OneTimePreKey.user_id == "alice",
            OneTimePreKey.is_consumed.is_(True),
        )
        .all()
    )
    assert len(consumed_rows) == 2

    consumed_ids = {row.id for row in consumed_rows}
    assert bundle_1["oneTimePrekeyId"] in consumed_ids
    assert bundle_2["oneTimePrekeyId"] in consumed_ids


def test_bundle_fetch_still_works_after_opk_exhaustion_with_fallback_shape(client):
    alice = register_and_authenticate_user(client, "alice")
    bob = register_and_authenticate_user(client, "bob")

    payload = make_key_upload_request("alice", opk_count=1)
    upload_resp = client.post(
        "/keys/upload",
        json=payload,
        headers=auth_headers(alice["access_token"]),
    )
    assert upload_resp.status_code == 200, upload_resp.text

    first_fetch = client.get("/keys/alice/bundle", headers=auth_headers(bob["access_token"]))
    second_fetch = client.get("/keys/alice/bundle", headers=auth_headers(bob["access_token"]))

    assert first_fetch.status_code == 200, first_fetch.text
    assert second_fetch.status_code == 200, second_fetch.text

    first_bundle = first_fetch.json()
    second_bundle = second_fetch.json()

    assert first_bundle["oneTimePrekey"] is not None
    assert first_bundle["oneTimePrekeyId"] is not None

    assert second_bundle["identityKey"] == payload["identityKey"]
    assert second_bundle["identityAgreementKey"] == payload["identityAgreementKey"]
    assert second_bundle["signedPrekey"] == payload["signedPrekey"]
    assert second_bundle["signedPrekeySignature"] == payload["signedPrekeySignature"]
    assert second_bundle["oneTimePrekey"] is None
    assert second_bundle["oneTimePrekeyId"] is None


def test_opk_count_endpoint_reports_remaining_inventory(client):
    alice = register_and_authenticate_user(client, "alice")
    bob = register_and_authenticate_user(client, "bob")

    payload = make_key_upload_request("alice", opk_count=3)
    upload_resp = client.post(
        "/keys/upload",
        json=payload,
        headers=auth_headers(alice["access_token"]),
    )
    assert upload_resp.status_code == 200, upload_resp.text

    count_before = client.get(
        "/keys/me/opk-count",
        headers=auth_headers(alice["access_token"]),
    )
    assert count_before.status_code == 200, count_before.text
    assert count_before.json()["remaining"] == 3

    fetch_resp = client.get(
        "/keys/alice/bundle",
        headers=auth_headers(bob["access_token"]),
    )
    assert fetch_resp.status_code == 200, fetch_resp.text

    count_after = client.get(
        "/keys/me/opk-count",
        headers=auth_headers(alice["access_token"]),
    )
    assert count_after.status_code == 200, count_after.text
    assert count_after.json()["remaining"] == 2