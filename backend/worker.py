import time
import subprocess
import os
import sys
import stat
import glob
import shutil
import select

# Add current directory to sys.path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tempfile
import signal
from sqlalchemy.orm import Session
from database import SessionLocal, Mailbox, engine, Job

# Global registry for running processes {mailbox_id: process_object}
active_processes = {}

STOP_REQUESTED_MESSAGE = "Stop requested by user"
CANCEL_REQUESTED_MESSAGE = "Cancel requested by user"
STOPPED_BY_USER_MESSAGE = "Stopped by user"
CANCELLED_BY_USER_MESSAGE = "Cancelled by user"
STOPPED_BEFORE_START_MESSAGE = "Stopped before start"
CANCELLED_BEFORE_START_MESSAGE = "Cancelled before start"

SOFT_STOP_REQUEST_MESSAGES = {
    STOP_REQUESTED_MESSAGE,
    CANCEL_REQUESTED_MESSAGE,
}
PRESTART_STOP_MESSAGES = {
    STOPPED_BEFORE_START_MESSAGE,
    CANCELLED_BEFORE_START_MESSAGE,
}
FINAL_STOP_MESSAGE_BY_REQUEST = {
    STOP_REQUESTED_MESSAGE: STOPPED_BY_USER_MESSAGE,
    CANCEL_REQUESTED_MESSAGE: CANCELLED_BY_USER_MESSAGE,
}

IMAPSYNC_BINARY = os.getenv("IMAPSYNC_BINARY") or shutil.which("imapsync") or "imapsync"
IMAPSYNC_TIMEOUT = max(60, int(os.getenv("IMAPSYNC_TIMEOUT", "180")))
IMAPSYNC_RECONNECT_RETRY = max(1, int(os.getenv("IMAPSYNC_RECONNECT_RETRY", "6")))
IMAPSYNC_SPLIT = max(50, int(os.getenv("IMAPSYNC_SPLIT", "200")))
IMAPSYNC_ERRORS_MAX = max(50, int(os.getenv("IMAPSYNC_ERRORS_MAX", "500")))
IMAPSYNC_MESSAGE_RETRIES = max(1, int(os.getenv("IMAPSYNC_MESSAGE_RETRIES", "5")))
IMAPSYNC_BUFFER_SIZE = max(0, int(os.getenv("IMAPSYNC_BUFFER_SIZE", "8192000")))


def _host_matches(hostname: str, *needles: str) -> bool:
    host = (hostname or "").lower()
    return any(needle in host for needle in needles)


def _detect_provider(hostname: str) -> str:
    host = (hostname or "").lower()
    if any(token in host for token in ('gmail.com', 'googlemail.com')):
        return 'gmail'
    if any(token in host for token in ('office365.com', 'outlook.com', 'hotmail.com', 'live.com', 'microsoftonline.com')):
        return 'office365'
    if 'yandex' in host:
        return 'yandex'
    return 'generic'


def _provider_tuning(source_host: str, target_host: str) -> dict:
    profiles = {
        'gmail': {
            'split': 120,
            'timeout': 240,
            'reconnect_retry': 8,
            'errors_max': 400,
            'message_retries': 5,
            'buffer_size': 4 * 1024 * 1024,
        },
        'office365': {
            'split': 80,
            'timeout': 300,
            'reconnect_retry': 8,
            'errors_max': 300,
            'message_retries': 5,
            'buffer_size': 4 * 1024 * 1024,
        },
        'yandex': {
            'split': 150,
            'timeout': 210,
            'reconnect_retry': 6,
            'errors_max': 400,
            'message_retries': 5,
            'buffer_size': 6 * 1024 * 1024,
        },
        'generic': {
            'split': IMAPSYNC_SPLIT,
            'timeout': IMAPSYNC_TIMEOUT,
            'reconnect_retry': IMAPSYNC_RECONNECT_RETRY,
            'errors_max': IMAPSYNC_ERRORS_MAX,
            'message_retries': IMAPSYNC_MESSAGE_RETRIES,
            'buffer_size': IMAPSYNC_BUFFER_SIZE,
        },
    }

    source_profile = profiles[_detect_provider(source_host)]
    target_profile = profiles[_detect_provider(target_host)]

    return {
        'split': min(source_profile['split'], target_profile['split']),
        'timeout': max(source_profile['timeout'], target_profile['timeout']),
        'reconnect_retry': max(source_profile['reconnect_retry'], target_profile['reconnect_retry']),
        'errors_max': min(source_profile['errors_max'], target_profile['errors_max']),
        'message_retries': max(source_profile['message_retries'], target_profile['message_retries']),
        'buffer_size': min(source_profile['buffer_size'], target_profile['buffer_size']),
        'source_provider': _detect_provider(source_host),
        'target_provider': _detect_provider(target_host),
    }


