from __future__ import annotations

import logging

import httpx


logger = logging.getLogger(__name__)


def notify_review_queue(webhook_url: str, payload: dict) -> bool:
    if not webhook_url:
        return False
    try:
        response = httpx.post(webhook_url, json=payload, timeout=2.5)
        response.raise_for_status()
        return True
    except Exception as exc:
        # Workflow execution must not fail because an optional notification
        # channel is unavailable. The review task remains persisted in SQL.
        logger.warning("n8n webhook unavailable: %s", exc)
        return False

