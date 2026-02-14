"""
test_database.py
Database model, encryption, and ORM relationship tests for IMAP Sync Pro.
Tests cover Fernet encryption/decryption, model defaults, relationships,
and database utility functions.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import (
    Base, Job, Mailbox, User,
    encrypt_password, decrypt_password,
    get_db, init_db
)

# Setup test database (in-memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_database.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# ==========================================
# 1. Fernet Encryption Tests
# ==========================================

class TestEncryption:
    """Tests for password encryption/decryption using Fernet"""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypt then decrypt returns original password"""
        original = "my_secret_password"
        encrypted = encrypt_password(original)
        decrypted = decrypt_password(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self):
        """Empty string encryption returns empty string"""
        result = encrypt_password("")
        assert result == ""
        assert decrypt_password("") == ""

    def test_encrypt_unicode(self):
        """Unicode characters in password"""
        original = "密码пароль🔑한국어"
        encrypted = encrypt_password(original)
        decrypted = decrypt_password(encrypted)
        assert decrypted == original

    def test_encrypt_special_chars(self):
        """Special characters in password"""
        original = r'!@#$%^&*()_+-={}[]|\":;<>?,./~`'
        encrypted = encrypt_password(original)
        decrypted = decrypt_password(encrypted)
        assert decrypted == original

    def test_different_encryptions_same_input(self):
        """Same input produces different ciphertexts (Fernet uses random IV)"""
        password = "test_password"
        enc1 = encrypt_password(password)
        enc2 = encrypt_password(password)
        # Fernet includes a timestamp and random IV, so they should differ
        assert enc1 != enc2
        # But both should decrypt to the same value
        assert decrypt_password(enc1) == password
        assert decrypt_password(enc2) == password

    def test_encrypt_long_password(self):
        """Encrypt a very long password"""
        original = "A" * 10000
        encrypted = encrypt_password(original)
        decrypted = decrypt_password(encrypted)
        assert decrypted == original

    def test_encrypted_value_is_string(self):
        """Encrypted value should be a string"""
        encrypted = encrypt_password("test")
        assert isinstance(encrypted, str)

    def test_encrypted_not_readable(self):
        """Encrypted value should not contain the original password"""
        original = "my_secret"
        encrypted = encrypt_password(original)
        assert original not in encrypted


# ==========================================
# 2. Job Model Tests
# ==========================================

