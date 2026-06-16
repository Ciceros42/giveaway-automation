import requests
import config
from scrapers.base import BaseScraper

SOCIAL_SEARCH_TERMS = [
    "site:facebook.com salt lake giveaway",
    "site:instagram.com salt lake city giveaway",
]

TAVILY_URL = "https://api.tavily.com/search"


class SocialScraper(BaseScraper):
    def scrape(self) -> list[dict]:
        results = []

        # Step 1: find social page URLs via Tavily
        social_urls = []
        for query in SOCIAL_SEARCH_TERMS:
            try:
                resp = requests.post(
                    TAVILY_URL,
                    json={
                        "api_key": config.TAVILY_API_KEY,
                        "query": query,
                        "max_results": 5,
                        "search_depth": "basic",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                for item in resp.json().get("results", []):
                    u = item.get("url", "")
                    if ("facebook.com" in u or "instagram.com" in u) and u not in social_urls:
                        social_urls.append(u)
            except Exception as e:
                print(f"[WARN] Social search failed for '{query}': {e}")

        # Step 2: fetch public pages (no auth, public only)
        page_headers = {"User-Agent": "Mozilla/5.0 (compatible; slc-deal-bot/1.0)"}
        for url in social_urls[:10]:
            try:
                resp = requests.get(url, headers=page_headers, timeout=15, allow_redirects=True)
                if resp.status_code == 200:
                    results.append({
                        "source": "social",
                        "title":  url,
                        "text":   resp.text,
                        "url":    url,
                    })
            except Exception as e:
                print(f"[WARN] Social page fetch failed for {url}: {e}")
        return results
