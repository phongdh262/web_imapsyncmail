"""
Check App Password / Email Credentials
Unified IMAP-based check for all providers (Gmail, Yandex, Office365, Yahoo, custom).
"""

import imaplib
import ssl
import socket
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Well-known IMAP servers by email domain
PROVIDER_MAP = {
    "gmail.com": {"host": "imap.gmail.com", "port": 993, "name": "Gmail"},
    "googlemail.com": {"host": "imap.gmail.com", "port": 993, "name": "Gmail"},
    "yandex.com": {"host": "imap.yandex.com", "port": 993, "name": "Yandex"},
    "yandex.ru": {"host": "imap.yandex.com", "port": 993, "name": "Yandex"},
    "ya.ru": {"host": "imap.yandex.com", "port": 993, "name": "Yandex"},
    "outlook.com": {"host": "outlook.office365.com", "port": 993, "name": "Outlook"},
    "hotmail.com": {"host": "outlook.office365.com", "port": 993, "name": "Outlook"},
    "live.com": {"host": "outlook.office365.com", "port": 993, "name": "Outlook"},
    "yahoo.com": {"host": "imap.mail.yahoo.com", "port": 993, "name": "Yahoo"},
    "yahoo.co.jp": {"host": "imap.mail.yahoo.co.jp", "port": 993, "name": "Yahoo Japan"},
    "zoho.com": {"host": "imap.zoho.com", "port": 993, "name": "Zoho"},
    "zohomail.com": {"host": "imap.zoho.com", "port": 993, "name": "Zoho"},
    "icloud.com": {"host": "imap.mail.me.com", "port": 993, "name": "iCloud"},
    "me.com": {"host": "imap.mail.me.com", "port": 993, "name": "iCloud"},
    "mac.com": {"host": "imap.mail.me.com", "port": 993, "name": "iCloud"},
    "aol.com": {"host": "imap.aol.com", "port": 993, "name": "AOL"},
    "mail.ru": {"host": "imap.mail.ru", "port": 993, "name": "Mail.ru"},
    "vantaibuuchinh.com": {"host": "imap.yandex.com", "port": 993, "name": "Yandex"},
}

TIMEOUT = 15  # seconds


def infer_provider_from_host(host: str) -> Optional[dict]:
    normalized = (host or "").strip().lower()
    if not normalized:
        return None

    host_patterns = (
        (("imap.gmail.com", "imap.googlemail.com"), PROVIDER_MAP["gmail.com"]),
        (("imap.yandex.com",), PROVIDER_MAP["yandex.com"]),
        (("outlook.office365.com", "imap-mail.outlook.com"), PROVIDER_MAP["outlook.com"]),
        (("imap.mail.yahoo.com",), PROVIDER_MAP["yahoo.com"]),
        (("imap.mail.yahoo.co.jp",), PROVIDER_MAP["yahoo.co.jp"]),
        (("imap.zoho.com", "imappro.zoho.com"), PROVIDER_MAP["zoho.com"]),
        (("imap.mail.me.com",), PROVIDER_MAP["icloud.com"]),
        (("imap.aol.com",), PROVIDER_MAP["aol.com"]),
        (("imap.mail.ru",), PROVIDER_MAP["mail.ru"]),
    )

    for patterns, provider in host_patterns:
        if any(pattern in normalized for pattern in patterns):
            return provider

    return None


def _build_auth_failure_message(provider_name: str) -> str:
    if provider_name == "Zoho":
        return (
            "Authentication failed - Wrong email or password. "
            "If Zoho MFA is enabled, use a 12-character Application-Specific Password and make sure IMAP access is enabled."
        )
    return "Authentication failed - Wrong email or password / App Password required"


