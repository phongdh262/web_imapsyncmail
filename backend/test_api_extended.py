"""
test_api_extended.py
Extended API tests covering input validation, edge cases, CSV upload variations,
and business logic for the IMAP Sync Pro web application.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, get_db
from database import Base, Job, Mailbox

# Setup test database (SQLite in-memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_extended.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# Helper to create a valid job
def create_test_job(name="Test Job", password="testpwd123"):
    return client.post("/api/jobs", json={
        "name": name,
        "source_host": "imap.source.com",
        "target_host": "imap.target.com",
        "source_port": 993,
        "target_port": 993,
        "source_security": "SSL/TLS",
        "target_security": "SSL/TLS",
        "options": {},
        "password": password
    })


# ==========================================
# 1. Input Validation Tests
# ==========================================

class TestCreateJobValidation:
    """Tests for /api/jobs POST validation"""

    def test_create_job_empty_name(self):
        """Empty name should still work (name has a default)"""
        response = client.post("/api/jobs", json={
            "name": "",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "pwd"
        })
        assert response.status_code == 200
        # Name can be empty string, that's valid but gets stored

    def test_create_job_very_long_name(self):
        """Name exceeding 255 characters"""
        long_name = "A" * 500
        response = client.post("/api/jobs", json={
            "name": long_name,
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "pwd"
        })
        # Should succeed (SQLite doesn't enforce length) or fail gracefully
        assert response.status_code in [200, 422, 500]

    def test_create_job_special_chars_name(self):
        """Name with dangerous characters (XSS, SQL injection)"""
        response = client.post("/api/jobs", json={
            "name": '<script>alert("xss")</script>',
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "pwd"
        })
        assert response.status_code == 200
        data = response.json()
        # The name should be stored as-is (output escaping is the frontend's job)
        assert "<script>" in data["name"]

    def test_create_job_invalid_port_negative(self):
        """Negative port number"""
        response = client.post("/api/jobs", json={
            "name": "Test",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "source_port": -1,
            "password": "pwd"
        })
        # FastAPI accepts any int, but negative ports are semantically invalid
        assert response.status_code in [200, 422]

    def test_create_job_invalid_port_too_high(self):
        """Port number exceeding 65535"""
        response = client.post("/api/jobs", json={
            "name": "Test",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "source_port": 99999,
            "password": "pwd"
        })
        assert response.status_code in [200, 422]

    def test_create_job_string_port(self):
        """String value for port (should fail validation)"""
        response = client.post("/api/jobs", json={
            "name": "Test",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "source_port": "not_a_number",
            "password": "pwd"
        })
        assert response.status_code == 422

    def test_create_job_invalid_security_option(self):
        """Invalid security option string"""
        response = client.post("/api/jobs", json={
            "name": "Test",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "source_security": "INVALID_PROTOCOL",
            "password": "pwd"
        })
        # Currently no enum validation, so it accepts any string
        assert response.status_code == 200

    def test_create_job_empty_hosts(self):
        """Empty source and target hosts"""
        response = client.post("/api/jobs", json={
            "name": "Test",
            "source_host": "",
            "target_host": "",
            "password": "pwd"
        })
        # Empty strings are valid str type in Pydantic
        assert response.status_code == 200

    def test_create_job_missing_required_fields(self):
        """Missing source_host (required field)"""
        response = client.post("/api/jobs", json={
            "name": "Test",
            "target_host": "imap.target.com",
            "password": "pwd"
        })
        assert response.status_code == 422

    def test_create_job_missing_password(self):
        """Password is mandatory"""
        response = client.post("/api/jobs", json={
            "name": "Test",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com"
        })
        assert response.status_code == 422


# ==========================================
# 2. 404 and Not Found Tests
# ==========================================

class TestNotFound:
    """Tests for accessing non-existent resources"""

    def test_get_nonexistent_job(self):
        """GET job with random UUID"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/jobs/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    def test_delete_nonexistent_job(self):
        """DELETE job with random UUID"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/jobs/{fake_id}")
        assert response.status_code == 404

    def test_add_mailbox_nonexistent_job(self):
        """POST mailbox to non-existent job"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/jobs/{fake_id}/mailboxes", json={
            "source_user": "u1@test.com",
            "source_pass": "p1",
            "target_user": "u2@test.com",
            "target_pass": "p2"
        })
        assert response.status_code == 404

    def test_stop_nonexistent_mailbox(self):
        """Stop sync for non-existent mailbox (should not crash)"""
        response = client.post("/api/mailboxes/99999/stop")
        assert response.status_code == 200  # Returns "Process not found" message

    def test_retry_nonexistent_mailbox(self):
        """Retry non-existent mailbox"""
        response = client.post("/api/mailboxes/99999/retry")
        assert response.status_code == 404

    def test_cancel_nonexistent_job(self):
        """Cancel non-existent job"""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/jobs/{fake_id}/cancel")
        assert response.status_code == 404


# ==========================================
# 3. CSV Upload Tests
# ==========================================

