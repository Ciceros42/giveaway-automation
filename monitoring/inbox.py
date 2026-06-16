import sys
import os
import imaplib
import email as emaillib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import db
import config
from digest.sender import forward_win

WIN_KEYWORDS = [
    "winner",
    "you won",
    "congratulations",
    "claim your prize",
    "selected",
    "you have been chosen",
]


def check_inbox(account: dict) -> int:
    """Check one inbox for win-pattern emails. Returns count of new wins forwarded."""
    forwarded = 0
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(account["email"], account["app_password"])
    mail.select("inbox")

    # Union matches across all keywords (one IMAP SEARCH per keyword)
    all_ids: set[bytes] = set()
    for keyword in WIN_KEYWORDS:
        try:
            _, ids = mail.search(None, f'SUBJECT "{keyword}"')
            if ids[0]:
                all_ids.update(ids[0].split())
        except Exception as e:
            print(f"[WARN] IMAP search failed for keyword '{keyword}': {e}")

    for msg_id in all_ids:
        try:
            _, data = mail.fetch(msg_id, "(RFC822)")
            if not data or not data[0]:
                continue
            msg              = emaillib.message_from_bytes(data[0][1])
            gmail_message_id = msg.get("Message-ID") or f"{account['email']}:{msg_id.decode()}"
            subject          = msg.get("Subject", "")

            # Skip if already logged
            existing = (
                db.table("win_notifications")
                .select("id")
                .eq("gmail_message_id", gmail_message_id)
                .execute()
                .data
            )
            if existing:
                continue

            now_ts = datetime.now(timezone.utc).isoformat()

            # Log to DB
            db.table("win_notifications").insert({
                "gmail_message_id": gmail_message_id,
                "inbox_email":      account["email"],
                "subject":          subject,
                "sender":           msg.get("From"),
                "received_at":      now_ts,
            }).execute()

            # Forward
            try:
                forward_win(msg, account["email"])
                db.table("win_notifications").update({
                    "forwarded_at": datetime.now(timezone.utc).isoformat()
                }).eq("gmail_message_id", gmail_message_id).execute()
                forwarded += 1
                print(f"[INFO] Win forwarded: '{subject}' from {account['email']}")
            except Exception as e:
                print(f"[WARN] Forward failed for '{subject}': {e}")

        except Exception as e:
            print(f"[WARN] Failed to process message {msg_id}: {e}")

    mail.logout()
    return forwarded


def main():
    total_forwarded = 0
    for account in config.MONITORED_ACCOUNTS:
        try:
            count = check_inbox(account)
            total_forwarded += count
        except Exception as e:
            print(f"[WARN] Inbox check failed for {account['email']}: {e}")

    print(f"[INFO] Total wins forwarded this run: {total_forwarded}")

    # Heartbeat: single-row upsert keeps Supabase free tier active
    db.table("heartbeat").upsert(
        {"id": "singleton", "checked_at": datetime.now(timezone.utc).isoformat()},
        on_conflict="id",
    ).execute()
    print("[INFO] Heartbeat updated")


if __name__ == "__main__":
    main()
