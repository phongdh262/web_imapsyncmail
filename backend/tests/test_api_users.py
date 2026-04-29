"""
Test Suite: API — Admin User Management & RBAC
Tests: list, create, update password, delete users, and permission checks.
"""
import pytest, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestListUsers:
    def test_list_users(self, admin_client):
        """Root admin can list all users."""
        c, _ = admin_client
        r = c.get("/api/admin/users")
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        assert any(u["username"] == "phongdh" for u in users)

    def test_list_users_shows_root_flag(self, admin_client):
        """Root admin has is_root_admin=True."""
        c, _ = admin_client
        r = c.get("/api/admin/users")
        root = [u for u in r.json() if u["username"] == "phongdh"][0]
        assert root["is_root_admin"] is True


class TestCreateUser:
    def test_create_user(self, admin_client):
        """Create new user returns 201."""
        c, csrf = admin_client
        r = c.post("/api/admin/users", json={"username": "newuser01", "password": "secure1234"},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 201
        assert r.json()["username"] == "newuser01"
        assert r.json()["is_root_admin"] is False

    def test_create_duplicate_user(self, admin_client):
        """Duplicate username returns 409."""
        c, csrf = admin_client
        c.post("/api/admin/users", json={"username": "dupeuser1", "password": "secure1234"},
               headers={"X-CSRF-Token": csrf})
        r = c.post("/api/admin/users", json={"username": "dupeuser1", "password": "secure1234"},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 409

    def test_create_user_invalid_username(self, admin_client):
        """Invalid username pattern returns 400."""
        c, csrf = admin_client
        r = c.post("/api/admin/users", json={"username": "a!", "password": "secure1234"},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400

    def test_create_user_short_password(self, admin_client):
        """Password <8 chars returns 400."""
        c, csrf = admin_client
        r = c.post("/api/admin/users", json={"username": "shortpw01", "password": "abc"},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400

    def test_create_user_too_short_username(self, admin_client):
        """Username <3 chars returns 400."""
        c, csrf = admin_client
        r = c.post("/api/admin/users", json={"username": "ab", "password": "secure1234"},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400


class TestUpdateUserPassword:
    def test_update_password(self, admin_client):
        """Update user password succeeds."""
        c, csrf = admin_client
        r1 = c.post("/api/admin/users", json={"username": "pwupdate1", "password": "oldpass1234"},
                     headers={"X-CSRF-Token": csrf})
        uid = r1.json()["id"]
        r2 = c.put(f"/api/admin/users/{uid}/password", json={"password": "newpass5678"},
                    headers={"X-CSRF-Token": csrf})
        assert r2.status_code == 200
        assert r2.json()["username"] == "pwupdate1"

    def test_update_password_too_short(self, admin_client):
        """Password <8 chars rejected."""
        c, csrf = admin_client
        r1 = c.post("/api/admin/users", json={"username": "pwshort1", "password": "oldpass1234"},
                     headers={"X-CSRF-Token": csrf})
        uid = r1.json()["id"]
        r2 = c.put(f"/api/admin/users/{uid}/password", json={"password": "abc"},
                    headers={"X-CSRF-Token": csrf})
        assert r2.status_code == 400

    def test_update_nonexistent_user(self, admin_client):
        """Update password for missing user returns 404."""
        c, csrf = admin_client
        r = c.put("/api/admin/users/99999/password", json={"password": "newpass5678"},
                   headers={"X-CSRF-Token": csrf})
        assert r.status_code == 404


class TestDeleteUser:
    def test_delete_user(self, admin_client):
        """Delete a non-root user succeeds."""
        c, csrf = admin_client
        r1 = c.post("/api/admin/users", json={"username": "todelete1", "password": "pass12345678"},
                     headers={"X-CSRF-Token": csrf})
        uid = r1.json()["id"]
        r2 = c.delete(f"/api/admin/users/{uid}", headers={"X-CSRF-Token": csrf})
        assert r2.status_code == 200

    def test_delete_root_admin_blocked(self, admin_client):
        """Cannot delete root admin."""
        c, csrf = admin_client
        # Get admin user ID
        users = c.get("/api/admin/users").json()
        root_id = [u for u in users if u["username"] == "phongdh"][0]["id"]
        r = c.delete(f"/api/admin/users/{root_id}", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400
        assert "root admin" in r.json()["detail"].lower()

    def test_delete_nonexistent_user(self, admin_client):
        """Delete missing user returns 404."""
        c, csrf = admin_client
        r = c.delete("/api/admin/users/99999", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 404


class TestNonRootAccess:
    def test_non_root_cannot_list_users(self, admin_client):
        """Non-root user gets 403 on user management."""
        c, csrf = admin_client
        # Create a non-root user
        c.post("/api/admin/users", json={"username": "regular01", "password": "regular1234"},
               headers={"X-CSRF-Token": csrf})
        # Logout and login as non-root
        c.post("/api/logout")
        r = c.post("/api/login", data={"username": "regular01", "password": "regular1234"})
        assert r.status_code == 200
        # Try to list users
        r2 = c.get("/api/admin/users")
        assert r2.status_code == 403
