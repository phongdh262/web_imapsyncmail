from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
from cryptography.fernet import Fernet
import os

from dotenv import load_dotenv
import os

load_dotenv()

# MySQL Connection from Env
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback or Error
    DATABASE_URL = "sqlite:///./imapsync.db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Encryption Key Management (Simple File-based for now)
KEY_FILE = "secret.key"
def load_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as key_file:
            return key_file.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
        return key

cipher_suite = Fernet(load_key())

def encrypt_password(password: str) -> str:
    if not password: return ""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(token: str) -> str:
    if not token: return ""
    return cipher_suite.decrypt(token.encode()).decode()

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255))
    status = Column(String(50), default="pending") # pending, running, completed, failed
    
    # Source Config
    source_host = Column(String(255))
    source_port = Column(Integer, default=993)
    source_security = Column(String(50), default="SSL/TLS") # SSL/TLS, STARTTLS, None
    
    # Target Config
    target_host = Column(String(255))
    target_port = Column(Integer, default=993)
    target_security = Column(String(50), default="SSL/TLS") # SSL/TLS, STARTTLS, None
    
    # Migration Options
    options = Column(Text, nullable=True) # JSON String for flexibility
    
    csv_path = Column(String(500), nullable=True)
    
    # Stats
    total_mailboxes = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    data_transferred = Column(Integer, default=0) # Bytes
    
    created_at = Column(DateTime, default=datetime.utcnow)

    mailboxes = relationship("Mailbox", back_populates="job")

class Mailbox(Base):
    __tablename__ = "mailboxes"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id"))
    
    source_user = Column(String(255))
    source_pass = Column(String(500)) # Encrypted
    target_user = Column(String(255))
    target_pass = Column(String(500)) # Encrypted
    
    status = Column(String(50), default="pending") # pending, running, success, failed
    message = Column(Text, nullable=True)
    data_transferred = Column(Integer, default=0) # Bytes
    
    job = relationship("Job", back_populates="mailboxes")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))

def init_db():
    Base.metadata.create_all(bind=engine)
