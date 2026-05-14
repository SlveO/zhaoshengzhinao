"""Async base scraper with retry, rate-limiting, and structured logging."""
import asyncio
import json
import time
from typing import Any, Optional

import httpx
from loguru import logger
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception
)

from scrapers.config import DATA_RAW, ScraperConfig


class ScrapingError(Exception):
    """Raised when a scrape fails after all retries."""


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on transient errors: timeouts, transport issues, 429, 5xx."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    if isinstance(exc, httpx.TransportError):
        return True
    return False


# Module-level log handler — one handler total, not one per instance
_log_handler_id: int | None = None


def _ensure_log_handler(log_path: str):
    global _log_handler_id
    if _log_handler_id is None:
        _log_handler_id = logger.add(
            log_path,
            rotation="10 MB",
            retention="7 days",
            level="INFO",
        )


class BaseScraper:
    """Base class for all data source scrapers."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self.raw_dir = DATA_RAW / config.name
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        _ensure_log_handler(str(self.raw_dir / "scraper.log"))

    async def _rate_limit(self):
        """Ensure minimum delay between requests."""
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self.config.delay_seconds:
                await asyncio.sleep(self.config.delay_seconds - elapsed)
            self._last_request_time = time.monotonic()

    async def _fetch(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[dict] = None,
        expect_json: bool = True,
    ) -> Any:
        """Fetch URL with rate limiting and error handling."""
        await self._rate_limit()
        headers = {**self.config.headers, "User-Agent": self.config.user_agent}
        resp = await client.get(
            url, params=params, headers=headers,
            timeout=self.config.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json() if expect_json else resp.text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception(_is_retryable),
    )
    async def fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[dict] = None,
        expect_json: bool = True,
    ) -> Any:
        """Fetch with automatic retry on transient network errors."""
        try:
            return await self._fetch(client, url, params, expect_json)
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            raise ScrapingError(f"Failed to fetch {url}: {e}") from e

    def save_raw(self, filename: str, data: Any):
        """Save raw scraped data as JSON. Wraps non-dict data in a dict."""
        path = self.raw_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, (list, dict)):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump({"_type": "text", "content": str(data)}, f,
                          ensure_ascii=False, indent=2)
        logger.info(f"Saved raw data: {path}")
        return path

    def load_raw(self, filename: str) -> Any:
        """Load previously saved raw data. Always returns JSON."""
        path = self.raw_dir / filename
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def close(self):
        """Clean up resources. Subclasses should call super().close()."""
        pass

    async def run(self) -> dict:
        """Override in subclasses. Returns summary dict."""
        raise NotImplementedError
