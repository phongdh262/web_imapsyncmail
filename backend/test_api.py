"""
Test cases for IMAP Sync Pro API
Comprehensive tests covering all API endpoints and features
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os
import io

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app

client = TestClient(app)


# ============================================================
# 1. HEALTH CHECK TESTS
# ============================================================
class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check_status(self):
        """Test that health check endpoint returns ok status"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_health_check_includes_system_info(self):
        """Test health check returns system information"""
        response = client.get("/api/health")
        data = response.json()
        assert "python" in data
        assert "database" in data
        assert "cwd" in data
        assert "imapsync" in data


# ============================================================
# 2. STATS ENDPOINT TESTS
# ============================================================
class TestStatsEndpoint:
    """Test dashboard stats endpoint"""
    
    def test_get_stats_structure(self):
        """Test that stats endpoint returns expected data structure"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "active_jobs" in data
        assert "completed_mailboxes" in data
        assert "data_transferred" in data
    
    def test_stats_values_are_valid(self):
        """Test that stats values are valid numbers"""
        response = client.get("/api/stats")
        data = response.json()
        assert isinstance(data["total_jobs"], int)
        assert isinstance(data["active_jobs"], int)
        assert isinstance(data["completed_mailboxes"], int)
        assert data["total_jobs"] >= 0
        assert data["active_jobs"] >= 0


# ============================================================
# 3. JOBS CRUD TESTS
# ============================================================
class TestJobsCRUD:
    """Test jobs CRUD operations"""
    
    def test_list_jobs(self):
        """Test listing all jobs"""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_job_basic(self):
        """Test creating a new job with basic info"""
        job_data = {
            "name": "Test Migration Job",
            "source_host": "imap.test-source.com",
            "target_host": "imap.test-target.com"
        }
        response = client.post("/api/jobs", json=job_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Migration Job"
        assert data["source"] == "imap.test-source.com"
        assert data["target"] == "imap.test-target.com"
        assert "id" in data
    
    def test_create_job_with_options(self):
        """Test creating a job with all options"""
        job_data = {
            "name": "Full Options Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "source_port": 993,
            "target_port": 993,
            "source_security": "SSL/TLS",
            "target_security": "SSL/TLS",
            "options": {
                "sync_internal_dates": True,
                "skip_trash": True,
                "dry_run": True,
                "concurrency": 5
            }
        }
        response = client.post("/api/jobs", json=job_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
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
        assert "data_transferred" in data
    
    def test_get_nonexistent_job(self):
        """Test getting a job that doesn't exist"""
        response = client.get("/api/jobs/nonexistent-job-id-12345")
        assert response.status_code == 404
    
    def test_delete_job(self):
        """Test deleting a specific job"""
        # Create a job first
        job_data = {
            "name": "Job to Delete",
            "source_host": "delete.source.com",
            "target_host": "delete.target.com"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = client.get(f"/api/jobs/{job_id}")
        assert get_response.status_code == 404


# ============================================================
# 4. PASSWORD PROTECTION TESTS
# ============================================================
class TestPasswordProtection:
    """Test job password protection feature"""
    
    def test_create_job_with_password(self):
        """Test creating a job with password protection"""
        job_data = {
            "name": "Password Protected Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "password": "secret123"
        }
        response = client.post("/api/jobs", json=job_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        return data["id"]
    
    def test_access_protected_job_without_password(self):
        """Test accessing protected job without password returns 401"""
        # Create protected job
        job_data = {
            "name": "Protected Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "password": "mypassword"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Try to access without password
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Password required"
    
    def test_access_protected_job_with_correct_password(self):
        """Test accessing protected job with correct password"""
        # Create protected job
        job_data = {
            "name": "Protected Job 2",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "password": "correctpass"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Access with correct password
        response = client.get(
            f"/api/jobs/{job_id}",
            params={"password": "correctpass"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
    
    def test_access_protected_job_with_wrong_password(self):
        """Test accessing protected job with wrong password returns 401"""
        # Create protected job
        job_data = {
            "name": "Protected Job 3",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "password": "realpassword"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Access with wrong password
        response = client.get(
            f"/api/jobs/{job_id}",
            params={"password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect password"
    
    def test_verify_password_endpoint(self):
        """Test the verify password endpoint"""
        # Create protected job
        job_data = {
            "name": "Verify Test Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "password": "verifypass"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Verify with correct password
        response = client.post(
            f"/api/jobs/{job_id}/verify",
            json={"password": "verifypass"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert data["password_required"] == True
    
    def test_verify_wrong_password(self):
        """Test verify endpoint with wrong password"""
        # Create protected job
        job_data = {
            "name": "Verify Wrong Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "password": "correct"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Verify with wrong password
        response = client.post(
            f"/api/jobs/{job_id}/verify",
            json={"password": "wrong"}
        )
        assert response.status_code == 401
    
    def test_unprotected_job_access(self):
        """Test that unprotected jobs can be accessed without password"""
        # Create job without password
        job_data = {
            "name": "Unprotected Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        # Access without password - should work
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200


# ============================================================
# 5. MAILBOX OPERATIONS TESTS
# ============================================================
class TestMailboxOperations:
    """Test mailbox operations"""
    
    def test_add_single_mailbox(self):
        """Test adding a single mailbox to a job"""
        # Create a job
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
        return data["mailbox_id"]
    
    def test_add_mailbox_to_nonexistent_job(self):
        """Test adding mailbox to a job that doesn't exist"""
        mailbox_data = {
            "source_user": "test@source.com",
            "source_pass": "test_password",
            "target_user": "test@target.com",
            "target_pass": "target_password"
        }
        response = client.post("/api/jobs/nonexistent-id-xyz/mailboxes", json=mailbox_data)
        assert response.status_code == 404
    
    def test_mailbox_logs_endpoint(self):
        """Test getting mailbox logs"""
        # Create job and add mailbox
        job_data = {
            "name": "Log Test Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        mailbox_data = {
            "source_user": "logtest@source.com",
            "source_pass": "password",
            "target_user": "logtest@target.com",
            "target_pass": "password"
        }
        mailbox_response = client.post(f"/api/jobs/{job_id}/mailboxes", json=mailbox_data)
        mailbox_id = mailbox_response.json()["mailbox_id"]
        
        # Get logs
        response = client.get(f"/api/mailboxes/{mailbox_id}/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
    
    def test_protected_job_mailbox_logs(self):
        """Test mailbox logs require password for protected jobs"""
        # Create protected job
        job_data = {
            "name": "Protected Log Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com",
            "password": "logpass"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        # Add mailbox (need password to access job first for proper test)
        mailbox_data = {
            "source_user": "protlog@source.com",
            "source_pass": "password",
            "target_user": "protlog@target.com",
            "target_pass": "password"
        }
        mailbox_response = client.post(f"/api/jobs/{job_id}/mailboxes", json=mailbox_data)
        mailbox_id = mailbox_response.json()["mailbox_id"]
        
        # Try to get logs without password - should fail
        response = client.get(f"/api/mailboxes/{mailbox_id}/logs")
        assert response.status_code == 401
        
        # Get logs with password - should work
        response = client.get(
            f"/api/mailboxes/{mailbox_id}/logs",
            params={"password": "logpass"}
        )
        assert response.status_code == 200


# ============================================================
# 6. CSV UPLOAD TESTS
# ============================================================
class TestCSVUpload:
    """Test CSV file upload functionality"""
    
    def test_upload_valid_csv(self):
        """Test uploading a valid CSV file"""
        # Create a job first
        job_data = {
            "name": "CSV Upload Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        # Create CSV content
        csv_content = """source_user,source_pass,target_user,target_pass
user1@source.com,pass1,user1@target.com,tpass1
user2@source.com,pass2,user2@target.com,tpass2"""
        
        # Upload CSV
        files = {"file": ("test.csv", csv_content, "text/csv")}
        response = client.post(f"/api/jobs/{job_id}/csv", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 2
    
    def test_upload_csv_to_nonexistent_job(self):
        """Test uploading CSV to nonexistent job"""
        csv_content = "source_user,source_pass,target_user,target_pass\ntest@a.com,p,test@b.com,p"
        files = {"file": ("test.csv", csv_content, "text/csv")}
        response = client.post("/api/jobs/nonexistent-job-id/csv", files=files)
        assert response.status_code == 404


# ============================================================
# 7. MAILBOX CONTROL TESTS (Stop/Retry)
# ============================================================
class TestMailboxControl:
    """Test mailbox stop and retry operations"""
    
    def test_stop_mailbox(self):
        """Test stopping a mailbox sync"""
        # Create job and mailbox
        job_data = {
            "name": "Stop Test Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        mailbox_data = {
            "source_user": "stop@source.com",
            "source_pass": "password",
            "target_user": "stop@target.com",
            "target_pass": "password"
        }
        mailbox_response = client.post(f"/api/jobs/{job_id}/mailboxes", json=mailbox_data)
        mailbox_id = mailbox_response.json()["mailbox_id"]
        
        # Stop the mailbox
        response = client.post(f"/api/mailboxes/{mailbox_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_retry_mailbox(self):
        """Test retrying a failed mailbox"""
        # Create job and mailbox
        job_data = {
            "name": "Retry Test Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        mailbox_data = {
            "source_user": "retry@source.com",
            "source_pass": "password",
            "target_user": "retry@target.com",
            "target_pass": "password"
        }
        mailbox_response = client.post(f"/api/jobs/{job_id}/mailboxes", json=mailbox_data)
        mailbox_id = mailbox_response.json()["mailbox_id"]
        
        # Retry the mailbox
        response = client.post(f"/api/mailboxes/{mailbox_id}/retry")
        # Should work even if not failed (will restart)
        assert response.status_code == 200


# ============================================================
# 8. PROGRESS AND DATA TRANSFERRED TESTS
# ============================================================
class TestProgressTracking:
    """Test progress tracking and data transferred"""
    
    def test_job_includes_progress(self):
        """Test that job response includes progress field"""
        job_data = {
            "name": "Progress Test Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        response = client.get(f"/api/jobs/{job_id}")
        data = response.json()
        assert "progress" in data
        assert isinstance(data["progress"], int)
        assert 0 <= data["progress"] <= 100
    
    def test_job_includes_data_transferred(self):
        """Test that job response includes data_transferred field"""
        job_data = {
            "name": "Data Transfer Test Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        create_response = client.post("/api/jobs", json=job_data)
        job_id = create_response.json()["id"]
        
        response = client.get(f"/api/jobs/{job_id}")
        data = response.json()
        assert "data_transferred" in data
        # Should be formatted string like "0 B" or "1.5 MB"
        assert isinstance(data["data_transferred"], str)
    
    def test_mailbox_includes_progress(self):
        """Test that mailbox in job response includes progress"""
        # Create job and mailbox
        job_data = {
            "name": "Mailbox Progress Job",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        mailbox_data = {
            "source_user": "progress@source.com",
            "source_pass": "password",
            "target_user": "progress@target.com",
            "target_pass": "password"
        }
        client.post(f"/api/jobs/{job_id}/mailboxes", json=mailbox_data)
        
        # Get job detail
        response = client.get(f"/api/jobs/{job_id}")
        data = response.json()
        assert len(data["mailboxes"]) > 0
        mailbox = data["mailboxes"][0]
        assert "progress" in mailbox
        assert "status" in mailbox


# ============================================================
# 9. HTML PAGES TESTS
# ============================================================
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
    
    def test_job_detail_page(self):
        """Test job-detail.html page loads"""
        response = client.get("/job-detail.html")
        assert response.status_code == 200
    
    def test_guide_page(self):
        """Test guide.html page loads"""
        response = client.get("/guide.html")
        assert response.status_code == 200
    
    def test_css_loads(self):
        """Test CSS file loads"""
        response = client.get("/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
    
    def test_js_loads(self):
        """Test JavaScript file loads"""
        response = client.get("/js/app.js")
        assert response.status_code == 200


# ============================================================
# 10. NO AUTH REQUIRED TESTS
# ============================================================
class TestNoAuthRequired:
    """Verify that authentication is NOT required for endpoints"""
    
    def test_jobs_no_auth(self):
        """Test that /api/jobs doesn't require auth"""
        response = client.get("/api/jobs")
        assert response.status_code != 401 or response.status_code == 200
    
    def test_stats_no_auth(self):
        """Test that /api/stats doesn't require auth"""
        response = client.get("/api/stats")
        assert response.status_code == 200
    
    def test_create_job_no_auth(self):
        """Test that POST /api/jobs doesn't require auth"""
        job_data = {
            "name": "No Auth Test",
            "source_host": "test.com",
            "target_host": "test2.com"
        }
        response = client.post("/api/jobs", json=job_data)
        assert response.status_code == 200
    
    def test_health_no_auth(self):
        """Test that /api/health doesn't require auth"""
        response = client.get("/api/health")
        assert response.status_code == 200


# ============================================================
# 11. ERROR HANDLING TESTS
# ============================================================
class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_job_data(self):
        """Test creating job with missing required fields"""
        job_data = {
            "name": "Missing Host Job"
            # Missing source_host and target_host
        }
        response = client.post("/api/jobs", json=job_data)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_mailbox_data(self):
        """Test adding mailbox with missing fields"""
        # Create job first
        job_data = {
            "name": "Invalid Mailbox Test",
            "source_host": "imap.source.com",
            "target_host": "imap.target.com"
        }
        job_response = client.post("/api/jobs", json=job_data)
        job_id = job_response.json()["id"]
        
        # Try to add mailbox with missing fields
        mailbox_data = {
            "source_user": "test@source.com"
            # Missing other required fields
        }
        response = client.post(f"/api/jobs/{job_id}/mailboxes", json=mailbox_data)
        assert response.status_code == 422
    
    def test_nonexistent_mailbox_logs(self):
        """Test getting logs for nonexistent mailbox"""
        response = client.get("/api/mailboxes/999999/logs")
        assert response.status_code == 404


# ============================================================
# RUN TESTS
# ============================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
