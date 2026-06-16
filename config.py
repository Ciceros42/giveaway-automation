import os

SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY    = os.environ.get("ANTHROPIC_API_KEY", "")
BRAVE_API_KEY        = os.environ.get("BRAVE_API_KEY", "")
TWOCAPTCHA_API_KEY   = os.environ.get("TWOCAPTCHA_API_KEY", "")
DIGEST_TARGET        = os.environ.get("DIGEST_TARGET", "reurichards@gmail.com")
FORWARD_TO           = os.environ.get("FORWARD_TO",    "reurichards@gmail.com")

# Account 1 doubles as digest/alert sender — no 4th account needed
ACCOUNTS = [
    {
        "email":        os.environ["ENTRY_EMAIL_1"],
        "app_password": os.environ["GMAIL_ACCOUNT_1_APP_PASSWORD"],
        "name":         os.environ.get("ENTRY_NAME_1", ""),
    },
    {
        "email":        os.environ["ENTRY_EMAIL_2"],
        "app_password": os.environ["GMAIL_ACCOUNT_2_APP_PASSWORD"],
        "name":         os.environ.get("ENTRY_NAME_2", ""),
    },
    {
        "email":        os.environ["ENTRY_EMAIL_3"],
        "app_password": os.environ["GMAIL_ACCOUNT_3_APP_PASSWORD"],
        "name":         os.environ.get("ENTRY_NAME_3", ""),
    },
]

MONITORED_ACCOUNTS  = ACCOUNTS
DIGEST_EMAIL        = ACCOUNTS[0]["email"]
DIGEST_APP_PASSWORD = ACCOUNTS[0]["app_password"]
