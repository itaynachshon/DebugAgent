import atexit
import base64
import json
import os
import tempfile
from datetime import datetime, timezone

from google.cloud.logging import Client as LoggingClient

# Module-level temp file path, cleaned up on exit
_temp_credentials_path: str | None = None


def _ensure_credentials_file(config: dict) -> str:
    """
    Decode the base64-encoded SA key from .env and write it to a temp file.
    Sets GOOGLE_APPLICATION_CREDENTIALS so the SDK picks it up automatically.
    The temp file is cleaned up when the process exits.
    """
    global _temp_credentials_path

    if _temp_credentials_path and os.path.exists(_temp_credentials_path):
        return _temp_credentials_path

    sa_json = base64.b64decode(config["GCP_SA_KEY_BASE64"])

    fd, path = tempfile.mkstemp(suffix=".json", prefix="gcp_sa_")
    os.write(fd, sa_json)
    os.close(fd)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
    _temp_credentials_path = path

    # Clean up on exit
    atexit.register(lambda: os.unlink(path) if os.path.exists(path) else None)

    return path


def _get_client(config: dict) -> LoggingClient:
    """Create an authenticated Cloud Logging client using Application Default Credentials."""
    _ensure_credentials_file(config)
    return LoggingClient(project=config["GCP_PROJECT_ID"])


def query_logs(config: dict, filter_str: str, limit: int = 50) -> str:
    """
    Query GCP Cloud Logging with a custom filter string.

    Args:
        config: Application configuration dict.
        filter_str: Cloud Logging filter expression.
        limit: Maximum number of log entries to return.

    Returns:
        JSON string of matching log entries.
    """
    client = _get_client(config)
    entries = list(client.list_entries(filter_=filter_str, max_results=limit))

    results = []
    for entry in entries:
        log_entry = {
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "severity": entry.severity if entry.severity else "DEFAULT",
            "resource": {
                "type": entry.resource.type if entry.resource else None,
                "labels": dict(entry.resource.labels) if entry.resource and entry.resource.labels else {},
            },
        }

        # Extract text payload (system/application logs)
        if hasattr(entry, "text_payload") and entry.text_payload:
            log_entry["text_payload"] = entry.text_payload
        elif isinstance(entry.payload, str) and entry.payload:
            log_entry["text_payload"] = entry.payload
        elif isinstance(entry.payload, dict):
            log_entry["payload"] = entry.payload

        # Extract httpRequest field (request logs — contains URL, status, etc.)
        if hasattr(entry, "http_request") and entry.http_request:
            log_entry["http_request"] = entry.http_request

        results.append(log_entry)

    return json.dumps(results, indent=2, default=str)


def list_log_entries(config: dict, function_name: str, hours_ago: int = 24, limit: int = 50) -> str:
    """
    List recent log entries for a specific Cloud Function.

    Args:
        config: Application configuration dict.
        function_name: Name of the Cloud Function.
        hours_ago: How many hours back to search.
        limit: Maximum number of log entries to return.

    Returns:
        JSON string of matching log entries.
    """
    from datetime import timedelta
    past = datetime.now(timezone.utc) - timedelta(hours=hours_ago)

    # Filter specifically for HTTP request logs (not system/startup logs)
    # These contain httpRequest with the full URL, status, and response size
    filter_str = (
        f'resource.type="cloud_run_revision" '
        f'resource.labels.service_name="{function_name}" '
        f'logName="projects/{config["GCP_PROJECT_ID"]}/logs/run.googleapis.com%2Frequests" '
        f'timestamp>="{past.isoformat()}"'
    )

    return query_logs(config, filter_str, limit)
