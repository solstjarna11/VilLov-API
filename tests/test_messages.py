def test_key_bundle_fetch(client):
    response = client.get(
        "/keys/user_bob/bundle",
        headers={"Authorization": "Bearer dev-token-user_alice"},
    )
    assert response.status_code in (200, 201)

    data = response.json()
    assert data["userID"] == "user_bob"
    assert "identityKey" in data
    assert "signedPrekey" in data


def test_send_inbox_ack_happy_path(client):
    conversation_response = client.post(
        "/conversations/get-or-create",
        headers={"Authorization": "Bearer dev-token-user_alice"},
        json={"recipientUserID": "user_bob"},
    )
    assert conversation_response.status_code in (200, 201)
    conversation_id = conversation_response.json()["conversationID"]

    send_response = client.post(
        "/messages/send",
        headers={"Authorization": "Bearer dev-token-user_alice"},
        json={
            "recipientUserID": "user_bob",
            "messageID": "550e8400-e29b-41d4-a716-446655440000",
            "conversationID": conversation_id,
            "ciphertext": "test-ciphertext",
            "header": "test-header",
            "sentAt": "2026-04-02T18:10:00Z",
        },
    )
    assert send_response.status_code in (200, 201)

    inbox_response = client.get(
        "/messages/inbox",
        headers={"Authorization": "Bearer dev-token-user_bob"},
    )
    assert inbox_response.status_code in (200, 201)
    inbox = inbox_response.json()

    assert len(inbox) >= 1
    message = inbox[0]
    assert message["recipientUserID"] == "user_bob"

    ack_response = client.post(
        "/messages/ack",
        headers={"Authorization": "Bearer dev-token-user_bob"},
        json={"messageID": "550e8400-e29b-41d4-a716-446655440000"},
    )
    assert ack_response.status_code in (200, 201)


def test_unauthorized_inbox_access(client):
    response = client.get("/messages/inbox")
    assert response.status_code == 401