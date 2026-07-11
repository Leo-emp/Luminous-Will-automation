# ============================================================
# ADMIN FAILURE NOTIFICATION — notify_admin.py
# ============================================================
# Sends structured failure alerts when pipeline jobs crash.
# Two notification channels:
#   1. Always: structured log to stdout (visible in GitHub Actions / HF logs)
#   2. Optional: POST to ALERT_WEBHOOK_URL env var (Slack/Discord)
#
# This module NEVER raises — alerting failures are logged
# but can never crash the pipeline that called us.
#
# Usage:
#   from notify_admin import notify_admin
#   notify_admin("Short Video", error, {"topic": "resilience"})
#
# Environment variables:
#   ALERT_WEBHOOK_URL — Slack/Discord webhook URL (optional)
# ============================================================

import os
import json
import traceback
from datetime import datetime, timezone


def notify_admin(cron_name: str, error: Exception, details: dict = None):
    """
    # Sends a failure alert when a pipeline job fails.
    # cron_name: human-readable name like "Short Video" or "Quote Reel"
    # error: the caught exception
    # details: optional context dict for debugging (topic, format, etc.)
    #
    # NEVER raises — if alerting itself fails, it just prints a warning.
    """
    try:
        # # Extract error info
        error_message = str(error)
        timestamp = datetime.now(timezone.utc).isoformat()
        stack = traceback.format_exception(type(error), error, error.__traceback__)
        stack_str = "".join(stack) if stack else "No traceback"

        # # ── Channel 1: Structured console log ──────────────────
        # # Always fires — visible in GitHub Actions logs and HF Space logs
        log_entry = {
            "level": "PIPELINE_FAILURE",
            "pipeline": cron_name,
            "error": error_message,
            "timestamp": timestamp,
        }
        if details:
            log_entry.update(details)
        print(f"\n[ALERT] {json.dumps(log_entry)}")
        print(f"[ALERT] Stack trace:\n{stack_str}")

        # # ── Channel 2: Webhook (Slack/Discord) ────────────────
        # # Only fires if ALERT_WEBHOOK_URL is set in env vars
        webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
        if not webhook_url:
            return

        # # Use urllib to avoid adding requests as a dependency
        import urllib.request
        import urllib.error

        # # Build Slack-compatible payload
        text_lines = [
            f"*Luminous Will Pipeline Failure*",
            f"*Pipeline:* {cron_name}",
            f"*Error:* {error_message}",
            f"*Time:* {timestamp}",
        ]
        if details:
            text_lines.append(f"*Details:* {json.dumps(details)}")

        payload = json.dumps({
            "text": "\n".join(text_lines),
            "pipeline": cron_name,
            "error": error_message,
            "timestamp": timestamp,
            "details": details or {},
        }).encode("utf-8")

        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)

    except Exception as alert_error:
        # # Never let alerting crash the pipeline
        print(f"[ALERT] Failed to send notification: {alert_error}")
