from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Request, Response, Query
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import csv
import io
import os
import sys
import logging
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)

# Add current directory to sys.path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Job, Mailbox, User, get_db, init_db
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

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

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


# --- Auth Routes ---
@app.post("/api/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Auto-create admin user if not exists (For simple setup)
    # Password should be set via environment variable
    if not user and form_data.username == "phongdh":
        admin_password = os.getenv("ADMIN_PASSWORD", "changeme123")
        user = User(username="phongdh", hashed_password=get_password_hash(admin_password))
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
class JobCreate(BaseModel):
    name: str = "Migration Job"
    source_host: str
    target_host: str
    source_port: int = 993
    target_port: int = 993
    source_security: str = "SSL/TLS"
    target_security: str = "SSL/TLS"
    options: dict = {} # JSON Options
    password: str # Mandatory password protection

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
    data_transferred: str = "0 B" # Formatted string
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
async def create_job(job_data: JobCreate, background_tasks: BackgroundTasks, response: Response, db: Session = Depends(get_db)):
    try:
        job_id = str(uuid.uuid4())
    
        # Process Options
        import json
        options_json = json.dumps(job_data.options)
        
        # Hash password if provided
        password_hash = None
        if job_data.password:
            password_hash = get_password_hash(job_data.password)
            # Set cookie from backend for reliability
            response.set_cookie(
                key="job_password", 
                value=quote(job_data.password, safe=''), 
                max_age=3600*24, 
                httponly=False,
                samesite="lax"
            )
        
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
            password_hash=password_hash,
            status="running" # Auto start for demo
        )
        db.add(db_job)
        db.commit()
        return format_job_response(db_job)
    except Exception as e:
        with open("error_log.txt", "a") as f:
            import traceback
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))

from concurrent.futures import ThreadPoolExecutor

# Global Executor
max_workers = int(os.getenv("MAX_WORKERS", 7))
executor = ThreadPoolExecutor(max_workers=max_workers) 

