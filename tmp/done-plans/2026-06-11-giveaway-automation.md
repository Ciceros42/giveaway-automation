# Plan: SLC Giveaway & Deal Automation

## Overview

A Python-based automation system that scrapes Salt Lake City/Utah deals and giveaways twice daily, auto-enters form-based contests, monitors Gmail inboxes for wins every 6 hours, and emails a daily ranked digest to reurichards@gmail.com. Runs entirely on GitHub Actions (free) with Supabase as the database (free tier).

**Estimated monthly cost:** ~$2–4 (Claude Haiku parsing + 2captcha)
**No VPS. No always-on server.**

---

## Cadence Rationale

Deals and giveaways operate on day-to-week time frames — checking twice daily (6am + 6pm MST) captures everything meaningful without burning Actions minutes or Brave API quota. This cascade simplifies the entire system:

- Scrape: **twice daily** → Brave budget drops to ~600 queries/month (vs 2,000 limit) — all queries run every cycle, no rotation needed
- Entry: **after each scrape** via `workflow_run` → 2 Playwright startups/day (vs 12)
- Static sites: **included in regular scrape** → no separate cron needed
- Inbox monitor: **every 6 hours** → wins are still detected same-day while staying lightweight
- Digest: **daily 8am MST** → unchanged

---

## Architecture Overview

```
6am + 6pm MST: GitHub Actions → scrape.yml
  ├── all scrapers run (search + Reddit + KSL + static sites + social)
  ├── pre-filter dedup_keys already in Supabase
  ├── raw text → Claude Haiku (one call/doc) → structured JSON
  └── upsert into Supabase deals table

After each scrape: GitHub Actions → entry.yml (workflow_run)
  ├── query unentered giveaways (entry_attempts < 3, has entry_url)
  ├── Playwright fills form → 2captcha (semaphore=3) → submit
  ├── verify success by checking page for confirmation text
  └── update entry_attempts regardless; set entered=true only on confirmed success

Every 6 hours: GitHub Actions → inbox_monitor.yml
  ├── IMAP polls 3 Gmail inboxes (multi-keyword search, unioned)
  ├── dedup by gmail_message_id — skip already-logged messages
  ├── forward new wins to reurichards@gmail.com
  └── upsert single heartbeat row (keeps Supabase free tier active)

Daily 8am MST: GitHub Actions → digest.yml
  ├── query deals since last_digest_sent_at (stored in app_state table)
  └── send ranked HTML digest to reurichards@gmail.com

All workflows: failure alerting step (if: failure() → email via SMTP)
```

---

## Files Being Changed

```
giveaway-automation/                        ← NEW (root of new repo)
├── .github/
│   └── workflows/
│       ├── scrape.yml                      ← NEW (twice daily, no Playwright)
│       ├── entry.yml                       ← NEW (workflow_run trigger)
│       ├── inbox_monitor.yml               ← NEW (every 6 hours)
│       └── digest.yml                      ← NEW (daily 8am MST)
├── scrapers/
│   ├── __init__.py                         ← NEW
│   ├── run_all.py                          ← NEW (entry point)
│   ├── base.py                             ← NEW (BaseScraper abstract class)
│   ├── search.py                           ← NEW (Brave Search API)
│   ├── reddit.py                           ← NEW (r/SaltLakeCity, r/Utah)
│   ├── ksl.py                              ← NEW (KSL.com deals/contests)
│   ├── static_sites.py                     ← NEW (radio + restaurants, config-driven)
│   └── social.py                           ← NEW (public FB/IG via search URLs)
├── parser/
│   ├── __init__.py                         ← NEW
│   └── claude_parser.py                    ← NEW (Claude Haiku, one call/doc)
├── entry/
│   ├── __init__.py                         ← NEW
│   ├── run_entries.py                      ← NEW (query + round-robin + update)
│   ├── form_entry.py                       ← NEW (Playwright + CAPTCHA)
│   └── captcha.py                          ← NEW (2captcha wrapper)
├── monitoring/
│   ├── __init__.py                         ← NEW
│   └── inbox.py                            ← NEW (IMAP multi-keyword + dedup)
├── digest/
│   ├── __init__.py                         ← NEW
│   ├── builder.py                          ← NEW (HTML template)
│   ├── sender.py                           ← NEW (SMTP via Gmail app password)
│   └── send_daily.py                       ← NEW (entry point)
├── db/
│   ├── __init__.py                         ← NEW
│   ├── client.py                           ← NEW (Supabase singleton + helpers)
│   └── schema.sql                          ← NEW
├── utils/
│   ├── __init__.py                         ← NEW
│   └── alert.py                            ← NEW (SMTP failure alert helper)
├── config.py                               ← NEW
└── requirements.txt                        ← NEW
```

