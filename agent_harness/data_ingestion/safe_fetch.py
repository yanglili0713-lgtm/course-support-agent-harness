from __future__ import annotations

import time
import urllib.parse
import urllib.request
from pathlib import Path


ALLOWED_HOSTS = {"huggingface.co", "raw.githubusercontent.com"}


def assert_safe_public_url(url: str) -> urllib.parse.ParseResult:
    """Validate a public URL before downloading.

    This fetcher does not log in, bypass auth, crawl arbitrary links, or accept
    credential-bearing URLs. It is intentionally small and allow-list based.
    """

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS public URLs are allowed.")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Host is not allow-listed: {parsed.hostname}")
    if "@" in parsed.netloc:
        raise ValueError("Credential-bearing URLs are not allowed.")
    return parsed


def download_public_file(url: str, output_path: Path, *, max_bytes: int = 20_000_000, delay_seconds: float = 1.0) -> Path:
    """Download one allow-listed public file with a size cap and polite delay."""

    assert_safe_public_url(url)
    time.sleep(delay_seconds)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "agent-harness-safe-ingestion/0.1"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"Downloaded file exceeds max_bytes={max_bytes}.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return output_path

