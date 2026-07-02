from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)

# Setup: create tables
Base.metadata.create_all(bind=engine)


def test_register_and_login():
    # Register
    resp = client.post("/api/auth/register", json={"username": "authtest", "password": "test123"})
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "authtest"

    # Duplicate register
    resp2 = client.post("/api/auth/register", json={"username": "authtest", "password": "test123"})
    assert resp2.status_code == 400

    # Login
    resp3 = client.post("/api/auth/login", json={"username": "authtest", "password": "test123"})
    assert resp3.status_code == 200
    assert "access_token" in resp3.json()

    # Bad login
    resp4 = client.post("/api/auth/login", json={"username": "authtest", "password": "wrong"})
    assert resp4.status_code == 401

    # Me
    token = resp3.json()["access_token"]
    resp5 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp5.status_code == 200
    assert resp5.json()["username"] == "authtest"

    # Me without token
    resp6 = client.get("/api/auth/me")
    assert resp6.status_code == 401