---

## Database Schema (`db/schema.sql`)

```sql
create table deals (
  id                uuid    primary key default gen_random_uuid(),
  dedup_key         text    not null,
  source            text    not null,
  title             text    not null,
  description       text,
  entry_url         text,                     -- nullable: coupons/deals may have no URL
  type              text    not null check (type in ('giveaway','deal','coupon','contest')),
  value_score       int     not null check (value_score between 1 and 10),
  value_description text,
  expiry_date       text,                     -- stored as text (Claude returns freeform)
  found_at          timestamptz default now(),
  entered           boolean default false,
  entered_at        timestamptz,
  entry_email       text,
  entry_attempts    int     default 0,
  flagged_manual    boolean default false,
  won               boolean default false,
  won_at            timestamptz,
  constraint deals_dedup_key_unique unique (dedup_key)
);

create table win_notifications (
  id                uuid    primary key default gen_random_uuid(),
  gmail_message_id  text    not null,
  inbox_email       text    not null,
  subject           text,
  sender            text,
  received_at       timestamptz,
  forwarded_at      timestamptz,
  raw_snippet       text,
  constraint win_notifications_message_id_unique unique (gmail_message_id)
);

-- Single-row heartbeat: upsert on fixed key, no unbounded growth
create table heartbeat (
  id         text primary key default 'singleton',
  checked_at timestamptz default now()
);

-- Key-value state: stores last_digest_sent_at so digest window is exact
create table app_state (
  key   text primary key,
  value text
);
insert into app_state (key, value) values ('last_digest_sent_at', now()::text);
```

---

## `config.py` Structure

```python
import os

SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
BRAVE_API_KEY        = os.environ["BRAVE_API_KEY"]
TWOCAPTCHA_API_KEY   = os.environ["TWOCAPTCHA_API_KEY"]
DIGEST_TARGET        = os.environ.get("DIGEST_TARGET", "reurichards@gmail.com")
FORWARD_TO           = os.environ.get("FORWARD_TO",   "reurichards@gmail.com")

# Account 1 also sends digests and alerts — no 4th account needed
ACCOUNTS = [
    {"email": os.environ["ENTRY_EMAIL_1"], "app_password": os.environ["GMAIL_ACCOUNT_1_APP_PASSWORD"], "name": os.environ["ENTRY_NAME_1"]},
    {"email": os.environ["ENTRY_EMAIL_2"], "app_password": os.environ["GMAIL_ACCOUNT_2_APP_PASSWORD"], "name": os.environ["ENTRY_NAME_2"]},
    {"email": os.environ["ENTRY_EMAIL_3"], "app_password": os.environ["GMAIL_ACCOUNT_3_APP_PASSWORD"], "name": os.environ["ENTRY_NAME_3"]},
]

MONITORED_ACCOUNTS = ACCOUNTS  # same list, all 3 inboxes monitored
DIGEST_EMAIL        = ACCOUNTS[0]["email"]
DIGEST_APP_PASSWORD = ACCOUNTS[0]["app_password"]
```

---

## Key Pseudocode

### Scraper pipeline (`scrapers/run_all.py`)

