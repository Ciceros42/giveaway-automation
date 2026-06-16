import requests
import config
from scrapers.base import BaseScraper

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

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class SearchScraper(BaseScraper):
    def scrape(self) -> list[dict]:
        results = []
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": config.BRAVE_API_KEY,
        }
        for query in QUERIES:
            try:
                resp = requests.get(
                    BRAVE_SEARCH_URL,
                    headers=headers,
                    params={"q": query, "count": 10},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "source": "search",
                        "title":  item.get("title", ""),
                        "text":   item.get("description", "") + "\n" + item.get("title", ""),
                        "url":    item.get("url", ""),
                    })
            except Exception as e:
                print(f"[WARN] Brave search failed for '{query}': {e}")
        return results
