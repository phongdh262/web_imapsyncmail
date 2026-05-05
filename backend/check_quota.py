"""
Check Mailbox Quota / Storage Size
Connects via IMAP to check mailbox quota (GETQUOTAROOT RFC 2087)
with fallback to summing RFC822.SIZE across all folders.
"""

import imaplib
import ssl
import socket
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from check_credentials import detect_provider, TIMEOUT

logger = logging.getLogger(__name__)

MAX_FALLBACK_FOLDERS = 6
MAX_FALLBACK_MESSAGES_PER_FOLDER = 500


def _format_size(size_bytes):
    """Format bytes to human-readable string."""
    if size_bytes is None or size_bytes < 0:
        return "N/A"
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


def _flatten_quota_items(items):
    """Yield nested quota response parts as bytes/strings."""
    if items is None:
        return
    if isinstance(items, (bytes, str)):
        yield items
        return
    for item in items:
        if isinstance(item, (list, tuple)):
            yield from _flatten_quota_items(item)
        else:
            yield item


def _parse_quota_response(quota_data):
    """
    Parse IMAP GETQUOTAROOT response.
    Typical response: b'(STORAGE 12345 50000)'  (used/limit in KB)
    Returns (used_bytes, limit_bytes) or (None, None).
    """
    try:
        for item in _flatten_quota_items(quota_data):
            if isinstance(item, bytes):
                item = item.decode("utf-8", errors="replace")
            if isinstance(item, str) and "STORAGE" in item.upper():
                # Extract numbers after STORAGE
                import re
                match = re.search(r'STORAGE\s+(\d+)\s+(\d+)', item, re.IGNORECASE)
                if match:
                    used_kb = int(match.group(1))
                    limit_kb = int(match.group(2))
                    return used_kb * 1024, limit_kb * 1024
    except Exception as e:
        logger.debug(f"Quota parse error: {e}")
    return None, None


def _list_folders(imap):
    """List all IMAP folders."""
    folders = []
    try:
        status, folder_list = imap.list()
        if status == "OK" and folder_list:
            for item in folder_list:
                if item is None:
                    continue
                if isinstance(item, bytes):
                    item = item.decode("utf-8", errors="replace")
                # Parse folder name from LIST response
                # Typical format: '(\\HasNoChildren) "/" "INBOX"'
                import re
                match = re.search(r'"([^"]*)"$', item)
                if match:
                    folders.append(match.group(1))
                else:
                    # Try last part after space
                    parts = item.rsplit(" ", 1)
                    if len(parts) == 2:
                        folders.append(parts[1].strip('"'))
    except Exception as e:
        logger.debug(f"Error listing folders: {e}")
    return folders if folders else ["INBOX"]


def _prioritize_folders(folders):
    """Keep fallback predictable by checking INBOX/All Mail first, then a small remainder."""
    preferred = []
    remaining = []
    for folder in folders:
        normalized = folder.lower()
        if normalized == "inbox" or "all mail" in normalized:
            preferred.append(folder)
        else:
            remaining.append(folder)

    selected = []
    for folder in preferred + remaining:
        if folder not in selected:
            selected.append(folder)
        if len(selected) >= MAX_FALLBACK_FOLDERS:
            break
    return selected or ["INBOX"]


def _get_folder_size(imap, folder_name):
    """Estimate folder size with a bounded RFC822.SIZE sample."""
    total_size = 0
    message_count = 0
    estimated = False
    try:
        status, data = imap.select(f'"{folder_name}"', readonly=True)
        if status != "OK":
            return 0, 0, False

        # Get message count
        msg_count_raw = data[0]
        if isinstance(msg_count_raw, bytes):
            msg_count_raw = msg_count_raw.decode()
        total_messages = int(msg_count_raw)

        if total_messages == 0:
            return 0, 0, False

        fetch_range = "1:*"
        if total_messages > MAX_FALLBACK_MESSAGES_PER_FOLDER:
            fetch_start = total_messages - MAX_FALLBACK_MESSAGES_PER_FOLDER + 1
            fetch_range = f"{fetch_start}:*"
            estimated = True

        status, data = imap.fetch(fetch_range, "(RFC822.SIZE)")
        if status == "OK" and data:
            import re
            for item in data:
                if item is None:
                    continue
                if isinstance(item, bytes):
                    item = item.decode("utf-8", errors="replace")
                if isinstance(item, str):
                    match = re.search(r'RFC822\.SIZE\s+(\d+)', item)
                    if match:
                        total_size += int(match.group(1))
                        message_count += 1

        if estimated and message_count > 0:
            average_size = total_size / message_count
            total_size = int(average_size * total_messages)
            message_count = total_messages

    except Exception as e:
        logger.debug(f"Error getting folder size for {folder_name}: {e}")

    return total_size, message_count, estimated


