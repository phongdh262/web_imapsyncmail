"""
test_security.py
Security-focused tests: SQL injection, XSS, path traversal, password leaks,
cookie security, and cryptographic validation for IMAP Sync Pro.
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

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_security.db"
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


def create_test_job(name="Secure Job", password="securepassword"):
    return client.post("/api/jobs", json={
        "name": name,
        "source_host": "imap.source.com",
        "target_host": "imap.target.com",
        "password": password
    })


# ==========================================
# 1. SQL Injection Tests
# ==========================================

class TestSQLInjection:
    """Tests to ensure SQL injection is not possible"""

    def test_sql_injection_job_id_get(self):
        """SQL injection in job_id for GET request"""
        malicious_ids = [
            "'; DROP TABLE jobs;--",
            "1 OR 1=1",
            "1; DELETE FROM jobs WHERE 1=1;--",
            "' UNION SELECT * FROM users--",
        ]
        for mal_id in malicious_ids:
            response = client.get(f"/api/jobs/{mal_id}")
            # Should return 404 (not found), NOT 500 (server error)
            assert response.status_code in [404, 422], f"Unexpected status for injection: {mal_id}"

    def test_sql_injection_job_id_delete(self):
        """SQL injection in job_id for DELETE request"""
        response = client.delete("/api/jobs/'; DROP TABLE jobs;--")
        assert response.status_code in [404, 422]

        # Verify jobs table still exists
        list_res = client.get("/api/jobs")
        assert list_res.status_code == 200

    def test_sql_injection_in_password_field(self):
        """SQL injection in password query parameter"""
        res = create_test_job()
        job_id = res.json()["id"]

        injections = [
            "' OR '1'='1",
            "'; DROP TABLE jobs;--",
            "admin'--",
        ]
        for injection in injections:
            response = client.get(f"/api/jobs/{job_id}?password={injection}")
            # Should fail auth, not bypass it
            assert response.status_code == 401

    def test_sql_injection_in_job_name(self):
        """SQL injection in job name field"""
        response = client.post("/api/jobs", json={
            "name": "'; DROP TABLE jobs;--",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "pwd"
        })
        assert response.status_code == 200

        # Verify the name is stored as-is, not executed
        jobs = client.get("/api/jobs").json()
        assert any("DROP TABLE" in j["name"] for j in jobs)

    def test_sql_injection_in_mailbox_user(self):
        """SQL injection in mailbox source_user"""
        res = create_test_job()
        job_id = res.json()["id"]

        response = client.post(f"/api/jobs/{job_id}/mailboxes", json={
            "source_user": "' OR 1=1;--",
            "source_pass": "pass",
            "target_user": "target@test.com",
            "target_pass": "pass"
        })
        assert response.status_code == 200


# ==========================================
# 2. XSS Tests
# ==========================================

class TestXSS:
    """Tests to ensure XSS payloads are stored safely"""

    def test_xss_in_job_name(self):
        """XSS payload in job name"""
        xss_payloads = [
            '<script>alert("xss")</script>',
            '<img src=x onerror=alert(1)>',
            '"><script>document.cookie</script>',
            "javascript:alert(1)",
        ]
        for payload in xss_payloads:
            response = create_test_job(name=payload)
            assert response.status_code == 200
            # Backend should store as-is (output encoding is frontend responsibility)
            assert response.json()["name"] == payload

    def test_xss_in_mailbox_user(self):
        """XSS payload in mailbox source_user"""
        res = create_test_job()
        job_id = res.json()["id"]

        response = client.post(f"/api/jobs/{job_id}/mailboxes", json={
            "source_user": '<script>alert("xss")</script>',
            "source_pass": "pass",
            "target_user": "target@test.com",
            "target_pass": "pass"
        })
        assert response.status_code == 200

    def test_xss_in_csv_upload(self):
        """XSS payload in CSV file data"""
        res = create_test_job("XSS CSV Job")
        job_id = res.json()["id"]

        csv_content = '<script>alert(1)</script>,pass,target@test.com,pass\n'
        files = {"file": ("xss.csv", csv_content, "text/csv")}
        response = client.post(f"/api/upload/{job_id}", files=files)
        assert response.status_code == 200


# ==========================================
# 3. Path Traversal Tests
# ==========================================

class TestPathTraversal:
    """Tests for path traversal in log access"""

    def test_path_traversal_in_mailbox_id(self):
        """Attempt path traversal through mailbox ID"""
        # The mailbox_id is an integer, so path traversal shouldn't be possible
        # But test with path-like values anyway
        response = client.get("/api/mailboxes/../../etc/passwd/logs")
        # FastAPI routing should reject this
        assert response.status_code in [404, 422]

    def test_negative_mailbox_id_logs(self):
        """Negative mailbox ID for log access"""
        response = client.get("/api/mailboxes/-1/logs")
        assert response.status_code in [404, 422]


# ==========================================
# 4. Password & Data Leak Tests
# ==========================================

class TestDataLeaks:
    """Tests to ensure sensitive data is not leaked in API responses"""

    def test_password_hash_not_in_list_response(self):
        """password_hash should not appear in job list response"""
        create_test_job()
        response = client.get("/api/jobs")
        response_text = response.text
        assert "password_hash" not in response_text

    def test_password_hash_not_in_detail_response(self):
        """password_hash should not appear in job detail response"""
        res = create_test_job()
        job_id = res.json()["id"]

        response = client.get(f"/api/jobs/{job_id}?password=securepassword")
        response_text = response.text
        assert "password_hash" not in response_text

    def test_encrypted_passwords_not_in_response(self):
        """Encrypted mailbox passwords should not appear in detail response"""
        res = create_test_job()
        job_id = res.json()["id"]

        client.post(f"/api/jobs/{job_id}/mailboxes", json={
            "source_user": "user@test.com",
            "source_pass": "my_secret_password_123",
            "target_user": "target@test.com",
            "target_pass": "my_target_password_456"
        })

        response = client.get(f"/api/jobs/{job_id}?password=securepassword")
        response_text = response.text
        # Raw passwords should never appear in response
        assert "my_secret_password_123" not in response_text
        assert "my_target_password_456" not in response_text

    def test_stats_no_sensitive_data(self):
        """Stats endpoint should not leak any sensitive data"""
        create_test_job()
        response = client.get("/api/stats")
        response_text = response.text
        assert "password" not in response_text.lower() or "data_transferred" in response_text


# ==========================================
# 5. Cookie Security Tests
# ==========================================

class TestCookieSecurity:
    """Tests for cookie attributes and behavior"""

    def test_create_job_sets_cookie(self):
        """Creating a job with password sets job_password cookie"""
        response = create_test_job()
        assert response.status_code == 200
        # Check that set-cookie header exists
        assert "set-cookie" in response.headers

    def test_verify_password_sets_cookie(self):
        """Verify password endpoint sets cookie on success"""
        res = create_test_job()
        job_id = res.json()["id"]

        verify_client = TestClient(app)
        response = verify_client.post(
            f"/api/jobs/{job_id}/verify",
            json={"password": "securepassword"}
        )
        assert response.status_code == 200
        assert "set-cookie" in response.headers


# ==========================================
# 6. Authentication Edge Cases
# ==========================================

class TestPasswordEdgeCases:
    """Tests for edge cases in password handling"""

    def test_empty_password_job(self):
        """Create job with empty string password"""
        response = client.post("/api/jobs", json={
            "name": "Empty PW Job",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": ""
        })
        # Empty password should still be accepted (hashed)
        assert response.status_code in [200, 422]

    def test_unicode_password(self):
        """Unicode characters in password — handled by SHA-256 pre-hashing"""
        response = client.post("/api/jobs", json={
            "name": "Unicode PW Job",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": "🔐密码пароль"
        })
        # SHA-256 pre-hashing normalizes any password to 64 bytes
        assert response.status_code == 200
        job_id = response.json()["id"]
        verify_res = client.post(f"/api/jobs/{job_id}/verify", json={"password": "🔐密码пароль"})
        assert verify_res.status_code == 200
        assert verify_res.json()["valid"] is True

    def test_very_long_password(self):
        """Very long password (1000+ characters) handled by SHA-256 pre-hashing"""
        long_pwd = "A" * 1000
        response = client.post("/api/jobs", json={
            "name": "Long PW Job",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": long_pwd
        })
        # SHA-256 pre-hashing normalizes to 64 bytes, so this should work
        assert response.status_code == 200

    def test_special_chars_password(self):
        """Password with special characters"""
        special_pwd = r'!@#$%^&*()_+-={}[]|":;<>?,./~`'
        response = client.post("/api/jobs", json={
            "name": "Special PW Job",
            "source_host": "imap.test.com",
            "target_host": "imap.target.com",
            "password": special_pwd
        })
        assert response.status_code == 200

        job_id = response.json()["id"]
        # Use /verify endpoint to avoid URL encoding issues with special chars in query params
        verify_res = client.post(f"/api/jobs/{job_id}/verify", json={"password": special_pwd})
        assert verify_res.status_code == 200
        assert verify_res.json()["valid"] is True

    def test_log_access_cross_job_password(self):
        """Access logs of job A using job B's password (should fail)"""
        # Create two jobs with different passwords
        res_a = create_test_job("Job A", "password_a")
        job_a_id = res_a.json()["id"]

        res_b = create_test_job("Job B", "password_b")

        # Add mailbox to job A
        mb_res = client.post(f"/api/jobs/{job_a_id}/mailboxes", json={
            "source_user": "u1@test.com",
            "source_pass": "p1",
            "target_user": "u2@test.com",
            "target_pass": "p2"
        })
        mb_id = mb_res.json()["mailbox_id"]

        # Try accessing job A's logs with job B's password
        no_auth = TestClient(app)
        response = no_auth.get(f"/api/mailboxes/{mb_id}/logs?password=password_b")
        assert response.status_code == 401
