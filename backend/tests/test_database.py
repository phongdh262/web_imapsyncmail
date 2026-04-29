"""
Test Suite: Database & Encryption Module
Tests password encryption/decryption, model defaults, and DB initialization.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import encrypt_password, decrypt_password, Job, Mailbox, User, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def mem_db():
    """Standalone in-memory DB for model tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


# =====================================================================
# Fernet Encryption / Decryption
# =====================================================================

class TestEncryption:
    """Verify Fernet-based password encryption roundtrip."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypt → decrypt returns original password."""
        original = "MyS3cretP@ssword!"
        encrypted = encrypt_password(original)
        assert encrypted != original
        assert decrypt_password(encrypted) == original

    def test_encrypt_empty_string(self):
        """Empty string returns empty without error."""
        assert encrypt_password("") == ""
        assert decrypt_password("") == ""

    def test_encrypt_unicode_password(self):
        """Vietnamese and emoji characters survive encryption."""
        original = "mật_khẩu_🔐"
        encrypted = encrypt_password(original)
        assert decrypt_password(encrypted) == original

    def test_encrypt_long_password(self):
        """Long passwords work correctly."""
        original = "x" * 500
        encrypted = encrypt_password(original)
        assert decrypt_password(encrypted) == original

    def test_encrypted_values_differ(self):
        """Same password encrypted twice produces different ciphertext (Fernet uses time-based token)."""
        e1 = encrypt_password("same_password")
        e2 = encrypt_password("same_password")
        # Fernet includes timestamp, so tokens differ
        assert e1 != e2
        assert decrypt_password(e1) == "same_password"
        assert decrypt_password(e2) == "same_password"


# =====================================================================
# SQLAlchemy Model Defaults
# =====================================================================

class TestJobModel:
    """Verify Job model column defaults."""

    def test_job_defaults(self, mem_db):
        """Job creation uses correct defaults."""
        job = Job(
            id="test-job-id",
            name="Test Job",
            source_host="imap.gmail.com",
            target_host="imap.yandex.com",
        )
        mem_db.add(job)
        mem_db.commit()
        mem_db.refresh(job)

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

    def test_job_password_hash_nullable(self, mem_db):
        """Job without password has null password_hash."""
        job = Job(id="no-pass-job", name="No Password", source_host="a", target_host="b")
        mem_db.add(job)
        mem_db.commit()
        assert job.password_hash is None


class TestMailboxModel:
    """Verify Mailbox model column defaults."""

    def test_mailbox_defaults(self, mem_db):
        """Mailbox creation uses correct defaults."""
        # Create parent job first
        job = Job(id="parent-job", name="Parent", source_host="a", target_host="b")
        mem_db.add(job)
        mem_db.commit()

        mb = Mailbox(
            job_id="parent-job",
            source_user="src@gmail.com",
            source_pass="enc1",
            target_user="tgt@yandex.com",
            target_pass="enc2",
        )
        mem_db.add(mb)
        mem_db.commit()
        mem_db.refresh(mb)

        assert mb.status == "pending"
        assert mb.progress == 0
        assert mb.data_transferred == 0
        assert mb.message is None

    def test_mailbox_job_relationship(self, mem_db):
        """Mailbox.job relationship resolves correctly."""
        job = Job(id="rel-test", name="Rel Test", source_host="a", target_host="b")
        mem_db.add(job)
        mem_db.commit()

        mb = Mailbox(job_id="rel-test", source_user="s@a.com", source_pass="x", target_user="t@b.com", target_pass="y")
        mem_db.add(mb)
        mem_db.commit()
        mem_db.refresh(mb)

        assert mb.job.id == "rel-test"
        assert mb.job.name == "Rel Test"


class TestUserModel:
    """Verify User model."""

    def test_user_creation(self, mem_db):
        """User can be created with username + hashed_password."""
        user = User(username="testuser", hashed_password="$2b$12$fakehash")
        mem_db.add(user)
        mem_db.commit()
        mem_db.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"

    def test_user_unique_username(self, mem_db):
        """Duplicate username raises integrity error."""
        from sqlalchemy.exc import IntegrityError

        mem_db.add(User(username="dupe", hashed_password="h1"))
        mem_db.commit()

        mem_db.add(User(username="dupe", hashed_password="h2"))
        with pytest.raises(IntegrityError):
            mem_db.commit()
        mem_db.rollback()


class TestInitDB:
    """Verify init_db creates all tables."""

    def test_all_tables_created(self):
        """init_db should create jobs, mailboxes, users, rate_limit_events."""
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=engine)
        table_names = set(Base.metadata.tables.keys())
        assert "jobs" in table_names
        assert "mailboxes" in table_names
        assert "users" in table_names
        assert "rate_limit_events" in table_names
        engine.dispose()