```python
import hashlib

def make_dedup_key(source, title, entry_url):
    raw = f"{source}|{title}|{entry_url or ''}"
    return hashlib.md5(raw.encode()).hexdigest()

# All scrapers run every cycle — twice/day is low enough for static sites too
raw_results = []
for scraper in [SearchScraper(), RedditScraper(), KSLScraper(), StaticSitesScraper(), SocialScraper()]:
    try:
        raw_results.extend(scraper.scrape())
    except Exception as e:
        print(f"[WARN] {scraper.__class__.__name__} failed: {e}")

# Pre-filter: skip items whose dedup_key is already in Supabase
existing_keys = {r["dedup_key"] for r in db.table("deals").select("dedup_key").execute().data}
new_results = [
    r for r in raw_results
    if make_dedup_key(r["source"], r.get("title",""), r.get("url")) not in existing_keys
]

# Parse — one Claude call per new document
deals = []
for item in new_results:
    try:
        parsed = claude_parser.parse_one(item["text"], item["source"], item.get("url"))
        if parsed and parsed.get("is_slc_utah_relevant"):
            parsed["dedup_key"]     = make_dedup_key(parsed["source"], parsed["title"], parsed.get("entry_url"))
            parsed["flagged_manual"]= parsed.pop("requires_manual_entry")
            parsed.pop("is_slc_utah_relevant")
            deals.append(parsed)
    except Exception as e:
        print(f"[WARN] Parse failed for {item.get('url')}: {e}")

if deals:
    db.table("deals").upsert(deals, on_conflict="dedup_key").execute()
```

### Claude Haiku parser (`parser/claude_parser.py`)

```python
# NOTE: Verify model ID before build: https://docs.anthropic.com/en/docs/about-claude/models
MODEL = "claude-haiku-4-5-20251001"

def parse_one(raw_html, source, url=None):
    text = trafilatura.extract(raw_html) or raw_html[:3000]  # strips HTML, cuts tokens ~80%

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        tools=[{
            "name": "extract_deal",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title":                 {"type": "string"},
                    "description":           {"type": "string"},
                    "entry_url":             {"type": ["string", "null"]},
                    "type":                  {"type": "string", "enum": ["giveaway","deal","coupon","contest"]},
                    "value_score":           {"type": "integer", "minimum": 1, "maximum": 10},
                    "value_description":     {"type": "string"},
                    "expiry_date":           {"type": ["string", "null"],
                                             "description": "ISO YYYY-MM-DD or null"},
                    "requires_manual_entry": {"type": "boolean"},
                    "is_slc_utah_relevant":  {"type": "boolean"}
                },
                "required": ["title","type","value_score","requires_manual_entry","is_slc_utah_relevant"]
            }
        }],
        tool_choice={"type": "tool", "name": "extract_deal"},
        # tool_choice forces a call on every doc — caller filters on is_slc_utah_relevant
        system=(
            "Extract deal or giveaway info from scraped text. "
            "Set is_slc_utah_relevant=false if not relevant to Salt Lake City / Utah, "
            "or if no actual deal/giveaway is present. "
            "Set requires_manual_entry=true if entry needs social actions (like, follow, comment). "
            "Value score: 10=cash $100+, 9=cash $50-99, 8=free meal, 7=gift card $50+, "
            "6=gift card $20-49, 5=free product, 4=50%+ off, 3=25-49% off, 2=notable deal, 1=minor. "
            "expiry_date: ISO YYYY-MM-DD or null."
        ),
        messages=[{"role": "user", "content": f"Source: {source}\nURL: {url}\n\n{text[:3500]}"}]
    )
    result = response.content[0].input
    result["source"] = source
    return result
```

### Form entry (`entry/form_entry.py`)