def build_imapsync_command(job, mailbox, pass1_path: str, pass2_path: str, options: dict):
    tuning = _provider_tuning(job.source_host, job.target_host)

    cmd = [
        IMAPSYNC_BINARY,
        '--host1', job.source_host,
        '--port1', str(job.source_port),
        '--user1', mailbox.source_user,
        '--passfile1', pass1_path,
        '--host2', job.target_host,
        '--port2', str(job.target_port),
        '--user2', mailbox.target_user,
        '--passfile2', pass2_path,
        '--automap',
        '--useuid',
        '--skipcrossduplicates',
        '--useheader', 'Message-Id',
        '--nofoldersizes',
        '--nofoldersizesatend',
        '--fastio1',
        '--fastio2',
        '--buffersize', str(tuning['buffer_size']),
        '--errorsmax', str(tuning['errors_max']),
        '--reconnectretry1', str(tuning['reconnect_retry']),
        '--reconnectretry2', str(tuning['reconnect_retry']),
        '--timeout1', str(tuning['timeout']),
        '--timeout2', str(tuning['timeout']),
        '--split1', str(tuning['split']),
        '--split2', str(tuning['split']),
        '--allowsizemismatch',
    ]

    if job.source_security == "SSL/TLS":
        cmd.append('--ssl1')
    elif job.source_security == "STARTTLS":
        cmd.append('--tls1')

    if job.target_security == "SSL/TLS":
        cmd.append('--ssl2')
    elif job.target_security == "STARTTLS":
        cmd.append('--tls2')

    if _host_matches(job.source_host, 'gmail.com', 'googlemail.com'):
        cmd.append('--gmail1')
    elif _host_matches(job.source_host, 'office365.com', 'outlook.com', 'hotmail.com'):
        cmd.append('--office3651')
    elif _host_matches(job.source_host, 'exchange'):
        cmd.append('--exchange1')
    elif _host_matches(job.source_host, 'zoho.com'):
        cmd.append('--zoho1')

    if _host_matches(job.target_host, 'gmail.com', 'googlemail.com'):
        cmd.append('--gmail2')
    elif _host_matches(job.target_host, 'office365.com', 'outlook.com', 'hotmail.com'):
        cmd.append('--office3652')
    elif _host_matches(job.target_host, 'exchange'):
        cmd.append('--exchange2')
    elif _host_matches(job.target_host, 'zoho.com'):
        cmd.append('--zoho2')

    if options.get('sync_internal_dates'):
        cmd.append('--syncinternaldates')

    if options.get('skip_trash'):
        cmd.extend([
            '--exclude', 'Trash',
            '--exclude', 'Bin',
            '--exclude', 'Deleted Items',
            '--exclude', 'Deleted Messages',
            '--exclude', '[Gmail]/Trash',
        ])

    if options.get('dry_run'):
        cmd.append('--dry')

    return cmd, tuning


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


def _is_stop_requested(mailbox: Mailbox) -> bool:
    return mailbox.status == 'stopping' and mailbox.message in SOFT_STOP_REQUEST_MESSAGES


def _resolve_stop_message(mailbox: Mailbox) -> str:
    return FINAL_STOP_MESSAGE_BY_REQUEST.get(mailbox.message, STOPPED_BY_USER_MESSAGE)


