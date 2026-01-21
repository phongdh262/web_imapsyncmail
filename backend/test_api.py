"""
Test cases for IMAP Sync Pro API
Tests the main API endpoints without authentication
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test that health check endpoint returns ok status"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "python" in data
        assert "database" in data


class TestStatsEndpoint:
    """Test dashboard stats endpoint (no auth required)"""
    
    def test_get_stats(self):
        """Test that stats endpoint returns expected data structure"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "active_jobs" in data
        assert "completed_mailboxes" in data
        assert "data_transferred" in data


class TestJobsEndpoint:
    """Test jobs CRUD operations (no auth required)"""
    
    def test_list_jobs(self):
        """Test listing all jobs"""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_job(self):
        """Test creating a new job"""
        job_data = {
            "name": "Test Migration Job",
            "source_host": "imap.test-source.com",
            "target_host": "imap.test-target.com",
            "source_port": 993,
            "target_port": 993,
            "source_security": "SSL/TLS",
            "target_security": "SSL/TLS",
            "options": {
                "sync_internal_dates": True,
                "skip_trash": True,
                "dry_run": True
            }
        }
        response = client.post("/api/jobs", json=job_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Migration Job"
        assert data["source"] == "imap.test-source.com"
        assert data["target"] == "imap.test-target.com"
        assert "id" in data
        return data["id"]
    
    def test_get_job_detail(self):
        """Test getting a specific job detail"""
        # First create a job
        job_data = {
            "name": "Test Job for Detail",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Then get its details
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert "mailboxes" in data
        assert "progress" in data
    
    def test_get_nonexistent_job(self):
        """Test getting a job that doesn't exist"""
        response = client.get("/api/jobs/nonexistent-job-id")
        assert response.status_code == 404


class TestMailboxEndpoint:
    """Test mailbox operations"""
    
    def test_add_single_mailbox(self):
        """Test adding a single mailbox to a job"""
        # First create a job
        job_data = {
            "name": "Test Job for Mailbox",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        # Add a mailbox
        mailbox_data = {
            "source_user": "test@source.com",
            "source_pass": "test_password",
            "target_user": "test@target.com",
            "target_pass": "target_password"
        }
        response = client.post(f"/api/jobs/{job_id}/mailboxes", json=mailbox_data)
        assert response.status_code == 200
        data = response.json()
        assert "mailbox_id" in data
    
    def test_add_mailbox_to_nonexistent_job(self):
        """Test adding mailbox to a job that doesn't exist"""
        mailbox_data = {
            "source_user": "test@source.com",
            "source_pass": "test_password",
            "target_user": "test@target.com",
            "target_pass": "target_password"
        }
        response = client.post("/api/jobs/nonexistent-id/mailboxes", json=mailbox_data)
        assert response.status_code == 404


class TestHTMLPages:
    """Test that HTML pages are served correctly"""
    
    def test_index_page(self):
        """Test index page loads"""
        response = client.get("/")
        assert response.status_code == 200
        assert "IMAP Sync" in response.text
    
    def test_index_html(self):
        """Test index.html page loads"""
        response = client.get("/index.html")
        assert response.status_code == 200
        assert "IMAP Sync" in response.text
    
    def test_create_job_page(self):
        """Test create-job.html page loads"""
        response = client.get("/create-job.html")
        assert response.status_code == 200
        assert "Create" in response.text or "Migration" in response.text
    
    def test_guide_page(self):
        """Test guide.html page loads"""
        response = client.get("/guide.html")
        assert response.status_code == 200


class TestNoAuthRequired:
    """Verify that authentication is NOT required for endpoints"""
    
    def test_jobs_no_auth(self):
        """Test that /api/jobs doesn't require auth"""
        response = client.get("/api/jobs")
        # Should NOT return 401 Unauthorized
        assert response.status_code != 401
        assert response.status_code == 200
    
    def test_stats_no_auth(self):
        """Test that /api/stats doesn't require auth"""
        response = client.get("/api/stats")
        assert response.status_code != 401
        assert response.status_code == 200
    
    def test_create_job_no_auth(self):
        """Test that POST /api/jobs doesn't require auth"""
        job_data = {
            "name": "No Auth Test",
            "source_host": "test.com",
            "target_host": "test2.com"
        }
        response = client.post("/api/jobs", json=job_data)
        assert response.status_code != 401
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
