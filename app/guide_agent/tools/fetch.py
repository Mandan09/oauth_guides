import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from google.adk.tools import ToolContext

MAX_CHARS = 8_000
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OAuthGuideBot/1.0)"}


class BlockedURL(Exception):
    pass


async def check_public(url: str) -> None:
    """Reject non-http(s) URLs and hosts resolving to private or internal addresses (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise BlockedURL(f"unsupported url: {url}")
    infos = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise BlockedURL(f"blocked non-public host: {parsed.hostname}")


async def _guard(request: httpx.Request) -> None:
    await check_public(str(request.url))


def client(**kwargs) -> httpx.AsyncClient:
    """HTTP client that re-checks every redirect hop against the SSRF guard."""
    return httpx.AsyncClient(headers=HEADERS, timeout=15, event_hooks={"request": [_guard]}, **kwargs)


def remember(tool_context: ToolContext | None, key: str, items: list) -> None:
    if tool_context is not None:
        tool_context.state[key] = tool_context.state.get(key, []) + items


async def fetch_page(url: str, tool_context: ToolContext) -> dict:
    """Fetch a public web page and return its readable text (truncated).

    Args:
        url: Full http(s) URL of the page to read.
    """
    try:
        async with client(follow_redirects=True) as http:
            resp = await http.get(url)
    except (BlockedURL, httpx.HTTPError, OSError) as e:
        return {"url": url, "error": str(e)[:300]}
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "svg"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    remember(tool_context, "seen_urls", [url, str(resp.url)])
    return {
        "url": str(resp.url),
        "status": resp.status_code,
        "title": soup.title.string.strip() if soup.title and soup.title.string else "",
        "text": text[:MAX_CHARS],
    }