```python
import asyncio

SEM = asyncio.Semaphore(3)  # max 3 concurrent 2captcha solves

async def enter_giveaway(deal, account):
    # account = {"email": ..., "name": ..., "app_password": ...}
    async with SEM:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await page.goto(deal["entry_url"], wait_until="domcontentloaded")

            for selector in ['input[name*="email"]', 'input[type="email"]']:
                if await page.query_selector(selector):
                    await page.fill(selector, account["email"]); break
            for selector in ['input[name*="name"]', 'input[name*="first"]']:
                if await page.query_selector(selector):
                    await page.fill(selector, account["name"]); break

            # reCAPTCHA v2: inject token AND fire data-callback
            captcha_el = await page.query_selector(".g-recaptcha")
            if captcha_el:
                sitekey  = await captcha_el.get_attribute("data-sitekey")
                callback = await captcha_el.get_attribute("data-callback") or "null"
                solver   = TwoCaptcha(config.TWOCAPTCHA_API_KEY)
                token    = solver.recaptcha(sitekey=sitekey, url=deal["entry_url"])["code"]
                await page.evaluate(f'''
                    document.getElementById("g-recaptcha-response").value = "{token}";
                    document.getElementById("g-recaptcha-response").innerHTML = "{token}";
                    if (typeof window["{callback}"] === "function") {{ window["{callback}"]("{token}"); }}
                ''')

            submit = await page.query_selector('button[type="submit"], input[type="submit"]')
            if not submit:
                return False
            await submit.click()
            await page.wait_for_timeout(3000)

            # Verify success — don't trust "button was clicked"
            page_text = (await page.inner_text("body")).lower()
            return any(s in page_text for s in ["thank you", "you're entered", "success", "confirmed", "submitted"])
```

### Entry runner (`entry/run_entries.py`)

```python
def pick_account(deal_id_str):
    # UUID-safe round-robin: each account has a distinct email + name so entries don't look identical
    idx = int(deal_id_str.replace("-", ""), 16) % 3
    return config.ACCOUNTS[idx]  # {"email": ..., "name": ..., "app_password": ...}

rows = (db.table("deals")
    .select("*")
    .eq("entered", False)
    .eq("flagged_manual", False)
    .not_.is_("entry_url", "null")
    .lt("entry_attempts", 3)
    .limit(50)                       # don't fetch unbounded result set
    .execute().data)

tasks = [enter_giveaway(deal, pick_account(deal["id"])) for deal in rows]
results = asyncio.run(asyncio.gather(*tasks, return_exceptions=True))

for deal, result in zip(rows, results):
    success = result is True  # False, exception, or True
    update  = {"entry_attempts": deal["entry_attempts"] + 1}
    if success:
        from datetime import datetime, timezone
        acct = pick_account(deal["id"])
        update.update({"entered": True, "entered_at": datetime.now(timezone.utc).isoformat(), "entry_email": acct["email"]})
    db.table("deals").update(update).eq("id", deal["id"]).execute()
```

### Gmail inbox polling (`monitoring/inbox.py`)

```python
import imaplib, email as emaillib, asyncio
from db.client import db
import config

WIN_KEYWORDS = ["winner", "you won", "congratulations", "claim your prize", "selected"]

for account in config.MONITORED_ACCOUNTS:
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(account["email"], account["app_password"])
        mail.select("inbox")

        # Multi-keyword search: union all matches, dedup by message ID
        all_ids = set()
        for keyword in WIN_KEYWORDS:
            _, ids = mail.search(None, f'SUBJECT "{keyword}"')
            if ids[0]:
                all_ids.update(ids[0].split())

        for msg_id in all_ids:
            _, data = mail.fetch(msg_id, "(RFC822)")
            msg              = emaillib.message_from_bytes(data[0][1])
            gmail_message_id = msg.get("Message-ID") or f"{account['email']}:{msg_id.decode()}"
            subject          = msg.get("Subject", "")

            # Skip if already logged
            if db.table("win_notifications").select("id").eq("gmail_message_id", gmail_message_id).execute().data:
                continue

            from digest.sender import forward_win
            from datetime import datetime, timezone
            now_ts = datetime.now(timezone.utc).isoformat()

            db.table("win_notifications").insert({
                "gmail_message_id": gmail_message_id,
                "inbox_email":      account["email"],
                "subject":          subject,
                "sender":           msg.get("From"),
                "received_at":      now_ts,
            }).execute()

            forward_win(msg, account["email"])
            db.table("win_notifications").update({"forwarded_at": datetime.now(timezone.utc).isoformat()}).eq("gmail_message_id", gmail_message_id).execute()

        mail.logout()
    except Exception as e:
        print(f"[WARN] Inbox check failed for {account['email']}: {e}")

# Upsert single heartbeat row — keeps Supabase free tier active, no table growth
from datetime import datetime, timezone
db.table("heartbeat").upsert({"id": "singleton", "checked_at": datetime.now(timezone.utc).isoformat()}, on_conflict="id").execute()
```

