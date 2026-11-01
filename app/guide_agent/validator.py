"""Evidence checks done in code, so the model cannot mark its own homework."""

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.guides.schemas import Guide, GuideDraft


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80]


def norm_url(url: str) -> str:
    p = urlparse(url.strip())
    host = (p.netloc or "").lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/').removesuffix('.md')}"  # docs sites often serve .md copies


class NotIdentified(Exception):
    pass


DURATION = re.compile(r"(\d+(?:\s*(?:-|–|to)\s*\d+)?)\s*(?:business\s+)?(hour|day|week|month)s?", re.I)


def _durations(text: str) -> set[str]:
    return {f"{m.group(1).replace(' ', '')} {m.group(2).lower()}" for m in DURATION.finditer(text)}


def finalize(draft: GuideDraft, state: dict, models: list[str]) -> Guide:
    if "unknown" in f"{draft.app} {draft.website}".lower() or not draft.website.startswith("http"):
        raise NotIdentified("Could not identify a specific app. Try its name or website.")
    seen = {norm_url(u) for u in state.get("seen_urls", [])}
    probes = state.get("probe_log", [])
    warnings: list[str] = []

    unverified = {s.id for s in draft.sources if norm_url(s.url) not in seen}
    for s in draft.sources:
        if s.id in unverified:
            warnings.append(f"Source {s.id} was cited but not opened or returned by search in this run: {s.url}")

    known = {s.id for s in draft.sources}
    research = " ".join(str(state.get(k, "")) for k in ("review_notes", "oauth_notes", "probe_notes"))
    for claim in [*draft.requirements, *draft.gotchas, *draft.key_claims]:
        backed = [i for i in claim.source_ids if i in known and i not in unverified]
        if claim.status == "tested" and not probes:
            claim.status = "sourced" if backed else "uncertain"
            warnings.append(f"Downgraded 'tested' (no probes ran): {claim.text[:80]}")
        elif claim.status == "sourced" and not backed:
            claim.status = "uncertain"
            warnings.append(f"Downgraded to uncertain (no verified source): {claim.text[:80]}")
        elif claim.status == "sourced" and _durations(claim.text) - _durations(research):
            claim.status = "uncertain"  # a timeline the researchers never saw is the writer's estimate
            warnings.append(f"Downgraded to uncertain (timeline not in research): {claim.text[:80]}")

    for perm in draft.permissions:
        missing = [scope for scope in perm.scopes if scope not in research]
        backed = [i for i in perm.source_ids if i in known and i not in unverified]
        perm.status = "sourced" if perm.scopes and not missing and backed else "uncertain"
        if missing:
            warnings.append(f"Scope not found in research, check before use: {', '.join(missing)}")

    if not draft.assumptions:
        draft.assumptions = ["Hands-on time is an estimate; providers do not publish it."]

    if draft.difficulty == "easy" and any(stage.blocking for stage in draft.stages):
        warnings.append("Rated easy but has a blocking provider stage; check the difficulty.")

    return Guide(
        **draft.model_dump(),
        slug=slugify(draft.app),
        probes=probes,
        warnings=warnings,
        models=models,
        search_providers=sorted(set(state.get("search_providers", []))),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
