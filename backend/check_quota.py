"""
Check Mailbox Quota / Storage Size
Connects via IMAP to check mailbox quota (GETQUOTAROOT RFC 2087)
with fallback to summing RFC822.SIZE across all folders.
"""

import imaplib
import ssl
import socket
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from check_credentials import detect_provider, TIMEOUT

logger = logging.getLogger(__name__)

FETCH_BATCH_SIZE = 500
MAX_REASONABLE_MAILBOX_QUOTA_BYTES = 100 * (1024 ** 4)
SUSPICIOUS_KB_INTERPRETATION_BYTES = 5 * (1024 ** 4)
FOLDER_ROLE_TRASH = "trash"
SYNC_DEDUPE_HEADER = "message-id"


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


def _quota_storage_to_bytes(used_value, limit_value):
    """
    Normalize IMAP QUOTA STORAGE values to bytes.

    RFC 2087 defines STORAGE in 1024-octet units, but some providers return
    byte values. A 7 GB byte quota may arrive as 7516192768; treating that as
    KB produces an obviously inflated limit. Prefer bytes when the raw value
    already looks like a realistic mailbox quota and the RFC interpretation
    would exceed a practical per-mailbox limit.
    """
    used_value = int(used_value)
    limit_value = int(limit_value)

    used_as_kb = used_value * 1024
    limit_as_kb = limit_value * 1024

    raw_values_look_like_bytes = (
        limit_value >= 1024 ** 3
        and limit_value <= MAX_REASONABLE_MAILBOX_QUOTA_BYTES
        and limit_as_kb > SUSPICIOUS_KB_INTERPRETATION_BYTES
    )
    if raw_values_look_like_bytes:
        return used_value, limit_value

    return used_as_kb, limit_as_kb


def _quota_values_look_plausible(used_bytes, limit_bytes):
    """Reject quota payloads that decode into obviously wrong mailbox sizes."""
    if used_bytes is None or limit_bytes is None:
        return False

    used_bytes = int(used_bytes)
    limit_bytes = int(limit_bytes)

    if used_bytes < 0 or limit_bytes < 0:
        return False
    if limit_bytes > MAX_REASONABLE_MAILBOX_QUOTA_BYTES:
        return False
    if limit_bytes > 0 and used_bytes > limit_bytes:
        return False

    return True


def _quota_values_need_mailbox_scan(used_bytes, limit_bytes):
    """
    Validate quota with a bounded mailbox scan when the server response looks
    incomplete. Several providers report a limit but keep used/messages at 0.
    """
    if used_bytes is None:
        return True
    if used_bytes == 0:
        return True
    if limit_bytes == 0:
        return True
    return False


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
                match = re.search(r'STORAGE\s+(\d+)\s+(\d+)', item, re.IGNORECASE)
                if match:
                    return _quota_storage_to_bytes(match.group(1), match.group(2))
    except Exception as e:
        logger.debug(f"Quota parse error: {e}")
    return None, None


def _parse_list_item(item):
    """Parse a LIST response line into folder metadata."""
    if item is None:
        return None
    if isinstance(item, bytes):
        item = item.decode("utf-8", errors="replace")
    if not isinstance(item, str):
        return None

    flags_match = re.match(r"^\((?P<flags>[^)]*)\)", item)
    flags = []
    if flags_match:
        flags = [flag.lower() for flag in flags_match.group("flags").split() if flag]

    name = None
    quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"$', item)
    if quoted_match:
        name = quoted_match.group(1).replace('\\"', '"')
    else:
        parts = item.rsplit(" ", 1)
        if len(parts) == 2:
            name = parts[1].strip('"')

    if not name:
        return None

    return {
        "name": name,
        "attributes": flags,
        "selectable": "\\noselect" not in flags,
    }


def _list_folders(imap):
    """List all IMAP folders."""
    folders = []
    try:
        status, folder_list = imap.list()
        if status == "OK" and folder_list:
            for item in folder_list:
                parsed = _parse_list_item(item)
                if parsed:
                    folders.append(parsed)
    except Exception as e:
        logger.debug(f"Error listing folders: {e}")
    return folders if folders else [{
        "name": "INBOX",
        "attributes": [],
        "selectable": True,
    }]


def _folder_has_attribute(folder, *attributes):
    attrs = set(folder.get("attributes", []))
    return any(attribute in attrs for attribute in attributes)


def _folder_matches_role(folder, role):
    name = folder["name"].lower()
    if role == FOLDER_ROLE_TRASH:
        return _folder_has_attribute(folder, "\\trash") or name.endswith("/trash") or name in {"trash", "bin", "deleted items", "deleted messages"}
    return False