@app.post("/api/jobs/{job_id}/mailboxes")
async def add_single_mailbox(job_id: str, mailbox_data: MailboxCreate, db: Session = Depends(get_db)):
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
async def upload_csv(job_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
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

@app.delete("/api/jobs")
def delete_all_jobs(db: Session = Depends(get_db)):
    # Check if any jobs are currently running
    active_jobs = db.query(Job).filter(Job.status == "running").count()
    if active_jobs > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete history while {active_jobs} jobs are still running. Please stop them first."
        )
    
    try:
        # Delete Log Files
        import shutil
        log_dir = "logs"
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                file_path = os.path.join(log_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')

        # Delete DB Records
        db.query(Mailbox).delete()
        db.query(Job).delete()
        db.commit()
        return {"message": "All jobs and history deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/jobs/{job_id}")
def delete_single_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status == "running":
        raise HTTPException(status_code=400, detail="Cannot delete a job that is currently running. Please stop it first.")
    
    try:
        # 1. Delete associated log files
        mailboxes = db.query(Mailbox).filter(Mailbox.job_id == job_id).all()
        for mb in mailboxes:
            log_path = f"logs/{mb.id}.log"
            if os.path.exists(log_path):
                try:
                    os.remove(log_path)
                except Exception as e:
                    print(f"Error removing log {log_path}: {e}")
        
        # 2. Delete DB records
        db.query(Mailbox).filter(Mailbox.job_id == job_id).delete()
        db.delete(job)
        db.commit()
        
        return {"message": f"Job {job_id} and its mailboxes/logs deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        return [format_job_response(j) for j in jobs]
    except Exception as e:
        with open("error_log.txt", "a") as f:
            import traceback
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Header, Query, Cookie
from typing import Optional

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request, db: Session = Depends(get_db), password: Optional[str] = Query(None), job_password: Optional[str] = Cookie(None)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Password verification
    if job.password_hash:
        x_job_password = request.headers.get("X-Job-Password")
        
        # Priority: 1. Query Param, 2. Header, 3. Cookie (URL-decoded)
        cookie_password = unquote(job_password) if job_password else None
        effective_password = password or x_job_password or cookie_password
        

        if not effective_password:
            raise HTTPException(
                status_code=401, 
                detail="Password required",
                headers={"X-Password-Required": "true"}
            )
        
        if not verify_password(effective_password, job.password_hash):
            logger.warning(f"Password mismatch for job {job_id}")
            raise HTTPException(status_code=401, detail="Incorrect password")
    
    
    # Self-heal / Real-time Stats Calculation
    # Trust the mailboxes table more than the job counters
    completed_count = db.query(Mailbox).filter(Mailbox.job_id == job_id, Mailbox.status.in_(['success', 'warning'])).count()
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
    
    # Calculate progress for response - use average progress of all mailboxes
    progress = 0
    if job.total_mailboxes > 0:
        # Calculate average progress from all mailboxes
        total_progress = sum(mb.progress for mb in mailboxes)
        progress = int(total_progress / job.total_mailboxes)

    # Format Data Transferred
    bytes_val = job.data_transferred or 0
    if bytes_val > 1024**3:
        data_str = f"{bytes_val / (1024**3):.2f} GB"
    elif bytes_val > 1024**2:
        data_str = f"{bytes_val / (1024**2):.2f} MB"
    elif bytes_val > 1024:
        data_str = f"{bytes_val / 1024:.2f} KB"
    else:
        data_str = f"{bytes_val} B"

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
        "data_transferred": data_str,
        "created_at": str(job.created_at),
        "mailboxes": [
            {
                "id": mb.id,
                "user": mb.source_user,
                "target_user": mb.target_user,
                "status": mb.status,
                "progress": mb.progress,
                "msg": mb.message
            } for mb in mailboxes
        ]
    }

@app.get("/api/mailboxes/{mailbox_id}/logs")
def get_mailbox_logs(mailbox_id: int, request: Request, db: Session = Depends(get_db), password: Optional[str] = Query(None), job_password: Optional[str] = Cookie(None)):
    mb = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mb:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    
    # Password verification for parent job
    job = db.query(Job).filter(Job.id == mb.job_id).first()
    if job and job.password_hash:
        x_job_password = request.headers.get("X-Job-Password")
        cookie_password = unquote(job_password) if job_password else None
        effective_password = password or x_job_password or cookie_password
        
        if not effective_password or not verify_password(effective_password, job.password_hash):
            raise HTTPException(status_code=401, detail="Password required")
    
    log_path = f"logs/{mailbox_id}.log"
    
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return {"logs": f.read()}
    
    return {"logs": f"Waiting for logs / Starting process...\nStatus: {mb.status}\nMessage: {mb.message}"}

@app.get("/api/jobs/{job_id}/logs/zip")
def download_logs_zip(job_id: str, request: Request, db: Session = Depends(get_db), password: Optional[str] = Query(None), job_password: Optional[str] = Cookie(None)):
    """Download all logs for a job as a ZIP file"""
    import zipfile
    from io import BytesIO

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Password verification
    if job.password_hash:
        x_job_password = request.headers.get("X-Job-Password")
        cookie_password = unquote(job_password) if job_password else None
        effective_password = password or x_job_password or cookie_password
        
        if not effective_password or not verify_password(effective_password, job.password_hash):
            raise HTTPException(status_code=401, detail="Password required")

    # Create ZIP in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add summary file
        summary = f"Job: {job.name}\nSource: {job.source_host}\nTarget: {job.target_host}\nDate: {job.created_at}\n"
        zf.writestr("summary.txt", summary)

        # Add each mailbox log
        mailboxes = db.query(Mailbox).filter(Mailbox.job_id == job_id).all()
        for mb in mailboxes:
            log_path = f"logs/{mb.id}.log"
            if os.path.exists(log_path):
                # Clean filename: user_source_to_user_target.log
                clean_source = mb.source_user.replace("@", "_at_").replace(".", "_")
                clean_target = mb.target_user.replace("@", "_at_").replace(".", "_")
                filename = f"{clean_source}_to_{clean_target}.log"
                
                with open(log_path, "r") as f:
                    zf.writestr(filename, f.read())
            else:
                 # Add even if log missing, noting status
                 clean_source = mb.source_user.replace("@", "_at_").replace(".", "_")
                 filename = f"{clean_source}_no_log.txt"
                 zf.writestr(filename, f"No log found.\nStatus: {mb.status}\nMessage: {mb.message}")

    memory_file.seek(0)
    
    # Generate filename
    clean_job_name = job.name.replace(" ", "_").replace("/", "").replace("\\", "")
    zip_filename = f"logs_{clean_job_name}.zip"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        memory_file, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )

class PasswordVerify(BaseModel):
    password: str

