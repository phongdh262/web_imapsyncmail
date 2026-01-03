from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import uuid
import csv
import io
import os
from database import SessionLocal, engine, init_db, Job, Mailbox, User
from auth import Token, get_current_user, create_access_token, verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from pydantic import BaseModel
from worker import run_imapsync

# Initialize DB safely
try:
    init_db()
    print("Database initialized successfully.")
except Exception as e:
    error_msg = f"Failed to initialize database: {str(e)}"
    print(error_msg)
    # Log to file for cPanel visibility
    try:
        with open("startup_error.log", "a") as f:
            import datetime
            f.write(f"[{datetime.datetime.now()}] {error_msg}\n")
    except:
        pass

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check ---
@app.get("/api/health")
def health_check():
    """Diagnostic endpoint for cPanel deployment"""
    import sys
    import shutil
    
    # Check DB
    db_status = "unknown"
    try:
        import sqlalchemy
        db = SessionLocal()
        db.execute(sqlalchemy.text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    # Check imapsync
    imapsync_path = shutil.which("imapsync")
    
    return {
        "status": "ok",
        "python": sys.version,
        "cwd": os.getcwd(),
        "database": db_status,
        "imapsync": imapsync_path or "not found"
    }

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth Routes ---
@app.post("/api/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Auto-create admin user if not exists (For simple setup)
    if not user and form_data.username == "phongdh":
        user = User(username="phongdh", hashed_password=get_password_hash(r"%1yedJck}KC]>%:K{e)."))
        db.add(user)
        db.commit()
        db.refresh(user)
        
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Pydantic Schemas
# Pydantic Schemas
class JobCreate(BaseModel):
    name: str = "Migration Job"
    source_host: str
    target_host: str
    source_port: int = 993
    target_port: int = 993
    source_security: str = "SSL/TLS"
    target_security: str = "SSL/TLS"
    options: dict = {} # JSON Options

class JobResponse(BaseModel):
    id: str
    name: str
    status: str
    progress: int = 0
    total: int = 0
    completed: int = 0
    failed: int = 0
    source: str
    target: str
    created_at: str

    class Config:
        from_attributes = True

class MailboxCreate(BaseModel):
    source_user: str
    source_pass: str
    target_user: str
    target_pass: str

# API Routes
@app.post("/api/jobs", response_model=JobResponse)
async def create_job(job_data: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    
    # Process Options
    import json
    options_json = json.dumps(job_data.options)
    
    db_job = Job(
        id=job_id,
        name=job_data.name,
        source_host=job_data.source_host,
        target_host=job_data.target_host,
        source_port=job_data.source_port,
        target_port=job_data.target_port,
        source_security=job_data.source_security,
        target_security=job_data.target_security,
        options=options_json,
        status="running" # Auto start for demo
    )
    db.add(db_job)
    db.commit()
    return format_job_response(db_job)

from concurrent.futures import ThreadPoolExecutor

# Global Executor
max_workers = int(os.getenv("MAX_WORKERS", 2))
executor = ThreadPoolExecutor(max_workers=max_workers) 

@app.post("/api/jobs/{job_id}/mailboxes")
async def add_single_mailbox(job_id: str, mailbox_data: MailboxCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from database import encrypt_password
    
    mb = Mailbox(
        job_id=job_id,
        source_user=mailbox_data.source_user,
        source_pass=encrypt_password(mailbox_data.source_pass),
        target_user=mailbox_data.target_user,
        target_pass=encrypt_password(mailbox_data.target_pass)
    )
    db.add(mb)
    
    job.total_mailboxes += 1
    
    db.commit()
    
    # Submit task
    executor.submit(run_imapsync, mb.id)
    
    return {"message": "Mailbox added and started", "mailbox_id": mb.id}

@app.post("/api/upload/{job_id}")
async def upload_csv(job_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    content = await file.read()
    csv_text = content.decode('utf-8')
    reader = csv.reader(io.StringIO(csv_text))
    
    from database import encrypt_password
    
    count = 0
    mailboxes = []
    for row in reader:
        if len(row) < 4: continue
        mb = Mailbox(
            job_id=job_id,
            source_user=row[0],
            source_pass=encrypt_password(row[1]),
            target_user=row[2],
            target_pass=encrypt_password(row[3])
        )
        db.add(mb)
        # Add to list to commit later or commit one by one? 
        # Commit one by one is safer for getting IDs.
        db.commit()
        mailboxes.append(mb)
        count += 1

    job.total_mailboxes += count # Increment instead of overwrite to support mixed usage
    db.commit()

    # Submit tasks to executor for parallel execution
    for mb in mailboxes:
        executor.submit(run_imapsync, mb.id)

    return {"message": f"Started {count} mailboxes"}

@app.get("/api/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [format_job_response(j) for j in jobs]

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Self-heal / Real-time Stats Calculation
    # Trust the mailboxes table more than the job counters
    completed_count = db.query(Mailbox).filter(Mailbox.job_id == job_id, Mailbox.status == 'success').count()
    failed_count = db.query(Mailbox).filter(Mailbox.job_id == job_id, Mailbox.status == 'failed').count()
    
    # Update Job record if out of sync
    if job.completed != completed_count or job.failed != failed_count:
        job.completed = completed_count
        job.failed = failed_count
        
        # Check for completion
        if job.total_mailboxes > 0 and (completed_count + failed_count) >= job.total_mailboxes:
             if job.status == 'running':
                 job.status = 'completed'
        
        db.commit()
        db.refresh(job)

    # Get mailboxes for details
    mailboxes = db.query(Mailbox).filter(Mailbox.job_id == job_id).all()
    
    # Calculate progress for response
    progress = 0
    if job.total_mailboxes > 0:
        progress = int(((job.completed + job.failed) / job.total_mailboxes) * 100)

    # We need to construct the response manually to override what might be in the DB temporarily
    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "progress": progress,
        "total": job.total_mailboxes,
        "completed": job.completed,
        "failed": job.failed,
        "source": job.source_host,
        "target": job.target_host,
        "created_at": str(job.created_at),
        "mailboxes": [
            {
                "id": mb.id,
                "user": mb.source_user,
                "target_user": mb.target_user,
                "status": mb.status,
                "msg": mb.message
            } for mb in mailboxes
        ]
    }

@app.get("/api/mailboxes/{mailbox_id}/logs")
def get_mailbox_logs(mailbox_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mb = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mb:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    
    log_path = f"logs/{mailbox_id}.log"
    
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return {"logs": f.read()}
    
    return {"logs": f"Waiting for logs / Starting process...\nStatus: {mb.status}\nMessage: {mb.message}"}

@app.post("/api/mailboxes/{mailbox_id}/stop")
def stop_mailbox_sync(mailbox_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from worker import kill_sync
    # Kill the process
    success = kill_sync(mailbox_id)
    
    # Update DB immediately (in case worker doesn't correct it fast enough)
    mb = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if mb and mb.status == 'running':
        mb.status = 'failed'
        mb.message = 'Stopped by user'
        db.commit()
        
    if success:
        return {"message": "Process terminated"}
    else:
        # Could be already stopped
        return {"message": "Process not found or already stopped"}

@app.get("/api/stats")
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import func
    total_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.status == "running").count()
    completed_mailboxes = db.query(Mailbox).filter(Mailbox.status == "success").count()
    
    # Calculate Data Transferred
    total_bytes = db.query(func.sum(Job.data_transferred)).scalar() or 0
    
    # Format
    if total_bytes > 1024**3:
        data_str = f"{total_bytes / (1024**3):.2f} GB"
    elif total_bytes > 1024**2:
        data_str = f"{total_bytes / (1024**2):.2f} MB"
    elif total_bytes > 1024:
        data_str = f"{total_bytes / 1024:.2f} KB"
    else:
        data_str = f"{total_bytes} B"

    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "completed_mailboxes": completed_mailboxes,
        "data_transferred": data_str
    }

def format_job_response(job: Job):
    progress = 0
    if job.total_mailboxes > 0:
        progress = int(((job.completed + job.failed) / job.total_mailboxes) * 100)
        
    return JobResponse(
        id=job.id,
        name=job.name or "Untitled",
        status=job.status,
        progress=progress,
        total=job.total_mailboxes,
        completed=job.completed,
        failed=job.failed,
        source=job.source_host,
        target=job.target_host,
        created_at=job.created_at.isoformat()
    )

# Mount Static Files (Frontend)
# Mount Static Files (Frontend)
# Use absolute path relative to this file to ensure it works on cPanel
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from fastapi.responses import HTMLResponse

# Mount Static Assets
# Note: StaticFiles needs 'aiofiles' installed.
app.mount("/css", StaticFiles(directory=os.path.join(base_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(base_dir, "js")), name="js")

def serve_html(filename):
    path = os.path.join(base_dir, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
             return HTMLResponse(content=f.read())
    return HTMLResponse(content=f"File not found: {path} (Base: {base_dir})", status_code=404)

# Serve HTML Files explicitly (Sync read is safer without aiofiles)
@app.get("/")
async def read_root():
    return serve_html('index.html')

@app.get("/login.html")
async def read_login():
    return serve_html('login.html')

@app.get("/create-job.html")
async def read_create_job():
    return serve_html('create-job.html')

@app.get("/job-detail.html")
async def read_job_detail():
    return serve_html('job-detail.html')

@app.get("/guide.html")
async def read_guide():
    return serve_html('guide.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
