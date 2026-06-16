import requests
from scrapers.base import BaseScraper

STATIC_SITES = [
    {"source": "radio",      "url": "https://x96.com/contests"},
    {"source": "radio",      "url": "https://www.mix1051.com/contests"},
    {"source": "radio",      "url": "https://www.kubl.com/contests"},
    {"source": "restaurant", "url": "https://www.swignsweets.com"},
    {"source": "restaurant", "url": "https://www.costavida.com/promotions"},
    {"source": "restaurant", "url": "https://www.redrobin.com/offers"},
    # Excluded: hits1015.com (DNS dead), jcwsburgers.com (DNS dead),
    #           cubbysslc.com (DNS dead), Chick-fil-A (app-gated), Groupon (bot detection)
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; slc-deal-bot/1.0)"}


class StaticSitesScraper(BaseScraper):
    def scrape(self) -> list[dict]:
        results = []
        for site in STATIC_SITES:
            try:
                resp = requests.get(site["url"], headers=HEADERS, timeout=15)
                resp.raise_for_status()
                results.append({
                    "source": site["source"],
                    "title":  site["url"],
                    "text":   resp.text,
                    "url":    site["url"],
                })
            except Exception as e:
                print(f"[WARN] Static scrape failed for {site['url']}: {e}")
        return results
