import asyncio
import logging

from ddgs import DDGS
from google.adk.tools import ToolContext
from google.genai import types

from app.config import settings
from app.guide_agent.llm import gemini
from app.guide_agent.tools.fetch import client, remember
from app.guide_agent.usage import add_usage

log = logging.getLogger(__name__)


async def _resolve(url: str) -> str:
    """Gemini grounding links are redirects; follow one hop to get the real URL."""
    try:
        async with client() as http:
            resp = await http.get(url)
        return resp.headers.get("location", url)
    except Exception:
        return url


async def _gemini(query: str, tool_context: ToolContext) -> dict:
    resp = await gemini().aio.models.generate_content(
        model=settings.search_model,
        contents=f"Search the web for: {query}. Summarise the key official facts in under 120 words.",
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
    )
    add_usage(tool_context.state, "search_tool", resp.usage_metadata)  # the grounding call costs tokens too
    meta = resp.candidates[0].grounding_metadata if resp.candidates else None
    chunks = [c.web for c in (meta.grounding_chunks or []) if c.web] if meta else []
    urls = await asyncio.gather(*[_resolve(c.uri) for c in chunks[:6]])
    results = [{"title": c.title, "url": u} for c, u in zip(chunks, urls)]
    return {"summary": resp.text or "", "results": results}


async def _tavily(query: str, _) -> dict:
    async with client() as http:
        resp = await http.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            json={"query": query, "max_results": 6},
        )
    resp.raise_for_status()
    results = [{"title": r["title"], "url": r["url"], "snippet": r.get("content", "")[:400]} for r in resp.json()["results"]]
    return {"summary": "", "results": results}


async def _ddg(query: str, _) -> dict:
    hits = await asyncio.to_thread(lambda: DDGS().text(query, max_results=6))
    return {"summary": "", "results": [{"title": h["title"], "url": h["href"], "snippet": h["body"]} for h in hits]}


async def search_web(query: str, tool_context: ToolContext) -> dict:
    """Search the web. Returns a short summary (when available) and result titles and URLs.

    Args:
        query: What to search for, e.g. "Slack app directory review requirements".
    """
    providers = [("gemini", _gemini), ("tavily", _tavily), ("duckduckgo", _ddg)]
    for name, fn in providers:
        if name == "gemini" and not settings.gemini_api_key or name == "tavily" and not settings.tavily_api_key:
            continue
        try:
            out = await fn(query, tool_context)
        except Exception as e:  # any provider failure moves on to the next one
            log.warning("search provider %s failed: %s", name, e)
            continue
        remember(tool_context, "seen_urls", [r["url"] for r in out["results"]])
        remember(tool_context, "search_providers", [name])
        return {"provider": name, **out}
    return {"error": "all search providers failed"}