def _dedupe_folder_names(folders):
    unique = []
    seen = set()
    for folder in folders:
        name = folder["name"]
        if name in seen:
            continue
        seen.add(name)
        unique.append(folder)
    return unique


def _folder_excluded_by_sync(folder, skip_trash):
    if skip_trash and _folder_matches_role(folder, FOLDER_ROLE_TRASH):
        return True, "trash_excluded"
    return False, None


def _select_sync_folders(folders, skip_trash=True):
    """Select folders according to current imapsync rules used by worker.py."""
    unique_folders = _dedupe_folder_names(folders)
    selected = []
    skipped_folders = []
    for folder in unique_folders:
        if not folder.get("selectable", True):
            skipped_folders.append(folder["name"])
            continue
        excluded, reason = _folder_excluded_by_sync(folder, skip_trash)
        if excluded:
            skipped_folders.append(folder["name"])
            continue
        selected.append(folder)

    if not selected:
        selected = [{
        "name": "INBOX",
        "attributes": [],
        "selectable": True,
    }]

    return {
        "folders": selected,
        "strategy": "sync_rules_skip_trash" if skip_trash else "sync_rules_include_trash",
        "skipped_folders": skipped_folders,
    }


def _extract_message_id(header_blob):
    if header_blob is None:
        return None
    if isinstance(header_blob, bytes):
        header_blob = header_blob.decode("utf-8", errors="replace")
    match = re.search(r"^\s*Message-ID:\s*(.+?)\s*$", header_blob, re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1).strip()).lower()


def _iter_fetch_metadata(batch_data):
    """Yield parsed metadata rows from IMAP FETCH results."""
    for item in batch_data:
        if item is None:
            continue

        meta_text = None
        header_blob = None

        if isinstance(item, tuple) and item:
            meta_text = item[0]
            if len(item) > 1:
                header_blob = item[1]
        else:
            meta_text = item

        if isinstance(meta_text, bytes):
            meta_text = meta_text.decode("utf-8", errors="replace")
        if not isinstance(meta_text, str):
            continue

        size_match = re.search(r"RFC822\.SIZE\s+(\d+)", meta_text)
        uid_match = re.search(r"\bUID\s+(\d+)", meta_text)
        seq_match = re.match(r"^\s*(\d+)", meta_text)

        if not size_match:
            continue

        yield {
            "size": int(size_match.group(1)),
            "uid": uid_match.group(1) if uid_match else None,
            "seq": seq_match.group(1) if seq_match else None,
            "message_id": _extract_message_id(header_blob),
        }


def _build_message_identity(folder_name, metadata):
    """Match the effective imapsync dedupe key as closely as possible."""
    if metadata["message_id"]:
        return f"{SYNC_DEDUPE_HEADER}:{metadata['message_id']}", True
    if metadata["uid"]:
        return f"{folder_name}::uid:{metadata['uid']}", False
    if metadata["seq"]:
        return f"{folder_name}::seq:{metadata['seq']}", False
    return f"{folder_name}::anon:{metadata['size']}", False


