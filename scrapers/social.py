import requests
from scrapers.base import BaseScraper

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; slc-deal-bot/1.0)"}

SOCIAL_SEARCH_TERMS = [
    "site:facebook.com salt lake giveaway",
    "site:instagram.com salt lake city giveaway",
]

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class SocialScraper(BaseScraper):
    def __init__(self):
        import config
        self._api_key = config.BRAVE_API_KEY

    def scrape(self) -> list[dict]:
        results = []
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        # Step 1: find social page URLs via search
        social_urls = []
        for query in SOCIAL_SEARCH_TERMS:
            try:
                resp = requests.get(
                    BRAVE_SEARCH_URL,
                    headers=headers,
                    params={"q": query, "count": 5},
                    timeout=10,
                )
                resp.raise_for_status()
                for item in resp.json().get("web", {}).get("results", []):
                    u = item.get("url", "")
                    if ("facebook.com" in u or "instagram.com" in u) and u not in social_urls:
                        social_urls.append(u)
            except Exception as e:
                print(f"[WARN] Social search failed for '{query}': {e}")

        # Step 2: fetch public pages (no auth, public only)
        page_headers = {"User-Agent": "Mozilla/5.0 (compatible; slc-deal-bot/1.0)"}
        for url in social_urls[:10]:  # cap to avoid excessive requests
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
