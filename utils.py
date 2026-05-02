"""
utils.py
--------
Shared utility functions for the JobPulse platform.
"""

import hashlib
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s — %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# ── Text helpers ──────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert a string to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def truncate(text: str, max_len: int = 512, ellipsis: str = "…") -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - len(ellipsis)] + ellipsis


def extract_salary_range(raw: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    Best-effort extraction of (min, max) salary from a free-text string.
    Returns (None, None) if parsing fails.

    Examples:
        "$60,000 – $80,000"  → (60000, 80000)
        "PKR 80k–120k/month" → (80000, 120000)
        "Competitive"        → (None, None)
    """
    if not raw:
        return None, None

    raw = raw.replace(",", "").replace(" ", "")
    numbers = re.findall(r"\d+(?:\.\d+)?[kK]?", raw)
    parsed = []
    for n in numbers:
        multiplier = 1000 if n.lower().endswith("k") else 1
        try:
            parsed.append(int(float(n.lower().rstrip("k")) * multiplier))
        except ValueError:
            continue

    if len(parsed) == 0:
        return None, None
    if len(parsed) == 1:
        return parsed[0], parsed[0]
    return min(parsed), max(parsed)


# ── Deduplication ─────────────────────────────────────────────────────────────

def _listing_fingerprint(listing: Dict[str, Any]) -> str:
    """SHA-1 fingerprint based on URL (primary) or title+company."""
    url = listing.get("url", "")
    if url:
        return hashlib.sha1(url.encode()).hexdigest()
    key = f"{listing.get('title','').lower()}|{listing.get('company','').lower()}"
    return hashlib.sha1(key.encode()).hexdigest()


def deduplicate(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate listings, preferring later records (more complete data)."""
    seen: Dict[str, Dict] = {}
    for item in listings:
        fp = _listing_fingerprint(item)
        seen[fp] = item  # last-write-wins within a single run
    return list(seen.values())


# ── Database helpers ──────────────────────────────────────────────────────────

def batch_upsert(listings: List[Any]) -> Tuple[int, int]:
    """
    Upsert a batch of JobListingCreate objects into the database.
    Returns (new_count, updated_count).

    Note: This is a synchronous wrapper; the actual DB calls use SQLAlchemy
    core upsert (INSERT … ON CONFLICT DO UPDATE).
    """
    # Lazy import to avoid circular deps and allow dry-run usage
    from backend.services.db import get_sync_engine
    from sqlalchemy import text

    engine = get_sync_engine()
    new_count = 0
    updated_count = 0

    with engine.begin() as conn:
        for listing in listings:
            data = listing.model_dump(exclude_none=True)
            # Simplified upsert via raw SQL — replace with ORM core upsert as needed
            result = conn.execute(
                text("""
                    INSERT INTO job_listings (
                        external_id, title, company, location,
                        job_type, category, salary_raw, url, source, scraped_at
                    ) VALUES (
                        :external_id, :title, :company, :location,
                        :job_type, :category, :salary_raw, :url, :source, :scraped_at
                    )
                    ON CONFLICT (url) DO UPDATE SET
                        title = EXCLUDED.title,
                        company = EXCLUDED.company,
                        salary_raw = EXCLUDED.salary_raw,
                        updated_at = NOW()
                    RETURNING (xmax = 0) AS inserted
                """),
                data,
            )
            row = result.fetchone()
            if row and row.inserted:
                new_count += 1
            else:
                updated_count += 1

    return new_count, updated_count


# ── Notifications ─────────────────────────────────────────────────────────────

def notify_slack(title: str, fields: Dict[str, str]) -> None:
    """Post a summary message to the configured Slack webhook (if set)."""
    from config import settings

    webhook = settings.SLACK_WEBHOOK_URL
    if not webhook:
        logger.debug("SLACK_WEBHOOK_URL not set — skipping notification.")
        return

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{k}*\n{v}"}
                for k, v in fields.items()
            ],
        },
    ]

    try:
        resp = requests.post(webhook, json={"blocks": blocks}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Slack notification failed: %s", exc)
