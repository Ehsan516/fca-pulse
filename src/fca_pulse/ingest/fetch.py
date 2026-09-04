import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def build_client(user_agent, timeout_seconds):
    return httpx.Client(headers={"User-Agent": user_agent}, timeout=timeout_seconds, follow_redirects=True)


class RateLimiter:
    """makes sure we don't hammer the same domain too fast"""

    def __init__(self, delay_seconds):
        self.delay_seconds = delay_seconds
        self._last_request_at = {}

    def wait(self, domain):
        last = self._last_request_at.get(domain)
        if last is not None:
            elapsed = time.monotonic() - last
            remaining = self.delay_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at[domain] = time.monotonic()


class RobotsCache:
    def __init__(self, client, user_agent):
        self.client = client
        self.user_agent = user_agent
        self._parsers = {}

    def can_fetch(self, url):
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain in self._parsers:
            parser = self._parsers[domain]
        else:
            parser = urllib.robotparser.RobotFileParser()
            robots_url = parsed.scheme + "://" + domain + "/robots.txt"
            try:
                resp = self.client.get(robots_url)
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                else:
                    parser.parse([])
            except httpx.HTTPError:
                parser.parse([])
            self._parsers[domain] = parser
        return parser.can_fetch(self.user_agent, url)


def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    container = soup.find("main") or soup.find("article") or soup.body or soup
    text = container.get_text(separator="\n", strip=True)
    return text


def fetch_full_text(client, url, robots, rate_limiter):
    if not robots.can_fetch(url):
        logger.warning("Skipping %s: disallowed by robots.txt", url)
        return None

    domain = urlparse(url).netloc
    rate_limiter.wait(domain)

    try:
        resp = client.get(url)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None

    return extract_text(resp.text)
