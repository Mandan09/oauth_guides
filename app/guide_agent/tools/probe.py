from urllib.parse import urlencode, urlparse

import httpx
from google.adk.tools import ToolContext

from app.guide_agent.tools.fetch import BlockedURL, client, remember

FAKE_CLIENT = "oauth-guide-probe-invalid-client"
ERROR_HINTS = ("invalid_client", "client_id", "unauthorized_client", "invalid_request", "app not found", "application", "redirect_uri")


def _log(tool_context: ToolContext, check: str, request: str, result: str) -> None:
    remember(tool_context, "probe_log", [{"check": check, "request": request, "result": result}])
    remember(tool_context, "seen_urls", [request.split()[1]])  # a probed URL counts as opened for citations


async def check_discovery(base_url: str, tool_context: ToolContext) -> dict:
    """Look for OAuth/OIDC discovery metadata (endpoints, PKCE support, dynamic client registration).

    Args:
        base_url: Issuer or auth host, e.g. https://accounts.google.com
    """
    root = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
    found = {}
    async with client(follow_redirects=True) as http:
        for path in ("/.well-known/openid-configuration", "/.well-known/oauth-authorization-server"):
            url = root + path
            try:
                resp = await http.get(url)
                data = resp.json() if resp.status_code == 200 else None
            except (BlockedURL, httpx.HTTPError, ValueError) as e:
                _log(tool_context, "discovery", f"GET {url}", f"failed: {str(e)[:120]}")
                continue
            if not isinstance(data, dict):
                _log(tool_context, "discovery", f"GET {url}", f"HTTP {resp.status_code}, no metadata")
                continue
            keys = ("authorization_endpoint", "token_endpoint", "registration_endpoint",
                    "code_challenge_methods_supported", "grant_types_supported", "scopes_supported")
            found = {k: data[k] for k in keys if k in data}
            if "scopes_supported" in found:
                found["scopes_supported"] = found["scopes_supported"][:25]
            _log(tool_context, "discovery", f"GET {url}",
                 f"HTTP 200; PKCE {found.get('code_challenge_methods_supported', 'not listed')}; "
                 f"dynamic registration {'yes' if 'registration_endpoint' in found else 'not listed'}")
            break
    return found or {"result": "no discovery metadata published"}


async def probe_authorize(authorize_url: str, tool_context: ToolContext) -> dict:
    """Call an authorize endpoint with a fake client_id to confirm it is live and see how it rejects unknown apps.
    Never sends real credentials.

    Args:
        authorize_url: The provider's OAuth authorize endpoint.
    """
    params = {"client_id": FAKE_CLIENT, "response_type": "code",
              "redirect_uri": "https://example.com/callback", "state": "probe"}
    url = f"{authorize_url}{'&' if '?' in authorize_url else '?'}{urlencode(params)}"
    try:
        async with client(follow_redirects=True) as http:
            resp = await http.get(url)
    except (BlockedURL, httpx.HTTPError) as e:
        _log(tool_context, "authorize", f"GET {authorize_url}", f"failed: {str(e)[:120]}")
        return {"error": str(e)[:300]}
    body = resp.text.lower()
    hints = [h for h in ERROR_HINTS if h in body or h in str(resp.url).lower()]
    result = f"HTTP {resp.status_code}, landed on {urlparse(str(resp.url)).netloc}; error hints: {hints or 'none'}"
    _log(tool_context, "authorize", f"GET {authorize_url} (fake client_id)", result)
    return {"status": resp.status_code, "final_url": str(resp.url)[:300], "error_hints": hints, "snippet": body[:800]}