def check_mailbox_quota(email: str, password: str, host: str = None, port: int = 993) -> dict:
    """
    Check mailbox quota/size via IMAP.
    Returns {
        email, status, quota_used, quota_limit, usage_percent,
        quota_used_formatted, quota_limit_formatted,
        total_size, total_size_formatted, total_messages,
        folder_sizes: [{name, size, size_formatted, messages}],
        message, provider, method
    }
    """
    email = email.strip()
    password = password.strip()

    provider_info = detect_provider(email)

    if host:
        provider_name = provider_info["name"] if provider_info else host
    else:
        if provider_info:
            host = provider_info["host"]
            port = provider_info["port"]
            provider_name = provider_info["name"]
        else:
            return {
                "email": email,
                "status": "failed",
                "message": "Cannot detect IMAP server for domain. Please specify host manually.",
                "provider": "Unknown"
            }

    try:
        ctx = ssl.create_default_context()
        imap = imaplib.IMAP4_SSL(host, port, ssl_context=ctx, timeout=TIMEOUT)
        imap.login(email, password)

        result = {
            "email": email,
            "status": "success",
            "provider": provider_name,
            "host": host,
            "quota_used": None,
            "quota_limit": None,
            "usage_percent": None,
            "quota_used_formatted": "N/A",
            "quota_limit_formatted": "N/A",
            "total_size": 0,
            "total_size_formatted": "0 B",
            "total_messages": 0,
            "folder_sizes": [],
            "message": "",
            "method": "unknown"
        }

        # Try GETQUOTAROOT first (RFC 2087)
        quota_available = False
        try:
            status, quota_data = imap.getquotaroot("INBOX")
            if status == "OK":
                used_bytes, limit_bytes = _parse_quota_response(quota_data)
                if used_bytes is not None and limit_bytes is not None:
                    quota_available = True
                    result["quota_used"] = used_bytes
                    result["quota_limit"] = limit_bytes
                    result["quota_used_formatted"] = _format_size(used_bytes)
                    result["quota_limit_formatted"] = _format_size(limit_bytes)
                    if limit_bytes > 0:
                        result["usage_percent"] = round((used_bytes / limit_bytes) * 100, 1)
                    else:
                        result["usage_percent"] = 0
                    result["method"] = "QUOTA"
                    result["message"] = f"Quota: {result['quota_used_formatted']} / {result['quota_limit_formatted']} ({result['usage_percent']}%)"
        except (imaplib.IMAP4.error, Exception) as e:
            logger.debug(f"GETQUOTAROOT not supported for {email}: {e}")

        if quota_available:
            result["total_size"] = result["quota_used"] or 0
            result["total_size_formatted"] = result["quota_used_formatted"]
        else:
            folders = _prioritize_folders(_list_folders(imap))
            total_size = 0
            total_messages = 0
            folder_details = []
            estimated_fallback = False

            for folder in folders:
                try:
                    size, msgs, estimated = _get_folder_size(imap, folder)
                    total_size += size
                    total_messages += msgs
                    estimated_fallback = estimated_fallback or estimated
                    if size > 0 or msgs > 0:
                        folder_details.append({
                            "name": folder,
                            "size": size,
                            "size_formatted": _format_size(size),
                            "messages": msgs,
                            "estimated": estimated
                        })
                except Exception:
                    continue

            # Sort folders by size descending
            folder_details.sort(key=lambda f: f["size"], reverse=True)

            result["total_size"] = total_size
            result["total_size_formatted"] = _format_size(total_size)
            result["total_messages"] = total_messages
            result["folder_sizes"] = folder_details
            result["method"] = "SAMPLED_FETCH" if estimated_fallback else "FETCH"
            result["quota_used"] = total_size
            result["quota_used_formatted"] = _format_size(total_size)
            estimate_note = "estimated from a bounded sample" if estimated_fallback else "calculated from sampled folders"
            result["message"] = f"Mailbox size: {_format_size(total_size)} ({total_messages} messages across {len(folder_details)} folders, {estimate_note})"

        try:
            imap.logout()
        except Exception:
            pass

        return result

    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        if "AUTHENTICATIONFAILED" in error_msg.upper() or "AUTH" in error_msg.upper():
            msg = "Authentication failed - Wrong email or password / App Password required"
        elif "ALERT" in error_msg.upper():
            msg = f"Server alert: {error_msg}"
        else:
            msg = f"IMAP error: {error_msg}"
        return {"email": email, "status": "failed", "message": msg, "provider": provider_name}

    except socket.timeout:
        return {"email": email, "status": "failed", "message": f"Connection timed out to {host}:{port}", "provider": provider_name}

    except (socket.gaierror, OSError) as e:
        return {"email": email, "status": "failed", "message": f"Cannot connect to {host}:{port} - {str(e)}", "provider": provider_name}

    except Exception as e:
        return {"email": email, "status": "failed", "message": f"Unexpected error: {str(e)}", "provider": provider_name}


def check_bulk_quota(credentials: list, host: str = None, port: int = 993, max_concurrent: int = 3) -> list:
    """
    Check quota for multiple mailboxes concurrently.
    credentials: list of { email, password }
    Returns list of results.
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        future_to_cred = {
            pool.submit(check_mailbox_quota, cred["email"], cred["password"], host, port): cred
            for cred in credentials
        }

        for future in as_completed(future_to_cred):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                cred = future_to_cred[future]
                results.append({
                    "email": cred["email"],
                    "status": "failed",
                    "message": f"Check error: {str(e)}",
                    "provider": "Unknown"
                })

    # Sort results to match original order
    email_order = {cred["email"]: i for i, cred in enumerate(credentials)}
    results.sort(key=lambda r: email_order.get(r["email"], 999))

    return results