def detect_provider(email: str) -> dict:
    """Detect IMAP server from email domain."""
    domain = email.strip().lower().split("@")[-1] if "@" in email else ""
    provider = PROVIDER_MAP.get(domain, None)
    if provider:
        return provider
        
    # Check MX records for custom domains
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, 'MX')
        for rdata in answers:
            mx_domain = rdata.exchange.to_text().lower()
            if "google.com" in mx_domain or "googlemail.com" in mx_domain:
                return PROVIDER_MAP["gmail.com"]
            if "yandex.net" in mx_domain or "yandex.ru" in mx_domain:
                return PROVIDER_MAP["yandex.com"]
            if "azdigimail.com" in mx_domain:
                 # Many local domains use AZDIGI but users consider it "Yandex" because they migrate or use Yandex app passwords? 
                 # Let's fallback to Yandex if they are testing Yandex app passwords or use the MX domain itself
                 # Actually, let's just use the MX record minus the 'h02.' or just return yandex for this specific user's common case
                 return PROVIDER_MAP["yandex.com"]
            if "protection.outlook.com" in mx_domain or "office365.com" in mx_domain:
                return PROVIDER_MAP["outlook.com"]
            if "yahoodns.net" in mx_domain:
                return PROVIDER_MAP["yahoo.com"]
            if "zoho.com" in mx_domain:
                return PROVIDER_MAP["zoho.com"]
    except Exception:
        pass
        
    return None


def check_imap_login(email: str, password: str, host: str = None, port: int = 993) -> dict:
    """
    Check IMAP login credentials.
    Returns { email, status: "success"|"failed", message, provider }
    """
    email = email.strip()
    password = password.strip()

    # Auto-detect provider if host not specified
    provider_info = detect_provider(email)
    
    if host:
        # If user explicitly provided a host, use it
        provider_info = infer_provider_from_host(host) or provider_info
        provider_name = provider_info["name"] if provider_info else host
    else:
        # No host provided, rely on auto-detection
        if provider_info:
            host = provider_info["host"]
            port = provider_info["port"]
            provider_name = provider_info["name"]
        else:
            return {
                "email": email,
                "status": "failed",
                "message": f"Cannot detect IMAP server for domain. Please specify host manually.",
                "provider": "Unknown",
                "host": None,
                "port": port,
            }

    try:
        # Create SSL context
        ctx = ssl.create_default_context()

        # Connect with IMAP4_SSL (port 993)
        imap = imaplib.IMAP4_SSL(host, port, ssl_context=ctx, timeout=TIMEOUT)

        # Attempt login
        imap.login(email, password)

        # Success - logout cleanly
        try:
            imap.logout()
        except Exception:
            pass

        return {
            "email": email,
            "status": "success",
            "message": f"Login successful via {host}",
            "provider": provider_name,
            "host": host,
            "port": port,
        }

    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        # Parse common IMAP errors
        if "AUTHENTICATIONFAILED" in error_msg.upper() or "AUTH" in error_msg.upper():
            msg = _build_auth_failure_message(provider_name)
        elif "ALERT" in error_msg.upper():
            msg = f"Server alert: {error_msg}"
        else:
            msg = f"IMAP error: {error_msg}"

        return {
            "email": email,
            "status": "failed",
            "message": msg,
            "provider": provider_name,
            "host": host,
            "port": port,
        }

    except socket.timeout:
        return {
            "email": email,
            "status": "failed",
            "message": f"Connection timed out to {host}:{port}",
            "provider": provider_name,
            "host": host,
            "port": port,
        }

    except (socket.gaierror, OSError) as e:
        return {
            "email": email,
            "status": "failed",
            "message": f"Cannot connect to {host}:{port} - {str(e)}",
            "provider": provider_name,
            "host": host,
            "port": port,
        }

    except Exception as e:
        return {
            "email": email,
            "status": "failed",
            "message": f"Unexpected error: {str(e)}",
            "provider": provider_name,
            "host": host,
            "port": port,
        }


def check_bulk(credentials: list, host: str = None, port: int = 993, max_concurrent: int = 5) -> list:
    """
    Check multiple credentials concurrently.
    credentials: list of { email, password }
    Returns list of results.
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        future_to_cred = {
            pool.submit(check_imap_login, cred["email"], cred["password"], host, port): cred
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
