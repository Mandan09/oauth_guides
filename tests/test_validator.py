from app.guide_agent.validator import finalize
from app.guides.schemas import Claim, GuideDraft, OAuthFacts, Permission, Source

STATE = {
    "seen_urls": ["https://docs.example.dev/oauth"],
    "oauth_notes": "Scopes: tasks:read, tasks:write. Review takes up to 10 business days [https://docs.example.dev/oauth]",
    "probe_log": [],
}


def draft(**over) -> GuideDraft:
    base = dict(
        app="Example", provider="Example Inc", website="https://example.dev", category="Tasks", difficulty="easy",
        headline="h", summary="s", hands_on_time="1 hour", approval_wait="none", time_to_first_connection="now",
        time_to_production="now", oauth=OAuthFacts(), stages=[], requirements=[], gotchas=[], blockers=[],
        agent_can=[], you_must=[], key_claims=[], open_questions=[],
        sources=[Source(id="s1", title="OAuth", url="https://docs.example.dev/oauth"),
                 Source(id="s2", title="Blog", url="https://blog.example.dev/post")],
    )
    return GuideDraft(**{**base, **over})


def test_claim_citing_unopened_source_becomes_uncertain():
    g = finalize(draft(key_claims=[Claim(text="x", status="sourced", source_ids=["s2"])]), STATE, [])
    assert g.key_claims[0].status == "uncertain"


def test_timeline_not_in_research_becomes_uncertain():
    claims = [Claim(text="Review takes 10 business days", status="sourced", source_ids=["s1"]),
              Claim(text="Review takes 3 weeks", status="sourced", source_ids=["s1"])]
    g = finalize(draft(key_claims=claims), STATE, [])
    assert [c.status for c in g.key_claims] == ["sourced", "uncertain"]


def test_scope_status_checked_against_research():
    perms = [Permission(action="read", scopes=["tasks:read"], review_impact="none", source_ids=["s1"]),
             Permission(action="admin", scopes=["admin:all"], review_impact="none", source_ids=["s1"])]
    g = finalize(draft(permissions=perms), STATE, [])
    assert [p.status for p in g.permissions] == ["sourced", "uncertain"]
    assert any("admin:all" in w for w in g.warnings)


def test_tested_without_probes_is_downgraded():
    g = finalize(draft(key_claims=[Claim(text="endpoint live", status="tested", source_ids=["s1"])]), STATE, [])
    assert g.key_claims[0].status == "sourced"
