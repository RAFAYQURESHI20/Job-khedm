"""
run_daily_pipeline.py
---------------------
Orchestrator for the full daily data pipeline:

  1. Pre-flight checks (DB connectivity, model availability)
  2. Run all scrapers
  3. ML classification pass
  4. Deduplication & database upsert
  5. Generate daily statistics report
  6. Notify stakeholders (Slack)
  7. Cleanup old / inactive listings

Designed to be called by GitHub Actions (see .github/workflows/daily_pipeline.yml)
or directly via cron / task scheduler.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

from config import settings
from utils import notify_slack, setup_logging

logger = logging.getLogger(__name__)
UTC = timezone.utc


# ── Pre-flight ────────────────────────────────────────────────────────────────

def check_db_connection() -> bool:
    try:
        from backend.services.db import get_sync_engine
        with get_sync_engine().connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("✔ Database connection OK")
        return True
    except Exception as exc:
        logger.error("✘ Database connection failed: %s", exc)
        return False


def check_model_available() -> bool:
    import os
    available = os.path.exists(settings.MODEL_PATH)
    if available:
        logger.info("✔ ML model found at %s", settings.MODEL_PATH)
    else:
        logger.warning("⚠ ML model not found at %s — classification will be skipped.", settings.MODEL_PATH)
    return available


# ── Statistics ────────────────────────────────────────────────────────────────

def generate_stats_report() -> dict:
    """Query the DB for today's pipeline statistics."""
    try:
        from backend.services.db import get_sync_engine
        import sqlalchemy as sa

        engine = get_sync_engine()
        today = datetime.now(UTC).date()

        with engine.connect() as conn:
            total = conn.execute(
                sa.text("SELECT COUNT(*) FROM job_listings WHERE DATE(scraped_at) = :d"),
                {"d": today},
            ).scalar()

            by_source = conn.execute(
                sa.text(
                    "SELECT source, COUNT(*) AS cnt "
                    "FROM job_listings WHERE DATE(scraped_at) = :d "
                    "GROUP BY source ORDER BY cnt DESC"
                ),
                {"d": today},
            ).fetchall()

            by_category = conn.execute(
                sa.text(
                    "SELECT category, COUNT(*) AS cnt "
                    "FROM job_listings WHERE DATE(scraped_at) = :d "
                    "GROUP BY category ORDER BY cnt DESC LIMIT 5"
                ),
                {"d": today},
            ).fetchall()

        return {
            "date": str(today),
            "total_today": total,
            "by_source": {row.source: row.cnt for row in by_source},
            "top_categories": {row.category: row.cnt for row in by_category},
        }
    except Exception as exc:
        logger.error("Stats query failed: %s", exc)
        return {}


# ── Cleanup ───────────────────────────────────────────────────────────────────

def deactivate_old_listings(days: int = 30) -> int:
    """Mark listings older than `days` days as inactive."""
    try:
        from backend.services.db import get_sync_engine
        import sqlalchemy as sa

        cutoff = datetime.now(UTC) - timedelta(days=days)
        engine = get_sync_engine()
        with engine.begin() as conn:
            result = conn.execute(
                sa.text(
                    "UPDATE job_listings SET is_active = FALSE "
                    "WHERE scraped_at < :cutoff AND is_active = TRUE"
                ),
                {"cutoff": cutoff},
            )
        deactivated = result.rowcount
        logger.info("Deactivated %d stale listings (older than %d days).", deactivated, days)
        return deactivated
    except Exception as exc:
        logger.error("Cleanup step failed: %s", exc)
        return 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> int:
    setup_logging(settings.LOG_LEVEL)
    pipeline_start = datetime.now(UTC)
    logger.info("═══ JobPulse Daily Pipeline — %s ═══", pipeline_start.date())

    # 1. Pre-flight
    if not check_db_connection():
        notify_slack("❌ Pipeline aborted", {"Reason": "DB connection failed"})
        return 2
    check_model_available()

    # 2–4. Delegate to final_scraper
    import subprocess
    scraper_args = ["python", "final_scraper.py", "--sources", args.sources]
    if args.dry_run:
        scraper_args.append("--dry-run")
    ret = subprocess.call(scraper_args)
    if ret != 0:
        logger.error("Scraper exited with code %d", ret)
        notify_slack("❌ Scraper failed", {"Exit code": str(ret)})
        return ret

    # 5. Stats
    stats = generate_stats_report()
    if stats:
        logger.info("Stats: %s", stats)

    # 6. Cleanup
    if not args.skip_cleanup:
        deactivate_old_listings(days=args.retention_days)

    # 7. Final notification
    elapsed = (datetime.now(UTC) - pipeline_start).total_seconds()
    notify_slack(
        "✅ Daily Pipeline Complete",
        {
            "Date": stats.get("date", "—"),
            "Total today": str(stats.get("total_today", "—")),
            "Duration": f"{elapsed:.0f}s",
            "Top source": next(iter(stats.get("by_source", {})), "—"),
        },
    )

    logger.info("Pipeline finished in %.1fs.", elapsed)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobPulse daily pipeline")
    parser.add_argument("--sources", default="all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-cleanup", action="store_true")
    parser.add_argument("--retention-days", type=int, default=30)
    sys.exit(main(parser.parse_args()))