@app.post("/api/jobs/{job_id}/verify")
def verify_job_password(job_id: str, data: PasswordVerify, response: Response, db: Session = Depends(get_db)):
    """Verify password for a job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Job has no password
    if not job.password_hash:
        return {"valid": True, "password_required": False}
    
    # Verify password
    if verify_password(data.password, job.password_hash):
        # Set cookie from backend for reliability
        response.set_cookie(
            key="job_password", 
            value=quote(data.password, safe=''), 
            max_age=3600*24, # 1 day
            httponly=False,  # Allow JS access for redundancy if needed
            samesite="lax"
        )
        return {"valid": True, "password_required": True}
    else:
        raise HTTPException(status_code=401, detail="Incorrect password")

@app.post("/api/mailboxes/{mailbox_id}/stop")
def stop_mailbox_sync(mailbox_id: int, db: Session = Depends(get_db)):
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

@app.post("/api/mailboxes/{mailbox_id}/retry")
def retry_mailbox_sync(mailbox_id: int, db: Session = Depends(get_db)):
    mb = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mb:
        raise HTTPException(status_code=404, detail="Mailbox not found")
        
    if mb.status == 'running':
         raise HTTPException(status_code=400, detail="Mailbox is already running")

    # Reset Status
    mb.status = 'pending'
    mb.message = 'Queued for retry'
    # Optional: Reset data transferred? 
    # mb.data_transferred = 0 
    
    # Update Job stats logic if needed (e.g. decrement failed count)
    job = db.query(Job).filter(Job.id == mb.job_id).first()
    if job:
        # If it was failed, decrement failed count to reflect it's active again
        # But our real-time stats in get_job will handle it based on status count.
        # Just ensure status is set to running if job was completed?
        if job.status == 'completed' or job.status == 'failed':
            job.status = 'running'
            
    db.commit()
    
    # Re-submit to executor
    executor.submit(run_imapsync, mb.id)
    
    return {"message": "Mailbox retry started", "mailbox_id": mb.id}

@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel all running mailboxes in a job"""
    from worker import kill_sync
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get all running mailboxes
    running_mailboxes = db.query(Mailbox).filter(
        Mailbox.job_id == job_id, 
        Mailbox.status == 'running'
    ).all()
    
    cancelled_count = 0
    for mb in running_mailboxes:
        success = kill_sync(mb.id)
        if success:
            mb.status = 'failed'
            mb.message = 'Cancelled by user'
            cancelled_count += 1
    
    # Update job status
    if cancelled_count > 0:
        job.status = 'failed'
    
    db.commit()
    
    return {"message": f"Cancelled {cancelled_count} mailboxes", "cancelled": cancelled_count}

# --- Check Credentials API (Public) ---
from check_credentials import check_imap_login, check_bulk, detect_provider, PROVIDER_MAP

class CredentialCheck(BaseModel):
    email: str
    password: str
    host: Optional[str] = None  # Optional, auto-detect from email domain
    port: int = 993

@app.post("/api/check-credentials")
async def check_single_credential(data: CredentialCheck):
    """Check a single email credential via IMAP login."""
    result = check_imap_login(
        email=data.email,
        password=data.password,
        host=data.host,
        port=data.port
    )
    return result

@app.post("/api/check-credentials/bulk")
async def check_bulk_credentials(
    file: UploadFile = File(...),
    host: str = Query(None),
    port: int = Query(993)
):
    """Check multiple credentials from a CSV file (format: email,password per line)."""
    content = await file.read()
    csv_text = content.decode('utf-8')

    import csv as csv_module
    reader = csv_module.reader(io.StringIO(csv_text))

    credentials = []
    for row in reader:
        if len(row) < 2:
            continue
        email = row[0].strip()
        password = row[1].strip()
        if email and password:
            credentials.append({"email": email, "password": password})

    if not credentials:
        raise HTTPException(status_code=400, detail="No valid credentials found in CSV. Format: email,password")

    results = check_bulk(credentials, host=host, port=port, max_concurrent=5)

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    return {
        "results": results,
        "total": len(results),
        "success_count": success_count,
        "failed_count": failed_count
    }

@app.get("/api/providers")
def list_providers():
    """List supported email providers."""
    seen = {}
    for domain, info in PROVIDER_MAP.items():
        name = info["name"]
        if name not in seen:
            seen[name] = {"name": name, "host": info["host"], "port": info["port"], "domains": []}
        seen[name]["domains"].append(domain)
    return list(seen.values())

@app.get("/api/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
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

    # Format Bytes
    bytes_val = job.data_transferred or 0
    if bytes_val > 1024**3:
        data_str = f"{bytes_val / (1024**3):.2f} GB"
    elif bytes_val > 1024**2:
        data_str = f"{bytes_val / (1024**2):.2f} MB"
    elif bytes_val > 1024:
         data_str = f"{bytes_val / 1024:.2f} KB"
    else:
         data_str = f"{bytes_val} B"
        
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
        data_transferred=data_str,
        created_at=job.created_at.isoformat()
    )

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

@app.get("/index.html")
async def read_index():
    return serve_html('index.html')


@app.get("/create-job.html")
async def read_create_job():
    return serve_html('create-job.html')

@app.get("/job-detail.html")
async def read_job_detail():
    return serve_html('job-detail.html')

@app.get("/guide.html")
async def read_guide():
    return serve_html('guide.html')

@app.get("/check-credentials.html")
async def read_check_credentials():
    return serve_html('check-credentials.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
