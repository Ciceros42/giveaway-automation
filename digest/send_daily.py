import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from db.client import db
from digest.builder import build
from digest.sender import send_smtp


def main():
    now = datetime.now(timezone.utc)

    # Use last_digest_sent_at from app_state for an exact window
    try:
        row   = db.table("app_state").select("value").eq("key", "last_digest_sent_at").execute().data
        since = row[0]["value"] if row else now.isoformat()
    except Exception:
        since = now.isoformat()

    print(f"[INFO] Digest window: {since} → {now.isoformat()}")

    try:
        wins = (
            db.table("win_notifications")
            .select("*")
            .gte("received_at", since)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[WARN] Could not fetch wins: {e}")
        wins = []

    try:
        entered = (
            db.table("deals")
            .select("*")
            .eq("entered", True)
            .gte("entered_at", since)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[WARN] Could not fetch entered deals: {e}")
        entered = []

    try:
        manual = (
            db.table("deals")
            .select("*")
            .eq("flagged_manual", True)
            .eq("entered", False)
            .gte("found_at", since)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[WARN] Could not fetch manual deals: {e}")
        manual = []

    try:
        top_deals = (
            db.table("deals")
            .select("*")
            .gte("value_score", 4)
            .not_.eq("type", "giveaway")
            .gte("found_at", since)
            .order("value_score", desc=True)
            .limit(15)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[WARN] Could not fetch top deals: {e}")
        top_deals = []

    html = build(wins, entered, manual, top_deals)
    send_smtp(html, subject=f"SLC Deal Digest — {now.strftime('%b %d')}")

    # Update last sent timestamp
    db.table("app_state").upsert(
        {"key": "last_digest_sent_at", "value": now.isoformat()},
        on_conflict="key",
    ).execute()
    print("[INFO] app_state updated")


if __name__ == "__main__":
    main()