### Daily digest (`digest/send_daily.py`)

```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

# Use last_digest_sent_at from app_state — exact window, survives missed runs
row   = db.table("app_state").select("value").eq("key", "last_digest_sent_at").execute().data
since = row[0]["value"] if row else (now.isoformat())

wins      = db.table("win_notifications").select("*").is_("forwarded_at", "null").execute().data
entered   = db.table("deals").select("*").eq("entered", True).gte("entered_at", since).execute().data
manual    = db.table("deals").select("*").eq("flagged_manual", True).eq("entered", False).gte("found_at", since).execute().data
top_deals = (db.table("deals").select("*").gte("value_score", 4)
             .not_.eq("type", "giveaway").gte("found_at", since)
             .order("value_score", desc=True).limit(15).execute().data)

html = builder.build(wins, entered, manual, top_deals)
sender.send_smtp(html, subject=f"SLC Deal Digest — {now.strftime('%b %d')}")

# Update last sent timestamp
db.table("app_state").upsert({"key": "last_digest_sent_at", "value": now.isoformat()}, on_conflict="key").execute()
```

---

## GitHub Actions Workflows

### `scrape.yml` — twice daily, 6am + 6pm MST (no Playwright)
```yaml
name: Scrape Deals
on:
  schedule:
    - cron: '0 1,13 * * *'     # 01:00 + 13:00 UTC = 6pm + 6am MST
  workflow_dispatch:
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12', cache: 'pip' }
      - run: pip install -r requirements.txt
      - run: python -m scrapers.run_all
        env:
          SUPABASE_URL:         ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          ANTHROPIC_API_KEY:    ${{ secrets.ANTHROPIC_API_KEY }}
          BRAVE_API_KEY:        ${{ secrets.BRAVE_API_KEY }}
      - name: Alert on failure
        if: failure()
        run: python -m utils.alert "${{ github.workflow }}" "${{ github.run_id }}"
        env:
          DIGEST_EMAIL:        ${{ secrets.ENTRY_EMAIL_1 }}
          DIGEST_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_1_APP_PASSWORD }}
```

### `entry.yml` — after each scrape (2x/day)
```yaml
name: Enter Giveaways
on:
  workflow_run:
    workflows: ["Scrape Deals"]
    types: [completed]
  workflow_dispatch:
jobs:
  entry:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12', cache: 'pip' }
      - run: pip install -r requirements.txt
      - uses: actions/cache@v4
        with:
          path: ~/.cache/ms-playwright
          key: pw-${{ runner.os }}-${{ hashFiles('requirements.txt') }}
      - run: playwright install --with-deps chromium
      - run: python -m entry.run_entries
        env:
          SUPABASE_URL:         ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          TWOCAPTCHA_API_KEY:   ${{ secrets.TWOCAPTCHA_API_KEY }}
          ENTRY_EMAIL_1:        ${{ secrets.ENTRY_EMAIL_1 }}
          ENTRY_EMAIL_2:        ${{ secrets.ENTRY_EMAIL_2 }}
          ENTRY_EMAIL_3:        ${{ secrets.ENTRY_EMAIL_3 }}
          ENTRY_NAME:           ${{ secrets.ENTRY_NAME }}
      - name: Alert on failure
        if: failure()
        run: python -c "import smtplib,os; ..."
        env:
          DIGEST_EMAIL:        ${{ secrets.ENTRY_EMAIL_1 }}
          DIGEST_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_1_APP_PASSWORD }}
```

