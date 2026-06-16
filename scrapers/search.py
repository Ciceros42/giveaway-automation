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

TAVILY_URL = "https://api.tavily.com/search"


class SearchScraper(BaseScraper):
    def scrape(self) -> list[dict]:
        results = []
        for query in QUERIES:
            try:
                resp = requests.post(
                    TAVILY_URL,
                    json={
                        "api_key": config.TAVILY_API_KEY,
                        "query": query,
                        "max_results": 10,
                        "search_depth": "basic",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", []):
                    results.append({
                        "source": "search",
                        "title":  item.get("title", ""),
                        "text":   item.get("content", "") + "\n" + item.get("title", ""),
                        "url":    item.get("url", ""),
                    })
            except Exception as e:
                print(f"[WARN] Tavily search failed for '{query}': {e}")
        return results
