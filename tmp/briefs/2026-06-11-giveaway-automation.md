# Brief: Automated Deal & Giveaway Scanner for Salt Lake City

## Why
Automate the discovery and entry of local deals, promotions, and giveaways in the Salt Lake Valley to maximize wins and savings with minimal manual effort.

## Context
- New standalone project, no existing codebase
- User has 3 Gmail accounts already set up for entry/monitoring
- User is technical, comfortable with self-managed infra
- Hosting must be free or near-free
- Notification target: reurichards@gmail.com

## Decisions
- **Hosting:** GitHub Actions (cron scrapers) + Supabase free tier (database) — zero fixed cost
- **Social media scraping:** Scrape public Facebook business pages and Instagram profiles directly (no auth). Use Google/Bing search queries (e.g. `"salt lake city giveaway" site:facebook.com`) to discover new pages. No fresh social accounts needed.
- **Social entry type (like/follow/comment):** Flag in daily digest for manual entry by user (Option B). Not automated.
- **Form-based giveaway entry:** Playwright fills forms automatically. 2captcha service handles CAPTCHAs (~$1–2/month).
- **Deal parsing:** Claude API parses raw scraped content into structured deal records with value scores (~$1–3/month).
- **Output:** Daily HTML digest email to reurichards@gmail.com — top deals ranked by value + new giveaways entered or flagged.
- **Win monitoring:** Gmail API watches all 3 inboxes continuously. Detected wins forwarded immediately to reurichards@gmail.com.
- **Geography:** Salt Lake Valley / Utah only.

## Sources to Monitor
- Google/Bing search: rotating queries for SLC giveaways and deals
- Public Facebook business pages (SLC restaurants, local businesses)
- Public Instagram business profiles (same)
- Reddit: r/SaltLakeCity, r/Utah
- KSL.com deals/contests
- Groupon SLC
- Local radio station contest pages (X96, Mix 105.1, etc.)
- Restaurant websites (deals/specials pages) — curated list
- Email newsletters (3 Gmail accounts subscribed to local business lists)

## Deal Value Scoring
Priority order for digest ranking:
1. Cash winnings
2. Free meals / free products
3. 50%+ off food/products
4. Sizeable gift cards
5. Other notable deals

## Rejected Alternatives
- **Fresh Facebook/Instagram accounts for social entry automation** — Meta detects and bans fake accounts quickly; high maintenance, fragile.
- **Personal account browser automation for social media** — ToS risk; Option B (manual entry from digest) achieves 80% of the value with zero risk.
- **Web dashboard (Vercel Next.js app)** — unnecessary complexity; daily email digest serves the use case cleanly.
- **Self-hosted VPS** — costs money; GitHub Actions + Supabase covers the need for free.

## Where Reasoning Clashed
None — decisions converged cleanly.

## One Thing to Do First
Set up the Supabase schema: a `deals` table (source, title, url, type, value_score, expiry, entered, flagged_manual) and a `entries` table (deal_id, email_used, entered_at, won).

## Direction
Build a Python-based scraping pipeline running on GitHub Actions cron jobs, storing structured deals in Supabase, auto-entering form-based giveaways via Playwright + 2captcha, monitoring 3 Gmail inboxes for wins, and delivering a daily ranked digest email to reurichards@gmail.com. Social giveaways requiring likes/follows/comments are flagged in the digest for manual entry.
