from typing import Literal

from pydantic import BaseModel, Field

Owner = Literal["agent", "you", "provider"]
Status = Literal["tested", "sourced", "uncertain"]


class Source(BaseModel):
    id: str = Field(description="Short id like s1, s2")
    title: str
    url: str


class Claim(BaseModel):
    text: str
    status: Status = Field(description="tested = confirmed by a probe; sourced = stated in a cited source; uncertain = inferred or unconfirmed")
    source_ids: list[str] = []


class Step(BaseModel):
    title: str
    detail: str
    owner: Owner
    duration: str = ""
    source_ids: list[str] = []


class Stage(BaseModel):
    name: str
    duration: str
    blocking: bool = Field(description="True if work stops until this stage completes, e.g. waiting on provider review")
    steps: list[Step]


class Blocker(BaseModel):
    issue: str
    how_to_proceed: str


class Permission(BaseModel):
    action: str = Field(description="What the agent needs to do, e.g. create tasks")
    scopes: list[str]
    review_impact: str = Field(description="Whether these scopes trigger extra review, admin consent or a paid plan")
    source_ids: list[str] = []
    status: Status = Field("uncertain", description="Set by the validator: sourced only if every scope string appears in the research")


class OAuthFacts(BaseModel):
    developer_portal: str = ""
    docs_url: str = ""
    authorize_url: str = ""
    token_url: str = ""
    pkce: str = ""
    refresh_tokens: str = ""
    redirect_uri_rules: str = ""
    scopes: str = ""


class GuideDraft(BaseModel):
    """What the writer agent produces."""

    app: str
    provider: str
    website: str
    category: str
    difficulty: Literal["easy", "moderate", "hard", "gated"]
    headline: str = Field(description="One sentence verdict a developer can act on")
    summary: str
    hands_on_time: str
    approval_wait: str
    time_to_first_connection: str
    time_to_production: str
    oauth: OAuthFacts
    stages: list[Stage]
    requirements: list[Claim]
    gotchas: list[Claim]
    permissions: list[Permission] = Field([], description="Agent actions mapped to exact scopes")
    blockers: list[Blocker]
    agent_can: list[str]
    you_must: list[str]
    key_claims: list[Claim]
    open_questions: list[str]
    assumptions: list[str] = Field([], description="Estimates and inferences the guide relies on")
    sources: list[Source]


class Probe(BaseModel):
    check: str
    request: str
    result: str


class Guide(GuideDraft):
    """Draft plus fields filled by code, never by the model."""

    slug: str
    probes: list[Probe] = []
    warnings: list[str] = []
    origin: Literal["seed", "live"] = "live"
    models: list[str] = []
    search_providers: list[str] = []
    generated_at: str = ""
    verified_note: str = ""
