"""
Shared fixtures for the ImapSync Pro test suite.

Provides:
- In-memory SQLite database (no MySQL required)
- FastAPI TestClient with DB override
- Authenticated admin client with CSRF tokens
- Clean DB state per test
"""
import os
import sys
import pytest

# Ensure backend modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment BEFORE any backend imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")
os.environ.setdefault("ADMIN_USERNAME", "phongdh")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Provide a transactional DB session that rolls back after test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session):
    """Unauthenticated TestClient with DB override."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle managed by fixture

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client(client):
    """
    Authenticated TestClient — logs in as root admin,
    returns (client, csrf_token) tuple.
    """
    # Login as admin
    response = client.post(
        "/api/login",
        data={"username": "phongdh", "password": "testadmin123"},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"

    # Extract CSRF token from response cookies
    csrf_token = response.cookies.get("csrf_token", "")

    # The session cookie is auto-stored in client.cookies
    return client, csrf_token


# ---------------------------------------------------------------------------
# Helper: create a job via API
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_job(admin_client):
    """Create a sample job and return (client, csrf_token, job_id, job_password)."""
    client, csrf = admin_client
    job_password = "jobpass1234"

    resp = client.post(
        "/api/jobs",
        json={
            "name": "Test Migration",
            "source_host": "imap.gmail.com",
            "target_host": "imap.yandex.com",
            "source_port": 993,
            "target_port": 993,
            "source_security": "SSL/TLS",
            "target_security": "SSL/TLS",
            "options": {},
            "password": job_password,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, f"Job creation failed: {resp.text}"
    job_id = resp.json()["id"]
    return client, csrf, job_id, job_password