### `inbox_monitor.yml` — every 6 hours
```yaml
name: Inbox Monitor
on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:
jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12', cache: 'pip' }
      - run: pip install -r requirements.txt
      - run: python -m monitoring.inbox
        env:
          SUPABASE_URL:                 ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY:         ${{ secrets.SUPABASE_SERVICE_KEY }}
          ENTRY_EMAIL_1:                ${{ secrets.ENTRY_EMAIL_1 }}
          ENTRY_EMAIL_2:                ${{ secrets.ENTRY_EMAIL_2 }}
          ENTRY_EMAIL_3:                ${{ secrets.ENTRY_EMAIL_3 }}
          GMAIL_ACCOUNT_1_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_1_APP_PASSWORD }}
          GMAIL_ACCOUNT_2_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_2_APP_PASSWORD }}
          GMAIL_ACCOUNT_3_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_3_APP_PASSWORD }}
          DIGEST_EMAIL:                 ${{ secrets.DIGEST_EMAIL }}
          DIGEST_APP_PASSWORD:          ${{ secrets.DIGEST_APP_PASSWORD }}
          FORWARD_TO:                   reurichards@gmail.com
      - name: Alert on failure
        if: failure()
        run: python -c "import smtplib,os; ..."
        env:
          DIGEST_EMAIL:        ${{ secrets.ENTRY_EMAIL_1 }}
          DIGEST_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_1_APP_PASSWORD }}
```

### `digest.yml` — daily 8am MST (3pm UTC)
```yaml
name: Daily Digest
on:
  schedule:
    - cron: '0 15 * * *'
  workflow_dispatch:
jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12', cache: 'pip' }
      - run: pip install -r requirements.txt
      - run: python -m digest.send_daily
        env:
          SUPABASE_URL:         ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          ENTRY_EMAIL_1:        ${{ secrets.ENTRY_EMAIL_1 }}
          GMAIL_ACCOUNT_1_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_1_APP_PASSWORD }}
          ENTRY_NAME_1:         ${{ secrets.ENTRY_NAME_1 }}
          ENTRY_NAME_2:         ${{ secrets.ENTRY_NAME_2 }}
          ENTRY_NAME_3:         ${{ secrets.ENTRY_NAME_3 }}
          DIGEST_TARGET:        reurichards@gmail.com
      - name: Alert on failure
        if: failure()
        run: python -c "import smtplib,os; ..."
        env:
          DIGEST_EMAIL:        ${{ secrets.ENTRY_EMAIL_1 }}
          DIGEST_APP_PASSWORD: ${{ secrets.GMAIL_ACCOUNT_1_APP_PASSWORD }}
```

---

## Failure Alert Helper

Extract the inline Python into a reusable helper called in every workflow's `if: failure()` step:

```python
# utils/alert.py — called as: python -m utils.alert "Scrape Deals" "$RUN_ID"
import smtplib, os, sys
from email.mime.text import MIMEText

def send_alert(workflow_name, run_id):
    msg          = MIMEText(f"Workflow '{workflow_name}' failed.\nRun: {run_id}")
    msg["Subject"] = f"[SLC Deals] Workflow failure: {workflow_name}"
    msg["From"]    = os.environ["DIGEST_EMAIL"]
    msg["To"]      = "reurichards@gmail.com"
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["DIGEST_EMAIL"], os.environ["DIGEST_APP_PASSWORD"])
        s.sendmail(msg["From"], [msg["To"]], msg.as_string())

if __name__ == "__main__":
    send_alert(sys.argv[1], sys.argv[2])
```

Workflow failure step becomes:
```yaml
- name: Alert on failure
  if: failure()
  run: python -m utils.alert "${{ github.workflow }}" "${{ github.run_id }}"
  env:
    DIGEST_EMAIL:        ${{ secrets.DIGEST_EMAIL }}
    DIGEST_APP_PASSWORD: ${{ secrets.DIGEST_APP_PASSWORD }}
```

---

## Search Queries (`scrapers/search.py`)

All queries run every cycle — 10 queries × 2 runs/day × 30 days = 600/month (well under 2,000 free limit, no rotation needed):

```python
QUERIES = [
    '"salt lake city" giveaway free 2026',
    '"salt lake" restaurant "free meal" contest',
    '"SLC" giveaway win prize food',
    'site:facebook.com "salt lake" giveaway',
    'site:instagram.com "salt lake city" giveaway',
    '"utah" restaurant deal coupon promotion',
    '"salt lake valley" free contest enter',
    'KSL contest utah giveaway',
    'utah local business giveaway enter',
    '"salt lake" free food deal this week',
]
```

