import io
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def _auth_header() -> dict:
    import uuid
    username = f"int_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": username, "password": "test123"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_register_and_login():
    import uuid
    username = f"flow_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": username, "password": "test123"})
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    resp2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["username"] == username


def test_feedback_flow():
    headers = _auth_header()
    resp = client.post("/api/feedback", json={"content": "Great!"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["content"] == "Great!"


def test_task_list_flow():
    headers = _auth_header()
    resp = client.get("/api/tasks", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_upload_and_get_task():
    headers = _auth_header()

    test_file = io.BytesIO(b"\x00" * 1024)
    resp = client.post(
        "/api/tasks/upload",
        files={"file": ("test.mp3", test_file, "audio/mpeg")},
        headers=headers,
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]
    assert resp.json()["status"] in ("processing", "done", "failed")

    resp2 = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == task_id

    resp3 = client.delete(f"/api/tasks/{task_id}", headers=headers)
    assert resp3.status_code == 204

    resp4 = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert resp4.status_code == 404


def test_upload_invalid_extension():
    headers = _auth_header()
    test_file = io.BytesIO(b"test")
    resp = client.post(
        "/api/tasks/upload",
        files={"file": ("test.exe", test_file, "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_url_submit():
    headers = _auth_header()
    resp = client.post(
        "/api/tasks/url",
        data={"url": "https://example.com/test.mp3"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "processing"
