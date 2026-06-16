import requests
from scrapers.base import BaseScraper

URLS = [
    "https://www.ksl.com/deals",
    "https://www.ksl.com/contest",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; slc-deal-bot/1.0)"}


class KSLScraper(BaseScraper):
    def scrape(self) -> list[dict]:
        results = []
        for url in URLS:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                results.append({
                    "source": "ksl",
                    "title":  url,
                    "text":   resp.text,
                    "url":    url,
                })
            except Exception as e:
                print(f"[WARN] KSL scrape failed for {url}: {e}")
        return results
