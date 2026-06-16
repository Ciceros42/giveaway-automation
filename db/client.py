import hashlib
import config
from supabase import create_client

_client = None

def get_db():
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client

db = get_db()

def make_dedup_key(source: str, title: str, entry_url: str | None) -> str:
    raw = f"{source}|{title}|{entry_url or ''}"
    return hashlib.md5(raw.encode()).hexdigest()
