"""Fetch full publication text, respecting robots.txt and rate limits"""

import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def build_client(user_agent: str, timeout_seconds: float) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": user_agent}, timeout=timeout_seconds, follow_redirects=True)


class RateLimiter:
    """minimum delay between requests to the same domain"""

    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds
        self._last_request_at: dict[str, float] = {}

    def wait(self, domain: str) -> None:
        last = self._last_request_at.get(domain)
        if last is not None:
            remaining = self.delay_seconds - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at[domain] = time.monotonic()


class RobotsCache:
    """caches one robots.txt parser per domain for the lifetime of a run"""

    def __init__(self, client: httpx.Client, user_agent: str):
        self.client = client
        self.user_agent = user_agent
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc
        parser = self._parsers.get(domain)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            try:
                resp = self.client.get(robots_url)
                parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
            except httpx.HTTPError:
                parser.parse([])
            self._parsers[domain] = parser
        return parser.can_fetch(self.user_agent, url)


def extract_text(html: str) -> str:
    """extract readable article text from a page"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    container = soup.find("main") or soup.find("article") or soup.body or soup
    return container.get_text(separator="\n", strip=True)


def fetch_full_text(
    client: httpx.Client,
    url: str,
    robots: RobotsCache,
    rate_limiter: RateLimiter,
) -> str | None:
    """Fetch and extract the full text of a publication page
    """
    if not robots.can_fetch(url):
        logger.warning("Skipping %s: disallowed by robots.txt", url)
        return None

    rate_limiter.wait(urlparse(url).netloc)

    try:
        resp = client.get(url)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None

    return extract_text(resp.text)
