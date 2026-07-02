from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)
Base.metadata.create_all(bind=engine)


def _register_and_get_token() -> str:
    import uuid
    username = f"test_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/auth/register", json={"username": username, "password": "test123"})
    return resp.json()["access_token"]


def test_task_list_empty():
    token = _register_and_get_token()
    resp = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_task_list_requires_auth():
    resp = client.get("/api/tasks")
    assert resp.status_code == 401


def test_get_task_not_found():
    token = _register_and_get_token()
    resp = client.get("/api/tasks/99999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
