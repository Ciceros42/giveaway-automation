import requests
from scrapers.base import BaseScraper

SUBREDDITS = ["SaltLakeCity", "Utah"]
HEADERS = {"User-Agent": "script:slc-deal-bot:v1.0 (automated scraper)"}


class RedditScraper(BaseScraper):
    def scrape(self) -> list[dict]:
        results = []
        for sub in SUBREDDITS:
            for sort in ["new", "hot"]:
                try:
                    url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit=25"
                    resp = requests.get(url, headers=HEADERS, timeout=10)
                    resp.raise_for_status()
                    posts = resp.json().get("data", {}).get("children", [])
                    for post in posts:
                        d = post.get("data", {})
                        title = d.get("title", "")
                        body  = d.get("selftext", "")
                        link  = d.get("url", "")
                        results.append({
                            "source": f"reddit/{sub}",
                            "title":  title,
                            "text":   f"{title}\n{body}",
                            "url":    f"https://www.reddit.com{d.get('permalink', '')}",
                        })
                except Exception as e:
                    print(f"[WARN] Reddit scrape failed for r/{sub}/{sort}: {e}")
        return results
