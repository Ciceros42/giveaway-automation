import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from db.client import db
import config
from entry.form_entry import enter_giveaway


def pick_account(deal_id_str: str) -> dict:
    """UUID-safe round-robin: hash UUID hex to int, mod 3."""
    idx = int(deal_id_str.replace("-", ""), 16) % len(config.ACCOUNTS)
    return config.ACCOUNTS[idx]


def main():
    # Query unentered giveaways that have an entry URL and < 3 attempts
    rows = (
        db.table("deals")
        .select("*")
        .eq("entered", False)
        .eq("flagged_manual", False)
        .not_.is_("entry_url", "null")
        .lt("entry_attempts", 3)
        .limit(50)
        .execute()
        .data
    )

    if not rows:
        print("[INFO] No unentered giveaways found.")
        return

    print(f"[INFO] Attempting entry for {len(rows)} giveaways")

    async def run_all():
        return await asyncio.gather(
            *[enter_giveaway(deal, pick_account(deal["id"])) for deal in rows],
            return_exceptions=True,
        )

    results = asyncio.run(run_all())

    entered_count = 0
    for deal, result in zip(rows, results):
        success = result is True  # False, exception object, or True
        if isinstance(result, Exception):
            print(f"[WARN] Entry exception for {deal.get('entry_url')}: {result}")

        update = {"entry_attempts": deal["entry_attempts"] + 1}
        if success:
            acct = pick_account(deal["id"])
            update.update({
                "entered":    True,
                "entered_at": datetime.now(timezone.utc).isoformat(),
                "entry_email": acct["email"],
            })
            entered_count += 1

        try:
            db.table("deals").update(update).eq("id", deal["id"]).execute()
        except Exception as e:
            print(f"[WARN] DB update failed for deal {deal['id']}: {e}")

    print(f"[INFO] Successfully entered: {entered_count}/{len(rows)}")


if __name__ == "__main__":
    main()