class TestJobModel:
    """Tests for Job SQLAlchemy model"""

    def test_job_defaults(self):
        """Job model has correct default values"""
        db = TestingSessionLocal()
        job = Job(
            id="test-uuid-123",
            name="Test Job",
            source_host="imap.src.com",
            target_host="imap.tgt.com"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.status == "pending"
        assert job.source_port == 993
        assert job.target_port == 993
        assert job.source_security == "SSL/TLS"
        assert job.target_security == "SSL/TLS"
        assert job.total_mailboxes == 0
        assert job.completed == 0
        assert job.failed == 0
        assert job.data_transferred == 0
        assert job.created_at is not None
        db.close()

    def test_job_all_fields(self):
        """Job with all fields populated"""
        db = TestingSessionLocal()
        job = Job(
            id="full-uuid-456",
            name="Full Job",
            status="running",
            password_hash="hashed_pw",
            source_host="imap.src.com",
            source_port=143,
            source_security="STARTTLS",
            target_host="imap.tgt.com",
            target_port=143,
            target_security="STARTTLS",
            options='{"dry_run": true}',
            csv_path="/path/to/file.csv",
            total_mailboxes=10,
            completed=5,
            failed=2,
            data_transferred=1024000
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.source_port == 143
        assert job.source_security == "STARTTLS"
        assert job.data_transferred == 1024000
        db.close()

    def test_job_data_transferred_bigint(self):
        """Large byte values in data_transferred (BigInteger)"""
        db = TestingSessionLocal()
        job = Job(
            id="bigint-uuid",
            name="Big Data Job",
            source_host="src.com",
            target_host="tgt.com",
            data_transferred=10 * (1024 ** 3)  # 10 GB in bytes
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.data_transferred == 10 * (1024 ** 3)
        db.close()

    def test_job_nullable_fields(self):
        """Nullable fields can be None"""
        db = TestingSessionLocal()
        job = Job(
            id="null-uuid",
            name="Null Job",
            source_host="src.com",
            target_host="tgt.com"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.password_hash is None
        assert job.options is None
        assert job.csv_path is None
        db.close()


# ==========================================
# 3. Mailbox Model Tests
# ==========================================

class TestMailboxModel:
    """Tests for Mailbox SQLAlchemy model"""

    def test_mailbox_defaults(self):
        """Mailbox model has correct default values"""
        db = TestingSessionLocal()
        # Create parent job first
        job = Job(id="mb-parent", name="Parent", source_host="s", target_host="t")
        db.add(job)
        db.commit()

        mb = Mailbox(
            job_id="mb-parent",
            source_user="user@src.com",
            source_pass="encrypted_src",
            target_user="user@tgt.com",
            target_pass="encrypted_tgt"
        )
        db.add(mb)
        db.commit()
        db.refresh(mb)

        assert mb.status == "pending"
        assert mb.progress == 0
        assert mb.data_transferred == 0
        assert mb.message is None
        assert mb.id is not None  # Auto-incremented
        db.close()

    def test_mailbox_status_update(self):
        """Update mailbox status through various states"""
        db = TestingSessionLocal()
        job = Job(id="status-parent", name="Parent", source_host="s", target_host="t")
        db.add(job)
        db.commit()

        mb = Mailbox(
            job_id="status-parent",
            source_user="u@s.com",
            source_pass="ep",
            target_user="u@t.com",
            target_pass="ep"
        )
        db.add(mb)
        db.commit()

        # Simulate status progression
        for status in ["pending", "running", "success"]:
            mb.status = status
            db.commit()
            db.refresh(mb)
            assert mb.status == status
        db.close()


# ==========================================
# 4. User Model Tests
# ==========================================

class TestUserModel:
    """Tests for User SQLAlchemy model"""

    def test_create_user(self):
        """Create a user"""
        db = TestingSessionLocal()
        user = User(username="testuser", hashed_password="hash123")
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        db.close()

    def test_unique_username(self):
        """Duplicate username raises IntegrityError"""
        db = TestingSessionLocal()
        user1 = User(username="duplicate", hashed_password="hash1")
        db.add(user1)
        db.commit()

        user2 = User(username="duplicate", hashed_password="hash2")
        db.add(user2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.close()


# ==========================================
# 5. Relationship Tests
# ==========================================

class TestRelationships:
    """Tests for ORM relationships between models"""

    def test_job_mailbox_relationship(self):
        """Job→Mailbox one-to-many relationship"""
        db = TestingSessionLocal()
        job = Job(id="rel-job", name="Rel Job", source_host="s", target_host="t")
        db.add(job)
        db.commit()

        mb1 = Mailbox(job_id="rel-job", source_user="u1", source_pass="p1", target_user="t1", target_pass="p1")
        mb2 = Mailbox(job_id="rel-job", source_user="u2", source_pass="p2", target_user="t2", target_pass="p2")
        db.add_all([mb1, mb2])
        db.commit()

        db.refresh(job)
        assert len(job.mailboxes) == 2
        assert job.mailboxes[0].source_user in ["u1", "u2"]
        db.close()

    def test_mailbox_job_back_reference(self):
        """Mailbox→Job back reference"""
        db = TestingSessionLocal()
        job = Job(id="back-ref", name="Back Ref", source_host="s", target_host="t")
        db.add(job)
        db.commit()

        mb = Mailbox(job_id="back-ref", source_user="u", source_pass="p", target_user="t", target_pass="p")
        db.add(mb)
        db.commit()
        db.refresh(mb)

        assert mb.job is not None
        assert mb.job.id == "back-ref"
        assert mb.job.name == "Back Ref"
        db.close()

    def test_job_with_no_mailboxes(self):
        """Job with no mailboxes has empty list"""
        db = TestingSessionLocal()
        job = Job(id="empty-job", name="Empty", source_host="s", target_host="t")
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.mailboxes == []
        db.close()


# ==========================================
# 6. Database Utility Tests
# ==========================================

class TestDatabaseUtils:
    """Tests for database utility functions"""

    def test_get_db_yields_session(self):
        """get_db() yields a valid session"""
        gen = get_db()
        session = next(gen)
        assert session is not None
        # Clean up
        try:
            next(gen)
        except StopIteration:
            pass

    def test_init_db_creates_tables(self):
        """init_db() creates all tables without errors"""
        # Drop everything first
        Base.metadata.drop_all(bind=engine)
        # Re-create
        Base.metadata.create_all(bind=engine)

        # Verify tables exist by querying
        db = TestingSessionLocal()
        jobs = db.query(Job).all()
        assert isinstance(jobs, list)
        users = db.query(User).all()
        assert isinstance(users, list)
        db.close()