---

## Static Sites Config (`scrapers/static_sites.py`)

Radio + restaurants share identical scrape logic — single config-driven file:

```python
STATIC_SITES = [
    {"source": "radio",      "url": "https://x96.com/contests"},
    {"source": "radio",      "url": "https://www.mix1051.com/contests"},
    {"source": "radio",      "url": "https://www.kubl.com/contests"},
    {"source": "radio",      "url": "https://www.hits1015.com/contests"},
    {"source": "restaurant", "url": "https://www.costavida.com/deals"},
    {"source": "restaurant", "url": "https://www.jcwsburgers.com"},
    {"source": "restaurant", "url": "https://www.swignsweets.com"},
    {"source": "restaurant", "url": "https://www.cubbysslc.com"},
    {"source": "restaurant", "url": "https://www.redrobin.com/specials"},
]
# Excluded: Chick-fil-A (app-gated), Groupon (bot detection) — Brave search covers both
```

---

## Reddit Scraper Note (`scrapers/reddit.py`)

Reddit's JSON API requires a `User-Agent` header or returns 429/browser redirect:

```python
headers = {"User-Agent": "script:slc-deal-bot:v1.0 (automated scraper)"}
r = requests.get("https://www.reddit.com/r/SaltLakeCity/new.json?limit=25", headers=headers)
```

---

## Value Scoring Reference

| Score | Meaning |
|-------|---------|
| 10 | Cash prize $100+ |
| 9 | Cash prize $50–$99 |
| 8 | Free full meal |
| 7 | Gift card $50+ |
| 6 | Gift card $20–$49 |
| 5 | Free product/item |
| 4 | 50%+ off |
| 3 | 25–49% off |
| 2 | Notable deal (<25% off) |
| 1 | Minor coupon |

Digest shows: all giveaways (entered or flagged) + deals scoring ≥ 4.

---

## Requirements (`requirements.txt`)

```
anthropic>=0.40.0
playwright==1.60.0
2captcha-python>=2.0.7
supabase>=2.0.0
trafilatura>=1.12.0
requests>=2.32.0
```

`imaplib` and `smtplib` are Python standard library — no extra packages needed.

---

## One-Time Setup Sequence

1. Repo already created at github.com/Ciceros42 — public repo, unlimited free Actions minutes
2. Create Supabase project → run `db/schema.sql`
3. For each of the 3 entry accounts:
   - Enable 2-Step Verification → Google Account → Security → App Passwords → generate for "Mail"
   - App passwords bypass OAuth entirely — no Cloud project, no scope verification, no expiry
   - Account 1 also sends digests and alerts (no 4th account needed)
4. Add secrets to GitHub repo Settings → Secrets:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   - `ANTHROPIC_API_KEY`
   - `BRAVE_API_KEY` (sign up at api.search.brave.com)
   - `TWOCAPTCHA_API_KEY` (fund ~$5 to start)
   - `ENTRY_EMAIL_1`, `ENTRY_EMAIL_2`, `ENTRY_EMAIL_3`
   - `GMAIL_ACCOUNT_1_APP_PASSWORD`, `GMAIL_ACCOUNT_2_APP_PASSWORD`, `GMAIL_ACCOUNT_3_APP_PASSWORD`
   - `ENTRY_NAME_1`, `ENTRY_NAME_2`, `ENTRY_NAME_3` (three distinct full names, one per account)
5. Push code → workflows activate on next cron tick

---

## Gotchas & Notes

