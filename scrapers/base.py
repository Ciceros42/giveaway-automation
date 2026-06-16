from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """Each scraper returns a list of dicts: {source, title, text, url}"""

    @abstractmethod
    def scrape(self) -> list[dict]:
        ...
