NARRATE = """Think out loud briefly, for the developer watching: before each batch of tool calls write ONE short
sentence on what you are checking; after results, ONE short sentence judging what you found and what is still
missing. Plain sentences, no lists, no headings."""

BUDGET_NOTE = NARRATE + """
Be economical: you have a small tool budget. Make independent searches/fetches in the same turn (parallel
calls). Prefer official docs; do not re-read pages. Stop as soon as you can answer."""

RESOLVER = """Identify which app a developer means so others can research its OAuth setup.
Developer input: "{query}"

One or two searches at most. """ + NARRATE + """
Then reply with short plain-text lines:
App, Provider, Website, Developer portal, OAuth docs, Auth host, Supports OAuth, Notes.
Write "Supports OAuth: yes", "Supports OAuth: no" (e.g. API keys only, no public API, placeholder
site) or "Supports OAuth: unknown". In Notes, say which auth method it does use, if any.
Write "unknown" for anything you could not confirm. Do not guess URLs."""

REVIEW_RESEARCHER = """Research what a developer must do before ARBITRARY external users can connect their own
OAuth app for this provider (e.g. an AI agent product connecting customers' accounts).

App profile:
{app_profile}

Cover: what works immediately (test users, own workspace/tenant, dev-mode limits); mandatory vs optional review,
verification, security assessment, marketplace listing, partner programs, admin consent, paid plans; stated
timelines and costs; requirements (verified domain, privacy policy, demo video, business verification, scope
justification); common rejection reasons (mark anecdotal).
""" + BUDGET_NOTE + """
Output concise bullets. End EVERY bullet with the exact source URL in brackets. Flag conflicting or dated info."""

OAUTH_RESEARCHER = """Research the technical OAuth details for this provider.

App profile:
{app_profile}

Developer's use case: {use_case}

Cover: how to register the client and where; authorize/token URLs; PKCE; refresh token behaviour and expiry;
redirect URI rules; the exact scopes needed for each action in the use case, and which scopes are
sensitive/restricted or need admin consent or a paid plan; rate limits that affect connections.
""" + BUDGET_NOTE + """
Output concise bullets. End EVERY bullet with the exact source URL in brackets."""

PROBER = """Test this provider's OAuth setup live, without any account or credentials.

App profile:
{app_profile}

1. check_discovery on the auth host.
2. probe_authorize the authorize endpoint (from discovery, the profile, or the docs).
3. fetch_page the developer portal to confirm it exists.
Do these in as few turns as possible. """ + NARRATE + """
Finally report each check as one line: what you checked, what happened, what it
shows. Report failures honestly; do not speculate."""

WRITER = """Write a practical OAuth app setup and approval guide for developers building AI agents.

Approval and review research:
{review_notes}

Technical OAuth research:
{oauth_notes}

Live probe results:
{probe_notes}

App profile:
{app_profile}

Developer's use case: {use_case}

Rules:
- Use only facts from the notes and probes. Build `sources` from the URLs in the notes (ids s1, s2, ...) and cite them.
- status "tested" ONLY for facts confirmed by the probe results. "sourced" ONLY when a cited page states the
  fact itself (not just the topic). Everything else is "uncertain": your own estimates, forum or blog anecdotes,
  conflicting sources, timelines the provider does not publish, and anything you combined from several pages.
  Being honest here matters more than looking confident. Put unresolved questions in open_questions.
- assumptions: list every estimate or inference the guide relies on, e.g. "Hands-on time is our estimate, not
  published by the provider" or "Review time is based on developer reports, not an official SLA".
- difficulty: easy = self-serve, no mandatory review for production; moderate = light mandatory review,
  verification or admin consent, days to ~2 weeks; hard = mandatory review/security assessment/business
  verification, weeks or longer; gated = access depends on partner approval or a paid/enterprise tier and may be refused.
- Time fields are ranges. Separate hands-on work from waiting on the provider. Hands-on time is always an
  estimate; approval waits are estimates unless the provider publishes them, so name them in assumptions.
- Stages go in order from creating the app to production approval. Each step has an owner:
  agent = something an AI agent can do for the developer (research, drafting justification text, privacy policy
  drafts, config, testing endpoints); you = needs the developer (accounts, legal acceptance, payments, domain
  verification, submitting reviews); provider = waiting on the provider.
- permissions: map each action in the use case to exact scope strings copied from the notes, and say whether they
  trigger extra review, admin consent or a paid plan. Never invent or paraphrase a scope string; if the notes
  have none for an action, give your best guess and say so in review_impact.
- agent_can / you_must summarise that split. blockers say what to do when stuck, concretely.
- Be specific and brief. No marketing language."""
