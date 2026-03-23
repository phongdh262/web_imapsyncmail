import time
import subprocess
import os
import sys
import stat
import glob

# Add current directory to sys.path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tempfile
import signal
from sqlalchemy.orm import Session
from database import SessionLocal, Mailbox, engine, Job

# Global registry for running processes {mailbox_id: process_object}
active_processes = {}


def secure_delete_file(filepath):
    """
    Securely delete a file by overwriting its content with zeros
    before unlinking, so passwords can't be recovered from disk.
    """
    try:
        if not filepath or not os.path.exists(filepath):
            return
        # Overwrite file content with zeros
        file_size = os.path.getsize(filepath)
        with open(filepath, 'wb') as f:
            f.write(b'\x00' * file_size)
            f.flush()
            os.fsync(f.fileno())
        # Then delete the file
        os.unlink(filepath)
    except Exception:
        # Fallback: at least try to delete
        try:
            os.unlink(filepath)
        except Exception:
            pass


def cleanup_stale_passfiles():
    """
    Clean up any leftover temporary password files from previous
    crashed sessions. Called once when worker starts.
    """
    tmp_dir = tempfile.gettempdir()
    count = 0
    for f in glob.glob(os.path.join(tmp_dir, 'isp_*')):
        try:
            # Only clean files older than 1 hour to avoid deleting active ones
            if os.path.isfile(f) and (time.time() - os.path.getmtime(f)) > 3600:
                file_size = os.path.getsize(f)
                if file_size < 1024:  # Password files are very small
                    secure_delete_file(f)
                    count += 1
        except Exception:
            pass
    if count > 0:
        print(f"[Security] Cleaned up {count} stale temp file(s).")

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
    
    pass1_path = None
    pass2_path = None
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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='isp_') as f_pass1, \
             tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='isp_') as f_pass2:
            
            f_pass1.write(source_pass)
            f_pass1.flush()
            pass1_path = f_pass1.name
            
            f_pass2.write(target_pass)
            f_pass2.flush()
            pass2_path = f_pass2.name
        
        # Set strict file permissions (owner read/write only)
        os.chmod(pass1_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        os.chmod(pass2_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        
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
            '--nofoldersizes',
            # --- Resilience: prevent ERR_APPEND / ERR_FETCH ---
            '--errorsmax', '2000',          # Extreme tolerance for corrupted/UNAVAILABLE emails
            '--reconnectretry1', '10',      # Auto-reconnect source up to 10 times
            '--reconnectretry2', '10',      # Auto-reconnect target up to 10 times
            '--timeout1', '180',            # Extended source timeout to 180s (3 minutes)
            '--timeout2', '180',            # Extended target timeout to 180s
            '--split1', '50',               # Process in very small chunks of 50 msgs
            '--split2', '50',               # Process in very small chunks of 50 msgs
            '--skipcrossduplicates',        # Faster duplicate check
            '--useheader', 'Message-Id',    # Fast header parsing for large folders
            '--fastio1',                    # Use fast I/O on source
            '--fastio2',                    # Use fast I/O on target
            '--allowsizemismatch',          # Handle CRLF/LF encoding size differences between environments
            '--maxretries', '7',            # Per-message retry up to 7 times (default 3)
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

        # Provider-specific Flags (Source)
        source_host_lower = job.source_host.lower()
        if 'gmail.com' in source_host_lower or 'googlemail.com' in source_host_lower:
            cmd.append('--gmail1')
        elif 'office365.com' in source_host_lower or 'outlook.com' in source_host_lower or 'hotmail.com' in source_host_lower:
            cmd.append('--office3651')
        elif 'exchange' in source_host_lower:
            cmd.append('--exchange1')
        elif 'yahoo.com' in source_host_lower:
            cmd.append('--yahoo1')
        elif 'zoho.com' in source_host_lower:
            cmd.append('--zoho1')

        # Provider-specific Flags (Target)
        target_host_lower = job.target_host.lower()
        if 'gmail.com' in target_host_lower or 'googlemail.com' in target_host_lower:
            cmd.append('--gmail2')
        elif 'office365.com' in target_host_lower or 'outlook.com' in target_host_lower or 'hotmail.com' in target_host_lower:
            cmd.append('--office3652')
        elif 'exchange' in target_host_lower:
            cmd.append('--exchange2')
        elif 'yahoo.com' in target_host_lower:
            cmd.append('--yahoo2')
        elif 'zoho.com' in target_host_lower:
            cmd.append('--zoho2')
            
        # Feature Flags
        if options.get('sync_internal_dates'):
            cmd.append('--syncinternaldates')
        
        if options.get('skip_trash'):
             # Common trash folder names, can be expanded
            cmd.extend(['--exclude', 'Trash', '--exclude', 'Bin', '--exclude', 'Deleted Items'])
            
        if options.get('dry_run'):
            cmd.append('--dry')

        # --- Auto-Retry Configuration ---
        MAX_RETRIES = 3
        RETRY_DELAYS = [30, 60, 120]  # Exponential backoff in seconds
        # Exit codes that should NOT be retried (fatal / user-initiated)
        NON_RETRYABLE_CODES = {-15, -9}  # SIGTERM, SIGKILL (user stop)

        import re
        total_bytes = 0
        final_returncode = None

        for attempt in range(MAX_RETRIES + 1):
            # --- Retry delay (skip for first attempt) ---
            if attempt > 0:
                delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                mailbox.message = f"Retry {attempt}/{MAX_RETRIES}: Restarting sync in {delay}s after error (code {final_returncode})..."
                mailbox.status = 'running'
                db.commit()
                time.sleep(delay)

            # Open log file: "w" for first attempt, "a" for retries
            open_mode = "w" if attempt == 0 else "a"
            with open(log_file_path, open_mode) as log_file:
                if attempt > 0:
                    log_file.write(f"\n{'='*60}\n")
                    log_file.write(f"  AUTO-RETRY {attempt}/{MAX_RETRIES} — Previous exit code: {final_returncode}\n")
                    log_file.write(f"  imapsync will skip already-synced messages automatically\n")
                    log_file.write(f"{'='*60}\n\n")

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
                current_folder = 0
                total_folders = 0
                current_msg = 0
                total_msgs = 0
                last_progress = -1
                last_db_pulse = time.time()
                attempt_bytes = 0
                
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    
                    if not line:
                        continue

                    line_stripped = line.strip()
                    log_file.write(line)
                    log_file.flush()
                    
                    now = time.time()
                    # Pulse DB every 10 seconds even if no progress match, just to show activity
                    if now - last_db_pulse > 10:
                        try:
                            db.refresh(mailbox)
                            db.commit()
                            last_db_pulse = now
                        except: pass

                    # 1. Parse Folder Progress (e.g., "Folder     1/9 [INBOX]")
                    folder_match = re.search(r'Folder\s+(\d+)/(\d+)', line)
                    if folder_match:
                        try:
                            current_folder = int(folder_match.group(1))
                            total_folders = int(folder_match.group(2))
                            total_msgs = 0
                            if total_folders > 0:
                                progress = int(((current_folder - 1) / total_folders) * 100)
                                if progress != last_progress:
                                    retry_prefix = f"[Retry {attempt}/{MAX_RETRIES}] " if attempt > 0 else ""
                                    mailbox.progress = progress
                                    mailbox.message = f"{retry_prefix}Syncing folder {current_folder}/{total_folders}"
                                    db.commit()
                                    last_progress = progress
                                    last_db_pulse = now
                        except: pass
                    
                    # 2. Parse Message Total for current folder
                    msg_total_match = re.search(r'has\s+(\d+)\s+messages\s+in\s+total', line)
                    if msg_total_match:
                        try:
                            total_msgs = int(msg_total_match.group(1))
                        except: pass

                    # 3. Parse Message Progress (e.g., "msg INBOX/700 {356143} copied")
                    msg_match = re.search(r'msg\s+.*?/(\d+)', line)
                    if msg_match and total_folders > 0 and total_msgs > 0:
                        try:
                            current_msg = int(msg_match.group(1))
                            
                            if current_msg > total_msgs:
                                total_msgs = current_msg

                            base_p = ((current_folder - 1) / total_folders)
                            msg_p = (current_msg / total_msgs) / total_folders
                            progress = int((base_p + msg_p) * 100)
                            
                            if progress > 100:
                                progress = 100
                            
                            if progress != last_progress:
                                retry_prefix = f"[Retry {attempt}/{MAX_RETRIES}] " if attempt > 0 else ""
                                mailbox.progress = progress
                                mailbox.message = f"{retry_prefix}Folder {current_folder}/{total_folders}: msg {current_msg}/{total_msgs}"
                                db.commit()
                                last_progress = progress
                                last_db_pulse = now
                        except: pass

                    # 4. Catch general status lines
                    elif any(kw in line for kw in ["Connecting to", "Calculating", "Authentication", "Detected"]):
                        mailbox.message = line_stripped[:100] + "..." if len(line_stripped) > 100 else line_stripped
                        db.commit()
                        last_db_pulse = now
                    
                    # 5. Parse Data Transfer
                    if "Total bytes transferred" in line:
                        match = re.search(r'Total bytes transferred.*?:\s*(\d+)', line, re.IGNORECASE)
                        if match:
                             try: attempt_bytes = int(match.group(1))
                             except: pass
                    elif "Total size" in line and "bytes" in line and attempt_bytes == 0:
                         match = re.search(r'Total size.*?:\s*(\d+)', line, re.IGNORECASE)
                         if match:
                             try: attempt_bytes = int(match.group(1))
                             except: pass

                process.wait()
                final_returncode = process.returncode
                
                # Accumulate bytes across retries
                if attempt_bytes > 0:
                    total_bytes = max(total_bytes, attempt_bytes)
                
                # Cleanup registry for this attempt
                if mailbox_id in active_processes:
                    del active_processes[mailbox_id]

            # --- Decide: retry or break ---
            if final_returncode == 0:
                # Success — no retry needed
                break
            elif final_returncode in (111, 112, 113, 114, 115, 116):
                # Partial success — most messages synced, no point retrying
                break
            elif final_returncode in NON_RETRYABLE_CODES:
                # User stopped or killed — do not retry
                break
            else:
                # Retryable error — log and continue loop
                if attempt < MAX_RETRIES:
                    with open(log_file_path, "a") as log_file:
                        log_file.write(f"\n[WORKER] imapsync exited with code {final_returncode}. Will retry ({attempt + 1}/{MAX_RETRIES})...\n")
                else:
                    with open(log_file_path, "a") as log_file:
                        log_file.write(f"\n[WORKER] imapsync exited with code {final_returncode}. All {MAX_RETRIES} retries exhausted.\n")

        # --- Final status based on last return code ---
        # Update Stats
        if total_bytes > 0:
            mailbox.data_transferred = total_bytes
            job.data_transferred += total_bytes
        
        if final_returncode == 0:
            mailbox.status = 'success'
            mailbox.progress = 100
            retried_note = f" (after {attempt} retries)" if attempt > 0 else ""
            mailbox.message = f"Sync Completed Successfully{retried_note}"
            job.completed += 1
        elif final_returncode in (-15, -9):
            mailbox.status = 'failed'
            mailbox.message = "Stopped by user"
        elif final_returncode in (111, 112, 113, 114, 115, 116):
            # Partial success
            mailbox.status = 'warning'
            mailbox.progress = 100
            exit_names = {
                111: 'OVER_QUOTA', 112: 'TRANSFER', 113: 'CREATE',
                114: 'APPEND', 115: 'FETCH', 116: 'DELETE'
            }
            err_name = exit_names.get(final_returncode, str(final_returncode))
            retried_note = f" (after {attempt} retries)" if attempt > 0 else ""
            mailbox.message = f"Partial sync (ERR_{err_name}){retried_note}. Some messages failed. Check logs."
            job.completed += 1
        else:
            mailbox.status = 'failed'
            retried_note = f" after {MAX_RETRIES} retries" if attempt > 0 else ""
            mailbox.message = f"Exited with code {final_returncode}{retried_note}. Check logs."


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
        
        # Cleanup temp password files (ALWAYS, even on exception)
        # Use secure_delete_file to overwrite content before deleting
        for _p in [pass1_path, pass2_path]:
            secure_delete_file(_p)
        
        # Recalculate Job Stats to avoid race conditions and check completion
        if job:
            from sqlalchemy import func
            completed_count = db.query(Mailbox).filter(Mailbox.job_id == job.id, Mailbox.status.in_(['success', 'warning'])).count()
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