- **Bing Web Search API retired Aug 2025** — use Brave Search API (api.search.brave.com). 2×/day = ~600 queries/month, well under 2,000 free limit.
- **Gmail: App Passwords, not OAuth.** `gmail.readonly`/`gmail.send` are restricted scopes requiring Google verification. App passwords + IMAP/SMTP sidestep this entirely. Requires 2FA on each account. Account 1 doubles as the digest/alert sender — no 4th account needed.
- **Public repo (github.com/Ciceros42)** — unlimited free Actions minutes, no 2,000/month cap concern.
- **Supabase `on_conflict` must be a string**: `upsert(rows, on_conflict="dedup_key")`. Requires matching UNIQUE constraint.
- **reCAPTCHA data-callback must fire** after token injection — setting `innerHTML` alone is insufficient; the site's JS callback enables the submit button.
- **tool_choice forces extraction on every document** — Claude cannot return null. Filter post-call by `is_slc_utah_relevant == True`.
- **IMAP win search requires one call per keyword** — `SEARCH SUBJECT` takes one term at a time; union results across all WIN_KEYWORDS.
- **2captcha semaphore** limits concurrent solves to 3 — prevents throttling on low-balance accounts.
- **Playwright** only in `entry.yml` — `scrape.yml` is HTTP-only (saves minutes + simpler CI).
- **Reddit User-Agent** required: `User-Agent: script:slc-deal-bot:v1.0` or API returns 429.
- **Heartbeat** is a single-row upsert on `id='singleton'` — no unbounded growth.
- **Digest window** uses `last_digest_sent_at` from `app_state` table — survives missed runs cleanly.
- **Groupon + app-gated restaurants** excluded from static sites; Brave search picks them up incidentally.
- **Verify model ID** `claude-haiku-4-5-20251001` at https://docs.anthropic.com/en/docs/about-claude/models before building parser.

---

## Tasks (Implementation Order)

1. Create GitHub repo; push initial structure with empty `__init__.py` files
2. Write `db/schema.sql`; create Supabase project; run migration
3. Write `config.py` — all env vars + `MONITORED_ACCOUNTS` list
4. Write `db/client.py` — Supabase singleton, upsert helper, `make_dedup_key()`
5. Write `utils/alert.py` — SMTP failure alert helper
6. Write `parser/claude_parser.py` — `parse_one()`, trafilatura strip, post-call filter
7. Write `scrapers/base.py` — `BaseScraper` abstract class
8. Write `scrapers/search.py` — Brave Search API, full query list each run
9. Write `scrapers/reddit.py` — Reddit JSON API with proper User-Agent header
10. Write `scrapers/ksl.py` — KSL.com deals/contests
11. Write `scrapers/static_sites.py` — config-driven scraper for all radio + restaurant URLs
12. Write `scrapers/social.py` — extract FB/IG links from Brave results, fetch public pages
13. Write `scrapers/run_all.py` — try/except per scraper, pre-filter, parse, upsert
14. Write `entry/captcha.py` — 2captcha wrapper with retry + balance check
15. Write `entry/form_entry.py` — Playwright fill, reCAPTCHA callback injection, success check, Semaphore(3)
16. Write `entry/run_entries.py` — UUID-safe round-robin, limit(50), attempt tracking
17. Write `monitoring/inbox.py` — IMAP multi-keyword union, gmail_message_id dedup, heartbeat upsert
18. Write `digest/builder.py` — HTML template (wins / entered / manual / top deals / stats)
19. Write `digest/sender.py` — SMTP send + `forward_win()`
20. Write `digest/send_daily.py` — query from `last_digest_sent_at`, build, send, update state
21. Write all 4 GitHub Actions workflow files with failure alert steps
22. Write `requirements.txt`
23. **Local test:** run `python -m scrapers.run_all` with env vars set; verify Supabase rows
24. **Local test:** run `python -m entry.run_entries` against a known no-CAPTCHA test form; verify `entered=true`
25. **Local test:** seed a fake win email in one inbox; run `python -m monitoring.inbox`; verify forwarded + `win_notifications` row with `gmail_message_id`
26. Push to GitHub; verify all 4 workflows appear and trigger
27. Set up app passwords for all accounts; add all secrets

---

## Deprecated Code to Remove

None — new project.

---

**Plan confidence score: 9/10.** All reviewer blockers resolved; flow is clean and proportionate to twice-daily cadence. Residual uncertainty: public FB/IG HTML structure changes periodically and some static site URLs need live validation before first run.