def _get_folder_sync_metrics(imap, folder_name, seen_messages):
    """Estimate synced bytes/messages for one folder using imapsync-like dedupe."""
    raw_size = 0
    synced_size = 0
    raw_messages = 0
    synced_messages = 0
    duplicate_messages = 0
    duplicate_bytes = 0
    missing_message_ids = 0
    scan_complete = True
    scan_error = None
    selected_messages = 0
    try:
        status, data = imap.select(f'"{folder_name}"', readonly=True)
        if status != "OK":
            return {
                "name": folder_name,
                "size": 0,
                "size_formatted": "0 B",
                "messages": 0,
                "raw_size": 0,
                "raw_size_formatted": "0 B",
                "raw_messages": 0,
                "duplicate_messages": 0,
                "duplicate_bytes": 0,
                "duplicate_bytes_formatted": "0 B",
                "missing_message_id_count": 0,
                "complete": False,
                "error": "Folder select failed",
            }

        # Get message count
        msg_count_raw = data[0]
        if isinstance(msg_count_raw, bytes):
            msg_count_raw = msg_count_raw.decode()
        selected_messages = int(msg_count_raw)

        if selected_messages == 0:
            return {
                "name": folder_name,
                "size": 0,
                "size_formatted": "0 B",
                "messages": 0,
                "raw_size": 0,
                "raw_size_formatted": "0 B",
                "raw_messages": 0,
                "duplicate_messages": 0,
                "duplicate_bytes": 0,
                "duplicate_bytes_formatted": "0 B",
                "missing_message_id_count": 0,
                "complete": True,
                "error": None,
            }

        for start in range(1, selected_messages + 1, FETCH_BATCH_SIZE):
            end = min(start + FETCH_BATCH_SIZE - 1, selected_messages)
            fetch_range = f"{start}:{end}"
            status, batch_data = imap.fetch(fetch_range, "(UID RFC822.SIZE BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
            if status != "OK" or not batch_data:
                scan_complete = False
                logger.debug("RFC822.SIZE + MESSAGE-ID fetch failed for %s range %s", folder_name, fetch_range)
                continue

            for metadata in _iter_fetch_metadata(batch_data):
                size = metadata["size"]
                raw_messages += 1
                raw_size += size
                dedupe_key, dedupe_eligible = _build_message_identity(folder_name, metadata)
                if not dedupe_eligible:
                    missing_message_ids += 1
                if dedupe_key in seen_messages:
                    duplicate_messages += 1
                    duplicate_bytes += size
                    continue
                seen_messages.add(dedupe_key)
                synced_messages += 1
                synced_size += size

    except Exception as e:
        scan_complete = False
        scan_error = str(e)
        logger.debug(f"Error getting folder size for {folder_name}: {e}")

    return {
        "name": folder_name,
        "size": synced_size,
        "size_formatted": _format_size(synced_size),
        "messages": synced_messages,
        "raw_size": raw_size,
        "raw_size_formatted": _format_size(raw_size),
        "raw_messages": raw_messages,
        "duplicate_messages": duplicate_messages,
        "duplicate_bytes": duplicate_bytes,
        "duplicate_bytes_formatted": _format_size(duplicate_bytes),
        "missing_message_id_count": missing_message_ids,
        "complete": scan_complete,
        "error": scan_error,
    }


def _describe_scan_strategy(strategy):
    if strategy == "sync_rules_skip_trash":
        return "sync rules with Trash excluded"
    if strategy == "sync_rules_include_trash":
        return "sync rules with Trash included"
    return "selected folders"


def _collect_sync_estimate(imap, skip_trash=True):
    """Compute the bytes/messages likely to be transferred by the current sync rules."""
    selection = _select_sync_folders(_list_folders(imap), skip_trash=skip_trash)
    folders = selection["folders"]
    total_size = 0
    total_messages = 0
    raw_total_size = 0
    raw_total_messages = 0
    duplicate_messages = 0
    duplicate_bytes = 0
    missing_message_id_count = 0
    folder_details = []
    scan_complete = True
    seen_messages = set()

    for folder in folders:
        try:
            folder_result = _get_folder_sync_metrics(imap, folder["name"], seen_messages)
            total_size += folder_result["size"]
            total_messages += folder_result["messages"]
            raw_total_size += folder_result["raw_size"]
            raw_total_messages += folder_result["raw_messages"]
            duplicate_messages += folder_result["duplicate_messages"]
            duplicate_bytes += folder_result["duplicate_bytes"]
            missing_message_id_count += folder_result["missing_message_id_count"]
            folder_result["attributes"] = folder.get("attributes", [])
            scan_complete = scan_complete and folder_result["complete"]
            folder_details.append(folder_result)
        except Exception:
            scan_complete = False
            continue

    folder_details.sort(key=lambda f: f["size"], reverse=True)
    return {
        "total_size": total_size,
        "total_messages": total_messages,
        "raw_total_size": raw_total_size,
        "raw_total_messages": raw_total_messages,
        "duplicate_messages": duplicate_messages,
        "duplicate_bytes": duplicate_bytes,
        "missing_message_id_count": missing_message_id_count,
        "folder_details": folder_details,
        "scan_strategy": selection["strategy"],
        "scanned_folders": [folder["name"] for folder in folders],
        "skipped_folders": selection["skipped_folders"],
        "scan_complete": scan_complete,
    }


def check_mailbox_quota(email: str, password: str, host: str = None, port: int = 993, skip_trash: bool = True) -> dict:
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
            "raw_total_size": 0,
            "raw_total_size_formatted": "0 B",
            "raw_total_messages": 0,
            "duplicate_messages": 0,
            "duplicate_bytes": 0,
            "duplicate_bytes_formatted": "0 B",
            "missing_message_id_count": 0,
            "folder_sizes": [],
            "scan_strategy": "sync_rules_skip_trash" if skip_trash else "sync_rules_include_trash",
            "scanned_folders": [],
            "skipped_folders": [],
            "scan_complete": True,
            "message": "",
            "method": "unknown"
        }

        # Try GETQUOTAROOT first (RFC 2087)
        quota_available = False
        quota_needs_mailbox_scan = True
        try:
            status, quota_data = imap.getquotaroot("INBOX")
            if status == "OK":
                used_bytes, limit_bytes = _parse_quota_response(quota_data)
                if used_bytes is not None and limit_bytes is not None:
                    if _quota_values_look_plausible(used_bytes, limit_bytes):
                        quota_available = True
                        quota_needs_mailbox_scan = _quota_values_need_mailbox_scan(used_bytes, limit_bytes)
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
                    else:
                        logger.warning(
                            "Ignoring suspicious quota response for %s: used=%s limit=%s",
                            email,
                            used_bytes,
                            limit_bytes,
                        )
        except (imaplib.IMAP4.error, Exception) as e:
            logger.debug(f"GETQUOTAROOT not supported for {email}: {e}")

        if not quota_available or quota_needs_mailbox_scan:
            mailbox_metrics = _collect_sync_estimate(imap, skip_trash=skip_trash)
            total_size = mailbox_metrics["total_size"]
            total_messages = mailbox_metrics["total_messages"]
            folder_details = mailbox_metrics["folder_details"]
            result["total_size"] = total_size
            result["total_size_formatted"] = _format_size(total_size)
            result["total_messages"] = total_messages
            result["raw_total_size"] = mailbox_metrics["raw_total_size"]
            result["raw_total_size_formatted"] = _format_size(mailbox_metrics["raw_total_size"])
            result["raw_total_messages"] = mailbox_metrics["raw_total_messages"]
            result["duplicate_messages"] = mailbox_metrics["duplicate_messages"]
            result["duplicate_bytes"] = mailbox_metrics["duplicate_bytes"]
            result["duplicate_bytes_formatted"] = _format_size(mailbox_metrics["duplicate_bytes"])
            result["missing_message_id_count"] = mailbox_metrics["missing_message_id_count"]
            result["folder_sizes"] = folder_details
            result["scan_strategy"] = mailbox_metrics["scan_strategy"]
            result["scanned_folders"] = mailbox_metrics["scanned_folders"]
            result["skipped_folders"] = mailbox_metrics["skipped_folders"]
            result["scan_complete"] = mailbox_metrics["scan_complete"]
            estimate_note = (
                f"sync estimate from RFC822.SIZE + Message-Id using {_describe_scan_strategy(result['scan_strategy'])}"
            )
            if not result["scan_complete"]:
                estimate_note += "; partial coverage because some folders or ranges could not be fetched"
            if result["duplicate_messages"] > 0:
                estimate_note += (
                    f"; skipped {result['duplicate_messages']} duplicate messages "
                    f"({result['duplicate_bytes_formatted']}) by Message-Id"
                )
            if result["missing_message_id_count"] > 0:
                estimate_note += f"; {result['missing_message_id_count']} messages had no Message-Id and were kept as unique"

            if quota_available:
                result["method"] = "QUOTA+SYNC_ESTIMATE"
                if total_size > 0 or total_messages > 0:
                    result["quota_used"] = total_size
                    result["quota_used_formatted"] = _format_size(total_size)
                    if result["quota_limit"] and result["quota_limit"] > 0:
                        result["usage_percent"] = round((total_size / result["quota_limit"]) * 100, 1)
                    result["message"] = (
                        f"Sync estimate: {result['quota_used_formatted']} / "
                        f"{result['quota_limit_formatted']} ({result['usage_percent']}%) "
                        f"from {total_messages} messages across {len(result['scanned_folders'])} scanned folders, {estimate_note}"
                    )
                else:
                    result["total_size"] = result["quota_used"] or 0
                    result["total_size_formatted"] = result["quota_used_formatted"]
            else:
                result["method"] = "SYNC_ESTIMATE"
                result["quota_used"] = total_size
                result["quota_used_formatted"] = _format_size(total_size)
                result["message"] = (
                    f"Sync estimate: {_format_size(total_size)} "
                    f"({total_messages} messages across {len(result['scanned_folders'])} scanned folders, {estimate_note})"
                )
        else:
            result["total_size"] = result["quota_used"] or 0
            result["total_size_formatted"] = result["quota_used_formatted"]

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


def check_bulk_quota(credentials: list, host: str = None, port: int = 993, max_concurrent: int = 3, on_result=None, skip_trash: bool = True) -> list:
    """
    Check quota for multiple mailboxes concurrently.
    credentials: list of { email, password }
    Returns list of results.
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        future_to_cred = {
            pool.submit(check_mailbox_quota, cred["email"], cred["password"], host, port, skip_trash): (index, cred)
            for index, cred in enumerate(credentials)
        }

        for future in as_completed(future_to_cred):
            index, cred = future_to_cred[future]
            try:
                result = future.result()
                results.append((index, result))
            except Exception as e:
                result = {
                    "email": cred["email"],
                    "status": "failed",
                    "message": f"Check error: {str(e)}",
                    "provider": "Unknown"
                }
                results.append((index, result))

            if on_result:
                try:
                    on_result(index, result)
                except Exception:
                    logger.exception("Bulk quota progress callback failed for %s", cred["email"])

    results.sort(key=lambda item: item[0])
    return [result for _, result in results]
