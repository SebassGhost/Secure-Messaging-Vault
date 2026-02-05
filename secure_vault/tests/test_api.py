import base64

import pytest
from fastapi.testclient import TestClient

from server import api, db


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


@pytest.fixture()
def client():
    return TestClient(api.app)


def test_create_user_ok(monkeypatch, client):
    monkeypatch.setattr(db, "create_user", lambda public_key, fingerprint: "user-1")
    resp = client.post(
        "/users",
        json={"public_key": "pk", "fingerprint": b64("fp")},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user-1"
    assert resp.json()["key_id"] == "primary"


def test_create_user_invalid_base64(client):
    resp = client.post(
        "/users",
        json={"public_key": "pk", "fingerprint": "%%%"},
    )
    assert resp.status_code == 400


def test_get_user_not_found(monkeypatch, client):
    monkeypatch.setattr(db, "get_user_by_id", lambda user_id: None)
    resp = client.get("/users/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_create_message_invalid_key(monkeypatch, client):
    monkeypatch.setattr(db, "conversation_exists", lambda cid: True)
    monkeypatch.setattr(db, "is_participant", lambda cid, uid: True)
    monkeypatch.setattr(db, "get_active_key", lambda uid, kid: None)

    resp = client.post(
        "/conversations/00000000-0000-0000-0000-000000000000/messages",
        json={
            "sender_id": "00000000-0000-0000-0000-000000000001",
            "ciphertext": b64("ct"),
            "content_hash": b64("ch"),
            "prev_hash": None,
            "signature": b64("sig"),
            "client_timestamp": "2026-02-05T10:00:00Z",
            "key_id": "missing-key",
        },
    )
    assert resp.status_code == 400


def test_message_status_flow(monkeypatch, client):
    monkeypatch.setattr(db, "get_message_conversation_id", lambda mid: "c1")
    monkeypatch.setattr(db, "is_participant", lambda cid, uid: True)
    monkeypatch.setattr(db, "mark_message_delivered", lambda mid, uid: True)
    monkeypatch.setattr(db, "mark_message_read", lambda mid, uid: True)
    monkeypatch.setattr(
        db,
        "get_message_status",
        lambda mid: [{"user_id": "u1", "delivered_at": "t1", "read_at": "t2"}],
    )

    resp = client.post("/messages/00000000-0000-0000-0000-000000000000/delivered", json={"user_id": "00000000-0000-0000-0000-000000000001"})
    assert resp.status_code == 200

    resp = client.post("/messages/00000000-0000-0000-0000-000000000000/read", json={"user_id": "00000000-0000-0000-0000-000000000001"})
    assert resp.status_code == 200

    resp = client.get("/messages/00000000-0000-0000-0000-000000000000/status")
    assert resp.status_code == 200
    assert resp.json()[0]["user_id"] == "u1"


def test_attachments_flow(monkeypatch, client):
    monkeypatch.setattr(db, "get_message_conversation_id", lambda mid: "c1")
    monkeypatch.setattr(db, "is_participant", lambda cid, uid: True)
    monkeypatch.setattr(db, "insert_attachment", lambda **kwargs: ("att-1", "t0"))
    monkeypatch.setattr(
        db,
        "list_attachments",
        lambda mid: [
            {
                "attachment_id": "att-1",
                "uploader_id": "u1",
                "meta_ciphertext": b"meta",
                "meta_hash": b"mh",
                "meta_signature": b"ms",
                "created_at": "t0",
            }
        ],
    )
    monkeypatch.setattr(
        db,
        "get_attachment",
        lambda aid: {
            "attachment_id": "att-1",
            "message_id": "m1",
            "uploader_id": "u1",
            "ciphertext": b"ct",
            "content_hash": b"ch",
            "signature": b"sig",
            "meta_ciphertext": b"meta",
            "meta_hash": b"mh",
            "meta_signature": b"ms",
            "created_at": "t0",
        },
    )

    resp = client.post(
        "/messages/00000000-0000-0000-0000-000000000000/attachments",
        json={
            "uploader_id": "00000000-0000-0000-0000-000000000001",
            "ciphertext": b64("ct"),
            "content_hash": b64("ch"),
            "signature": b64("sig"),
            "meta_ciphertext": b64("meta"),
            "meta_hash": b64("mh"),
            "meta_signature": b64("ms"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["attachment_id"] == "att-1"

    resp = client.get(
        "/messages/00000000-0000-0000-0000-000000000000/attachments",
        params={"user_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert resp.status_code == 200
    assert resp.json()[0]["attachment_id"] == "att-1"

    resp = client.get(
        "/attachments/00000000-0000-0000-0000-000000000000",
        params={"user_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert resp.status_code == 200
    assert resp.json()["attachment_id"] == "att-1"
