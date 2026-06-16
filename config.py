import os

SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
OPENAI_API_KEY       = os.environ.get("OPENAI_API_KEY", "")
TAVILY_API_KEY       = os.environ.get("TAVILY_API_KEY", "")
DIGEST_TARGET        = os.environ.get("DIGEST_TARGET", "reurichards@gmail.com")
FORWARD_TO           = os.environ.get("FORWARD_TO",    "reurichards@gmail.com")

# Account 1 doubles as digest/alert sender — no 4th account needed
def _account(n: int) -> dict | None:
    email = os.environ.get(f"ENTRY_EMAIL_{n}", "")
    pw    = os.environ.get(f"GMAIL_ACCOUNT_{n}_APP_PASSWORD", "")
    if not email or not pw:
        return None
    return {"email": email, "app_password": pw, "name": os.environ.get(f"ENTRY_NAME_{n}", "")}

ACCOUNTS = [a for a in (_account(1), _account(2), _account(3)) if a]

MONITORED_ACCOUNTS  = ACCOUNTS
DIGEST_EMAIL        = ACCOUNTS[0]["email"] if ACCOUNTS else ""
DIGEST_APP_PASSWORD = ACCOUNTS[0]["app_password"] if ACCOUNTS else ""
