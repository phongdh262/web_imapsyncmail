import time
import subprocess
import os
import sys

# Add current directory to sys.path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tempfile
import signal
from sqlalchemy.orm import Session
from database import SessionLocal, Mailbox, engine, Job

# Global registry for running processes {mailbox_id: process_object}
active_processes = {}

def kill_sync(mailbox_id: int):
    """
    Terminates the sync process for a specific mailbox.
    """
    if mailbox_id in active_processes:
        try:
            process = active_processes[mailbox_id]
            process.terminate() # or process.kill()
            # process.wait() # Avoid blocking here, let the worker thread handle the exit
            return True
        except Exception as e:
            print(f"Error killing process {mailbox_id}: {e}")
            return False
    return False

def run_imapsync(mailbox_id: int):
    """
    Executes the real imapsync process.
    """
    db: Session = SessionLocal()
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        return

    job = db.query(Job).filter(Job.id == mailbox.job_id).first()
    
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file_path = f"{log_dir}/{mailbox.id}.log"
    
    try:
        mailbox.status = 'running'
        mailbox.message = "Starting imapsync..."
        db.commit()

        # Decrypt passwords
        from database import decrypt_password
        import json
        
        source_pass = decrypt_password(mailbox.source_pass)
        target_pass = decrypt_password(mailbox.target_pass)

        # Create temp files for passwords securely
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f_pass1, \
             tempfile.NamedTemporaryFile(mode='w', delete=False) as f_pass2:
            
            f_pass1.write(source_pass)
            f_pass1.flush()
            pass1_path = f_pass1.name
            
            f_pass2.write(target_pass)
            f_pass2.flush()
            pass2_path = f_pass2.name
        
        # Parse Options
        options = {}
        if job.options:
            try:
                options = json.loads(job.options)
            except:
                pass

        # Build Command
        cmd = [
            'imapsync',
            '--host1', job.source_host,
            '--port1', str(job.source_port),
            '--user1', mailbox.source_user,
            '--passfile1', pass1_path,
            '--host2', job.target_host,
            '--port2', str(job.target_port),
            '--user2', mailbox.target_user,
            '--passfile2', pass2_path,
            '--automap',
            '--nofoldersizes'
        ]
        
        # Security Flags
        if job.source_security == "SSL/TLS":
            cmd.append('--ssl1')
        elif job.source_security == "STARTTLS":
            cmd.append('--tls1')
            
        if job.target_security == "SSL/TLS":
            cmd.append('--ssl2')
        elif job.target_security == "STARTTLS":
            cmd.append('--tls2')
            
        # Feature Flags
        if options.get('sync_internal_dates'):
            cmd.append('--syncinternaldates')
        
        if options.get('skip_trash'):
             # Common trash folder names, can be expanded
            cmd.extend(['--exclude', 'Trash', '--exclude', 'Bin', '--exclude', 'Deleted Items'])
            
        if options.get('dry_run'):
            cmd.append('--dry')

        # Execute
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Register process
            active_processes[mailbox_id] = process
            
            # Stream logs
            import re
            total_bytes = 0
            
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
                
                # Parse Data Transfer
                # Parse Data Transfer
                # Pattern 1: Final summary "Total bytes transferred : 123456"
                if "Total bytes transferred" in line:
                    match = re.search(r'Total bytes transferred.*?:\s*(\d+)', line, re.IGNORECASE)
                    if match:
                         try:
                             total_bytes = int(match.group(1))
                         except: pass
                
                # Pattern 2: "Detected 12 messages ... Total size: 123456 bytes" (Estimation)
                # Use this if we haven't found the final yet, but accurate final is better.
                elif "Total size" in line and "bytes" in line and total_bytes == 0:
                     match = re.search(r'Total size.*?:\s*(\d+)', line, re.IGNORECASE)
                     if match:
                         try:
                             total_bytes = int(match.group(1))
                         except: pass

            process.wait()
            
            # Update Stats
            if total_bytes > 0:
                mailbox.data_transferred = total_bytes
                job.data_transferred += total_bytes
            
            # Cleanup registry
            if mailbox_id in active_processes:
                del active_processes[mailbox_id]

            # Cleanup temp files
            if os.path.exists(pass1_path): os.unlink(pass1_path)
            if os.path.exists(pass2_path): os.unlink(pass2_path)

            if process.returncode == 0:
                mailbox.status = 'success'
                mailbox.message = "Sync Completed Successfully"
                job.completed += 1
            elif process.returncode == -15 or process.returncode == -9: # Terminated
                mailbox.status = 'failed'
                mailbox.message = "Stopped by user"
            else:
                mailbox.status = 'failed'
                mailbox.message = f"Exited with code {process.returncode}. Check logs."


    except Exception as e:
        mailbox.status = 'failed'
        mailbox.message = str(e)
        # if job: job.failed += 1 # Don't update blindly
        with open(log_file_path, "a") as log_file:
            log_file.write(f"\nCRITICAL ERROR: {str(e)}\n")
            
    finally:
        # Final cleanup safety
        if mailbox_id in active_processes:
            del active_processes[mailbox_id]
        
        # Recalculate Job Stats to avoid race conditions and check completion
            # Recalculate Job Stats to avoid race conditions and check completion
        if job:
            from sqlalchemy import func
            completed_count = db.query(Mailbox).filter(Mailbox.job_id == job.id, Mailbox.status == 'success').count()
            failed_count = db.query(Mailbox).filter(Mailbox.job_id == job.id, Mailbox.status == 'failed').count()
            
            # Recalculate Data Transferred
            total_job_bytes = db.query(func.sum(Mailbox.data_transferred)).filter(Mailbox.job_id == job.id).scalar() or 0
            job.data_transferred = total_job_bytes

            job.completed = completed_count
            job.failed = failed_count
            
            # Check completion
            if (job.completed + job.failed) >= job.total_mailboxes:
                job.status = 'completed'

        db.commit()
        db.close()