def _sleep_with_stop_check(db: Session, mailbox: Mailbox, delay_seconds: int) -> str | None:
    deadline = time.time() + delay_seconds
    while time.time() < deadline:
        try:
            db.refresh(mailbox)
            if _is_stop_requested(mailbox):
                return _resolve_stop_message(mailbox)
        except Exception:
            pass
        time.sleep(min(1, max(0, deadline - time.time())))
    return None

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
        db.refresh(mailbox)
        if mailbox.status == 'failed' and mailbox.message in PRESTART_STOP_MESSAGES:
            return

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

        cmd, tuning = build_imapsync_command(job, mailbox, pass1_path, pass2_path, options)

        # --- Auto-Retry Configuration ---
        MAX_RETRIES = 3
        RETRY_DELAYS = [30, 60, 120]  # Exponential backoff in seconds
        # Exit codes that should NOT be retried (fatal / user-initiated)
        NON_RETRYABLE_CODES = {-15, -9}  # SIGTERM, SIGKILL (user stop)

        import re
        total_bytes = 0
        final_returncode = None
        stop_result_message = None

        for attempt in range(MAX_RETRIES + 1):
            # --- Retry delay (skip for first attempt) ---
            if attempt > 0:
                delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                mailbox.message = f"Retry {attempt}/{MAX_RETRIES}: Restarting sync in {delay}s after error (code {final_returncode})..."
                mailbox.status = 'running'
                db.commit()
                stop_result_message = _sleep_with_stop_check(db, mailbox, delay)
                if stop_result_message:
                    final_returncode = -15
                    break

            db.refresh(mailbox)
            if _is_stop_requested(mailbox):
                stop_result_message = _resolve_stop_message(mailbox)
                final_returncode = -15
                break

            # Open log file: "w" for first attempt, "a" for retries
            open_mode = "w" if attempt == 0 else "a"
            with open(log_file_path, open_mode) as log_file:
                if attempt > 0:
                    log_file.write(f"\n{'='*60}\n")
                    log_file.write(f"  AUTO-RETRY {attempt}/{MAX_RETRIES} — Previous exit code: {final_returncode}\n")
                    log_file.write(f"  imapsync will skip already-synced messages automatically\n")
                    log_file.write(f"{'='*60}\n\n")
                log_file.write(f"[WORKER] Using imapsync binary: {IMAPSYNC_BINARY}\n")
                log_file.write(
                    "[WORKER] Provider tuning: "
                    f"source={tuning['source_provider']} "
                    f"target={tuning['target_provider']} "
                    f"split={tuning['split']} "
                    f"timeout={tuning['timeout']} "
                    f"reconnect_retry={tuning['reconnect_retry']} "
                    f"errors_max={tuning['errors_max']} "
                    f"buffer_size={tuning['buffer_size']}\n"
                )
                log_file.write(f"[WORKER] Command: {' '.join(cmd)}\n\n")

                process_env = os.environ.copy()
                process_env["LC_ALL"] = "C"
                process_env["LANG"] = "C"
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=process_env
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
                last_control_check = 0
                attempt_bytes = 0
                
                while True:
                    now = time.time()
                    if now - last_control_check >= 1:
                        try:
                            db.refresh(mailbox)
                            if _is_stop_requested(mailbox):
                                stop_result_message = _resolve_stop_message(mailbox)
                                log_file.write(f"[WORKER] {mailbox.message}. Sending SIGTERM.\n")
                                log_file.flush()
                                if process.poll() is None:
                                    process.terminate()
                            last_control_check = now
                        except Exception:
                            pass

                    ready = []
                    try:
                        if process.stdout:
                            ready, _, _ = select.select([process.stdout], [], [], 1.0)
                    except Exception:
                        ready = [process.stdout] if process.stdout else []

                    if ready:
                        line = process.stdout.readline()
                    else:
                        line = ""

                    if not line:
                        if process.poll() is not None:
                            break
                        continue

                    line_stripped = line.strip()
                    log_file.write(line)
                    log_file.flush()
                    
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
            if stop_result_message:
                break
            elif final_returncode == 0:
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
        
        if stop_result_message:
            mailbox.status = 'failed'
            mailbox.message = stop_result_message
        elif final_returncode == 0:
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

            active_count = db.query(Mailbox).filter(
                Mailbox.job_id == job.id,
                Mailbox.status.in_(['running', 'pending', 'stopping'])
            ).count()

            if active_count > 0:
                job.status = 'running'
            elif job.total_mailboxes > 0 and (job.completed + job.failed) >= job.total_mailboxes:
                job.status = 'failed' if job.completed == 0 and job.failed > 0 else 'completed'
            elif job.total_mailboxes == 0:
                job.status = 'pending'

        db.commit()
        db.close()
