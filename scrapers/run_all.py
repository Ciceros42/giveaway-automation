import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import db, make_dedup_key
from parser.claude_parser import parse_one
from scrapers.search import SearchScraper
from scrapers.reddit import RedditScraper
from scrapers.ksl import KSLScraper
from scrapers.static_sites import StaticSitesScraper
from scrapers.social import SocialScraper


def main():
    # 1. Run all scrapers with per-scraper error isolation
    raw_results = []
    for scraper in [SearchScraper(), RedditScraper(), KSLScraper(), StaticSitesScraper(), SocialScraper()]:
        try:
            items = scraper.scrape()
            raw_results.extend(items)
            print(f"[INFO] {scraper.__class__.__name__}: {len(items)} items")
        except Exception as e:
            print(f"[WARN] {scraper.__class__.__name__} failed: {e}")

    print(f"[INFO] Total raw items: {len(raw_results)}")

    # 2. Pre-filter: skip items whose dedup_key is already in Supabase
    try:
        existing = db.table("deals").select("dedup_key").execute().data
        existing_keys = {r["dedup_key"] for r in existing}
    except Exception as e:
        print(f"[WARN] Could not fetch existing keys: {e}")
        existing_keys = set()

    # Pre-filter uses raw url as proxy for entry_url; upsert on dedup_key is the authoritative dedup
    new_results = [
        r for r in raw_results
        if make_dedup_key(r["source"], r.get("title", ""), r.get("url")) not in existing_keys
    ]
    print(f"[INFO] New items after dedup filter: {len(new_results)}")

    # 3. Parse each new item with Claude Haiku
    deals = []
    for item in new_results:
        try:
            parsed = parse_one(item["text"], item["source"], item.get("url"))
            if parsed and parsed.get("is_slc_utah_relevant"):
                parsed["dedup_key"]      = make_dedup_key(
                    parsed["source"], parsed["title"], parsed.get("entry_url")
                )
                parsed["flagged_manual"] = parsed.pop("requires_manual_entry")
                parsed.pop("is_slc_utah_relevant", None)
                # Clamp value_score to valid DB range (1-10)
                parsed["value_score"] = max(1, min(10, int(parsed.get("value_score") or 1)))
                deals.append(parsed)
        except Exception as e:
            print(f"[WARN] Parse failed for {item.get('url')}: {e}")

    print(f"[INFO] Parsed deals to upsert: {len(deals)}")

    # 4. Upsert into Supabase, dedup by dedup_key
    if deals:
        try:
            db.table("deals").upsert(deals, on_conflict="dedup_key").execute()
            print(f"[INFO] Upserted {len(deals)} deals")
        except Exception as e:
            print(f"[ERROR] Upsert failed: {e}")
            raise


if __name__ == "__main__":
    main()
