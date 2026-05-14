"""Async base scraper with retry, rate-limiting, and structured logging."""
import asyncio
import time
import json
from pathlib import Path
from typing import Optional, Any

import httpx
from loguru import logger
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type
)

from scrapers.config import ScraperConfig, DATA_RAW


class ScrapingError(Exception):
    """Raised when a scrape fails after all retries."""


class BaseScraper:
    """Base class for all data source scrapers."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self.raw_dir = DATA_RAW / config.name
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            self.raw_dir / "scraper.log",
            rotation="10 MB",
            retention="7 days",
            level="INFO",
        )

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
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[dict] = None,
        expect_json: bool = True,
    ) -> Any:
        """Fetch with automatic retry on network errors."""
        try:
            return await self._fetch(client, url, params, expect_json)
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            raise ScrapingError(f"Failed to fetch {url}: {e}") from e

    def save_raw(self, filename: str, data: Any):
        """Save raw scraped data to disk."""
        path = self.raw_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, (list, dict)):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(data))
        logger.info(f"Saved raw data: {path}")
        return path

    def load_raw(self, filename: str) -> Any:
        """Load previously saved raw data."""
        path = self.raw_dir / filename
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def run(self) -> dict:
        """Override in subclasses. Returns summary dict."""
        raise NotImplementedError
