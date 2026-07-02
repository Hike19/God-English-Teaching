from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def test_submit_feedback():
    import uuid
    username = f"fb_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": username, "password": "test123"})
    token = resp.json()["access_token"]

    resp2 = client.post(
        "/api/feedback",
        json={"content": "Great app!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 201
    assert resp2.json()["content"] == "Great app!"
    assert resp2.json()["user_id"] is not None


def test_feedback_requires_auth():
    resp = client.post("/api/feedback", json={"content": "test"})
    assert resp.status_code == 401
