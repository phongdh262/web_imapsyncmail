import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, get_db
from database import Base, Job, Mailbox

# Setup test database (SQLite in-memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()
# from .main import app # Removed
# from .database import get_db # Removed
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def test_user():
    db = TestingSessionLocal()
    from .auth import get_password_hash
    from .database import User
    user = User(username="testadmin", hashed_password=get_password_hash("password123"))
    db.add(user)
    db.commit()
    yield user
    db.close()

def test_create_job_mandatory_password():
    # Test creating job without password (should fail validation)
    response = client.post(
        "/api/jobs",
        json={
            "name": "Test Job No PW",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "source_port": 993,
            "target_port": 993,
            "source_security": "SSL/TLS",
            "target_security": "SSL/TLS",
            "options": {}
            # Missing password
        }
    )
    assert response.status_code == 422 # Unprocessable Entity (Missing field)

    # Test creating job with password (should succeed)
    response = client.post(
        "/api/jobs",
        json={
            "name": "Test Job With PW",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "source_port": 993,
            "target_port": 993,
            "source_security": "SSL/TLS",
            "target_security": "SSL/TLS",
            "options": {},
            "password": "secretpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Job With PW"
    assert "id" in data

def test_job_password_protection():
    # 1. Create a protected job
    # Use a fresh client to avoid cookie pollution
    auth_client = TestClient(app)
    create_res = auth_client.post(
        "/api/jobs",
        json={
            "name": "Protected Job",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "strongpassword"
        }
    )
    job_id = create_res.json()["id"]

    # 2. Try fetching without password using a NEW client (no cookies)
    no_auth_client = TestClient(app)
    response = no_auth_client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Password required"

    # 3. Try fetching with WRONG password
    response = no_auth_client.get(f"/api/jobs/{job_id}?password=wrongpassword")
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect password"

    # 4. Try fetching with CORRECT password (Query Param)
    response = no_auth_client.get(f"/api/jobs/{job_id}?password=strongpassword")
    assert response.status_code == 200
    assert response.json()["name"] == "Protected Job"

def test_verify_password_endpoint():
    # Create protected job
    create_res = client.post(
        "/api/jobs",
        json={
            "name": "Verify Job",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "testpwd"
        }
    )
    job_id = create_res.json()["id"]

    # Verify correct password using the /verify endpoint
    response = client.post(f"/api/jobs/{job_id}/verify", json={"password": "testpwd"})
    assert response.status_code == 200
    assert response.json()["valid"] is True

    # Verify incorrect password
    response = client.post(f"/api/jobs/{job_id}/verify", json={"password": "wrong"})
    assert response.status_code == 401

def test_mailbox_management():
    # Create job
    create_res = client.post(
        "/api/jobs",
        json={
            "name": "Mailbox Job",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "pwd"
        }
    )
    job_id = create_res.json()["id"]

    # Add mailbox
    response = client.post(
        f"/api/jobs/{job_id}/mailboxes",
        json={
            "source_user": "user1@test.com",
            "source_pass": "p1",
            "target_user": "u1@target.com",
            "target_pass": "p2"
        }
    )
    assert response.status_code == 200
    assert "mailbox_id" in response.json()

    # Fetch job details (authenticated) to see mailbox
    response = client.get(f"/api/jobs/{job_id}?password=pwd")
    assert response.status_code == 200
    job_data = response.json()
    assert job_data["total"] == 1 # The field is "total" in the response, not "total_mailboxes"


def test_stats_api(test_user):
    # Stats API is now public, no auth required
    res = client.get("/api/stats")
    assert res.status_code == 200
    assert "total_jobs" in res.json()
    assert "active_jobs" in res.json()
    assert "completed_mailboxes" in res.json()
    assert "data_transferred" in res.json()

def test_delete_all_jobs():
    create_res = client.post("/api/jobs", json={"name": "ToDelete", "source_host": "h1", "target_host": "h2", "password": "p"})
    job_id = create_res.json()["id"]
    
    # Force status to 'completed' so it can be deleted
    db = TestingSessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = "completed"
    db.commit()
    db.close()
    
    response = client.delete("/api/jobs")
    assert response.status_code == 200
    
    # Check if empty
    list_res = client.get("/api/jobs")
    assert len(list_res.json()) == 0

def test_delete_blocked_when_running():
    # 1. Create a job and manually set its status to running in DB
    create_res = client.post(
        "/api/jobs", 
        json={"name": "RunningJob", "source_host": "h1", "target_host": "h2", "password": "p"}
    )
    job_id = create_res.json()["id"]
    
    # Force status to 'running'
    db = TestingSessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = "running"
    db.commit()
    db.close()
    
    # 2. Try deleting - should be blocked
    response = client.delete("/api/jobs")
    assert response.status_code == 400
    assert "Cannot delete history" in response.json()["detail"]
    
    # 3. Force status to 'completed'
    db = TestingSessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = "completed"
    db.commit()
    db.close()
    
    # 4. Try deleting - should succeed now
    response = client.delete("/api/jobs")
    assert response.status_code == 200

def test_delete_single_job():
    # 1. Create a job
    create_res = client.post(
        "/api/jobs", 
        json={"name": "SingleDeleteJob", "source_host": "h1", "target_host": "h2", "password": "p"}
    )
    job_id = create_res.json()["id"]
    
    # 2. Add a mailbox
    client.post(f"/api/jobs/{job_id}/mailboxes", json={
        "source_user": "u1", "source_pass": "p1", "target_user": "u2", "target_pass": "p2"
    })
    
    # 3. Try deleting while 'running' (default state) - should be blocked
    response = client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 400
    
    # 4. Set to 'completed'
    db = TestingSessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = "completed"
    db.commit()
    db.close()
    
    # 5. Delete successfully
    response = client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    
    # 6. Verify records are gone
    list_res = client.get("/api/jobs")
    assert not any(j["id"] == job_id for j in list_res.json())
    
    db = TestingSessionLocal()
    mailboxes = db.query(Mailbox).filter(Mailbox.job_id == job_id).all()
    assert len(mailboxes) == 0
    db.close()

def test_mailbox_stop_retry():
    # 1. Setup job and mailbox
    create_res = client.post("/api/jobs", json={"name": "ActionJob", "source_host": "h1", "target_host": "h2", "password": "p"})
    job_id = create_res.json()["id"]
    mb_res = client.post(f"/api/jobs/{job_id}/mailboxes", json={
        "source_user": "u1", "source_pass": "p1", "target_user": "u2", "target_pass": "p2"
    })
    mb_id = mb_res.json()["mailbox_id"]

    # 2. Test Stop
    stop_res = client.post(f"/api/mailboxes/{mb_id}/stop")
    assert stop_res.status_code == 200
    
    # 3. Test Retry
    retry_res = client.post(f"/api/mailboxes/{mb_id}/retry")
    assert retry_res.status_code == 200
    assert retry_res.json()["message"] == "Mailbox retry started"

def test_invalid_log_access():
    # Test logs for non-existent mailbox
    response = client.get("/api/mailboxes/9999/logs")
    assert response.status_code == 404

def test_protected_log_access():
    # 1. Create protected job
    create_res = client.post("/api/jobs", json={"name": "LogJob", "source_host": "h1", "target_host": "h2", "password": "secure"})
    job_id = create_res.json()["id"]
    mb_res = client.post(f"/api/jobs/{job_id}/mailboxes", json={
        "source_user": "u1", "source_pass": "p1", "target_user": "u2", "target_pass": "p2"
    })
    mb_id = mb_res.json()["mailbox_id"]

    # 2. Try fetching logs without password
    no_auth_client = TestClient(app)
    response = no_auth_client.get(f"/api/mailboxes/{mb_id}/logs")
    assert response.status_code == 401
    
    # 3. Try fetching with correct password (Query)
    response = no_auth_client.get(f"/api/mailboxes/{mb_id}/logs?password=secure")
    assert response.status_code == 200
    assert "logs" in response.json()
def test_login_and_auth(test_user):
    # 1. Test Login
    response = client.post(
        "/api/login",
        data={"username": "testadmin", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token is not None

    # 2. Test Stats API (now public, no auth needed)
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    assert "total_jobs" in res_stats.json()

def test_csv_upload():
    # 1. Create a job
    create_res = client.post(
        "/api/jobs",
        json={"name": "CSV Job", "source_host": "h1", "target_host": "h2", "password": "p"}
    )
    job_id = create_res.json()["id"]

    # 2. Upload CSV
    csv_content = (
        "source1@gmail.com,pass1,target1@dest.com,tpass1\n"
        "source2@gmail.com,pass2,target2@dest.com,tpass2\n"
    )
    files = {"file": ("test.csv", csv_content, "text/csv")}
    response = client.post(f"/api/upload/{job_id}", files=files)
    
    assert response.status_code == 200
    assert "Started 2 mailboxes" in response.json()["message"]

    # 3. Verify mailboxes in DB
    db = TestingSessionLocal()
    mbs = db.query(Mailbox).filter(Mailbox.job_id == job_id).all()
    assert len(mbs) == 2
    assert mbs[0].source_user == "source1@gmail.com"
    db.close()

def test_advanced_password_verification():
    # Test that different ways of providing job password work
    create_res = client.post("/api/jobs", json={"name": "AuthTest", "source_host": "h1", "target_host": "h2", "password": "secret"})
    job_id = create_res.json()["id"]

    # Header auth
    res_header = client.get(f"/api/jobs/{job_id}", headers={"X-Job-Password": "secret"})
    assert res_header.status_code == 200

    # Cookie auth (Playwright/Browser logic simulation)
    client.cookies.set("job_password", "secret")
    res_cookie = client.get(f"/api/jobs/{job_id}")
    assert res_cookie.status_code == 200
    client.cookies.clear()
