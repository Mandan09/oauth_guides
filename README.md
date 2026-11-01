# OAuth App Guides

Before a developer can let users connect an app to their AI agent, they usually need their **own OAuth app** registered with the provider and approved for production. That path ranges from 15 minutes (Notion) to weeks plus a paid security audit (Gmail, Google Drive), and it is hard to tell which in advance.

This app answers that question per provider: **how hard is it, how long will it take (your work vs. waiting on the provider), which permissions you need, what an agent can do for you, and where you have to take over**. Every claim is labelled *tested* (confirmed by a live probe), *sourced* (stated on a cited page) or *uncertain*.

**Live:** _add the Render URL here_ · **Test log:** [docs/TESTING.md](docs/TESTING.md)

## What it does

- **Library:** ready guides (Gmail, Google Drive, Slack, Notion, HubSpot, Microsoft Outlook, Asana, Linear, Jira, GitHub, Dropbox, Zoho CRM, Keka), each at a shareable `/g/<slug>` link with PDF, Word, Markdown, HTML and JSON export.
- **Live generation:** type any app name or website, or describe what your agent must do ("read projects, create tasks…"), and agents research it while you watch. The guide is then written into the side panel as you read.
- **Follow-up questions** about the open guide, answered from the guide first and the provider's docs if needed.
- **Asks instead of guessing** when no app is named, and **stops early** when a site has no third-party OAuth (e.g. `example.com`).

## How it works

```
message ─► intake (Gemini, one call): app name · need → recommend services · follow-up · clarify
             │
             ▼
   resolver ─► ┌ review researcher  (approval, verification, timelines)
               ├ OAuth researcher   (registration, scopes, tokens, redirect rules)   ─► writer ─► validator ─► guide
               └ prober             (live checks with a fake client_id, no credentials)
```

- **Google ADK** agents, running in parallel where they can, with a tool budget per agent.
- **Tools:**
  - `search_web`: Gemini Google Search, then Tavily, then DuckDuckGo
  - `fetch_page`: reads a page, blocking internal and private URLs
  - `check_discovery`: looks for the provider's OAuth discovery metadata
  - `probe_authorize`: calls the authorize endpoint with a fake client_id
- **Validator (plain code, no LLM):**
  - Downgrades a claim if its source was never opened.
  - Downgrades a timeline that never appeared in the research.
  - Marks a scope "uncertain" if its exact string was not in the docs.
  - Lists the guide's assumptions.
- **FastAPI streaming:**
  - Server-sent events, numbered so a reconnecting browser resumes in order.
  - The live view streams the agents' short narration, each search with its results, and a progress bar with time left.
  - The guide is drawn while the writer's JSON is still arriving.
- **Postgres:**
  - guides and their versions, runs with their event history, and chats
  - ADK sessions (one per chat, so follow-ups remember earlier turns)
  - token usage from ADK's `usage_metadata`, gathered with a plugin
- **Model fallback:** Gemini, falling back through ADK's `FallbackModel` to OpenRouter and Groq models via LiteLLM, when those keys are set.

## Run locally

```bash
cp .env.example .env        # add GEMINI_API_KEY
docker compose up -d --build
open http://localhost:8000
```

Tests: `uv pip install -e '.[dev]'` then `pytest`.

## Deploy (Render + Neon, free)

1. Create a Postgres database at [neon.tech](https://neon.tech) and copy its connection string.
2. On [render.com](https://render.com): **New → Blueprint**, pick this repo, and fill in `GEMINI_API_KEY` and `DATABASE_URL`. `ADMIN_TOKEN` is generated for you.
3. Optional: in GitHub, set the repository variable `APP_URL` to the Render URL. The `keep-alive` workflow then pings it every 10 minutes, so the free instance doesn't sleep.

The library loads from `seed/` on first start. To refresh it from a local database, run `scripts/export_seed.py` (the command is in the file).

## Key decisions

- **Scope:** only getting *your own* OAuth app ready for production. That's where the uncertainty and the waiting are; API usage docs are out of scope.
- **Evidence over confidence:**
  - Probes run without accounts or credentials.
  - Labels are enforced in code, not left to the model.
  - Unconfirmed scopes and estimated times are marked as such.
- **Effort and waiting shown separately:** hands-on time, approval wait, first test connection and production readiness are distinct fields.
- **Agent vs. you:** every step is owned by *agent*, *you* or *provider*.
- **Cost control:**
  - A small tool budget per agent.
  - Library hits cost no research.
  - Short inputs skip the intake call.
  - Rate limits: 5 new guides per IP per hour, 50 per day.

## Limitations

- **Not verified with real accounts.** Guides come from public docs plus credential-free probes; no provider approval was actually attempted.
- **Older guides:** guides made before the stricter evidence rules keep their old labels until regenerated.
- **Speed:** a new guide takes about 2–3 minutes and about 50–65k tokens.
- **Interrupted runs:** a restart interrupts research in progress, and the run is marked failed. Follow-up answers stop if the browser leaves mid-answer.
- **No accounts:** chats are tied to an anonymous browser id, not a login.