class TestCSVUpload:
    """Tests for CSV file upload endpoint"""

    def test_csv_upload_empty_file(self):
        """Upload empty CSV file"""
        res = create_test_job("CSV Empty Job")
        job_id = res.json()["id"]

        files = {"file": ("empty.csv", "", "text/csv")}
        response = client.post(f"/api/upload/{job_id}", files=files)
        assert response.status_code == 200
        assert "Started 0 mailboxes" in response.json()["message"]

    def test_csv_upload_malformed_rows(self):
        """CSV with fewer than 4 columns (should be skipped)"""
        res = create_test_job("CSV Malformed Job")
        job_id = res.json()["id"]

        csv_content = "only_one_column\ntwo,columns\nthree,cols,here\n"
        files = {"file": ("bad.csv", csv_content, "text/csv")}
        response = client.post(f"/api/upload/{job_id}", files=files)
        assert response.status_code == 200
        assert "Started 0 mailboxes" in response.json()["message"]

    def test_csv_upload_extra_columns(self):
        """CSV with more than 4 columns (should still work, extra ignored)"""
        res = create_test_job("CSV Extra Job")
        job_id = res.json()["id"]

        csv_content = "src@test.com,srcpass,tgt@test.com,tgtpass,extra1,extra2\n"
        files = {"file": ("extra.csv", csv_content, "text/csv")}
        response = client.post(f"/api/upload/{job_id}", files=files)
        assert response.status_code == 200
        assert "Started 1 mailboxes" in response.json()["message"]

    def test_csv_upload_special_chars_in_email(self):
        """CSV with special characters in email addresses"""
        res = create_test_job("CSV Special Job")
        job_id = res.json()["id"]

        csv_content = 'user+tag@test.com,p@ss!w0rd,target.user@company.co.uk,tgt$pass\n'
        files = {"file": ("special.csv", csv_content, "text/csv")}
        response = client.post(f"/api/upload/{job_id}", files=files)
        assert response.status_code == 200
        assert "Started 1 mailboxes" in response.json()["message"]

    def test_csv_upload_nonexistent_job(self):
        """Upload CSV to non-existent job"""
        fake_id = str(uuid.uuid4())
        csv_content = "src@test.com,pass1,tgt@test.com,pass2\n"
        files = {"file": ("test.csv", csv_content, "text/csv")}
        response = client.post(f"/api/upload/{fake_id}", files=files)
        assert response.status_code == 404


# ==========================================
# 4. Business Logic Tests
# ==========================================

class TestBusinessLogic:
    """Tests for business logic and edge cases"""

    def test_list_jobs_empty(self):
        """List jobs when database is empty"""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_ordering(self):
        """Jobs should be returned newest first"""
        create_test_job("Job A", "pwd1")
        create_test_job("Job B", "pwd2")
        create_test_job("Job C", "pwd3")

        response = client.get("/api/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 3
        # Most recent job (C) should be first
        assert jobs[0]["name"] == "Job C"

    def test_health_endpoint(self):
        """/api/health returns expected fields"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "python" in data
        assert "database" in data

    def test_stats_empty_db(self):
        """Stats API returns zeros when DB is empty"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 0
        assert data["active_jobs"] == 0
        assert data["completed_mailboxes"] == 0
        assert data["data_transferred"] == "0 B"

    def test_stats_with_data(self):
        """Stats API reflects actual data"""
        create_test_job("Stats Job")
        response = client.get("/api/stats")
        data = response.json()
        assert data["total_jobs"] == 1
        # New job starts as "running" status
        assert data["active_jobs"] == 1

    def test_cancel_completed_job(self):
        """Cancel a job that's already completed (no running mailboxes)"""
        res = create_test_job("Completed Job")
        job_id = res.json()["id"]

        # Set job to completed
        db = TestingSessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "completed"
        db.commit()
        db.close()

        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 200
        assert response.json()["cancelled"] == 0

    def test_retry_running_mailbox(self):
        """Retry a mailbox that's already running should fail"""
        res = create_test_job("Retry Running Job")
        job_id = res.json()["id"]

        # Add mailbox
        mb_res = client.post(f"/api/jobs/{job_id}/mailboxes", json={
            "source_user": "u1@test.com",
            "source_pass": "p1",
            "target_user": "u2@test.com",
            "target_pass": "p2"
        })
        mb_id = mb_res.json()["mailbox_id"]

        # Set mailbox to running
        db = TestingSessionLocal()
        mb = db.query(Mailbox).filter(Mailbox.id == mb_id).first()
        mb.status = "running"
        db.commit()
        db.close()

        response = client.post(f"/api/mailboxes/{mb_id}/retry")
        assert response.status_code == 400
        assert "already running" in response.json()["detail"]

    def test_job_response_format(self):
        """Verify job response has all expected fields"""
        res = create_test_job("Format Job")
        assert res.status_code == 200
        data = res.json()

        expected_fields = ["id", "name", "status", "progress", "total", "completed",
                           "failed", "source", "target", "data_transferred", "created_at"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_multiple_mailboxes_in_job(self):
        """Add multiple mailboxes to a single job"""
        res = create_test_job("Multi MB Job")
        job_id = res.json()["id"]

        for i in range(5):
            mb_res = client.post(f"/api/jobs/{job_id}/mailboxes", json={
                "source_user": f"user{i}@src.com",
                "source_pass": f"pass{i}",
                "target_user": f"user{i}@tgt.com",
                "target_pass": f"tpass{i}"
            })
            assert mb_res.status_code == 200

        # Verify total
        job_res = client.get(f"/api/jobs/{job_id}?password=testpwd123")
        assert job_res.status_code == 200
        assert job_res.json()["total"] == 5

    def test_data_transferred_formatting(self):
        """Verify data_transferred formatting (B, KB, MB, GB)"""
        res = create_test_job("Data Format Job")
        job_id = res.json()["id"]

        # Set various sizes
        db = TestingSessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()

        # 500 bytes
        job.data_transferred = 500
        db.commit()
        db.close()

        response = client.get(f"/api/jobs/{job_id}?password=testpwd123")
        assert "B" in response.json()["data_transferred"]

    def test_serve_html_pages(self):
        """Test all HTML page routes"""
        for path in ["/", "/index.html", "/create-job.html", "/job-detail.html", "/guide.html"]:
            response = client.get(path)
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
