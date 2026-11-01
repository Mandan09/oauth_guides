# OAuth App Guides

If you're building an AI agent that connects to your users' Gmail, Slack or HubSpot, you'll eventually need your own OAuth app with that provider, and it has to be approved before real users can connect. For some providers that takes fifteen minutes. For others it takes weeks and a paid security audit. Usually you only find out which once you're halfway through.

I built this to answer that up front. Look up an app, or describe what your agent needs to do, and you get a guide that tells you:

- how hard it is, and how long it takes: your own work and the time spent waiting on the provider, shown separately
- the exact permissions (scopes) your agent needs, and whether any of them trigger a review
- the steps in order, each marked as something an agent can do for you, something you have to do, or a wait on the provider
- what to do when you get stuck
- where every claim comes from, marked as tested live, sourced from the docs, or uncertain

**Try it:** https://oauth-guides.onrender.com
(It runs on Render's free tier, so if nobody has used it for a while, the first page load can take about a minute.)

## Using it

- **Pick a guide from the library.** There are 13 ready to go: Gmail, Google Drive, Slack, Notion, HubSpot, Microsoft Outlook, Asana, Linear, Jira, GitHub, Dropbox, Zoho CRM and Keka.
- **Type any app name or website.** If it isn't in the library, the agent researches it while you watch. The guide writes itself into the side panel, usually in two to three minutes.
- **Describe what you need instead**, e.g. *"my agent needs to read projects, create tasks and assign people"*. It recommends a few services that fit and starts on the best one.
- **Ask follow-up questions** about the open guide, e.g. *"which scopes do I need for webhooks?"*.
- **Share or export** any guide: copy the link, or download it as PDF, Word, Markdown, HTML or JSON.

## How it works

Every message first goes through a quick check: is this an app name, a description of a need, a follow-up question, or too vague to act on? A vague request gets a clarifying question back instead of a guess.

For a new app, a small team of [Google ADK](https://google.github.io/adk-docs/) agents does the research:

1. **Resolver:** works out which app you mean and finds its developer portal. If the site has no third-party OAuth at all, it stops here and says so.
2. **Three agents in parallel:**
   - one researches review and approval rules
   - one researches the technical OAuth details
   - one tests the provider's endpoints live, using a fake client ID, with no accounts or credentials
3. **Writer:** turns the findings into the guide.
4. **Validator (plain code, no AI):** checks the result. A claim whose source was never actually opened loses its "sourced" label, and so does a scope or timeline that doesn't appear in the research.

You can watch all of this as it happens: short notes from the agents, each search and page read, a progress bar, and then the guide filling in on the right.

**Stack:**
- FastAPI and Google ADK running on Gemini
- web search through Gemini's Google Search, falling back to Tavily, then DuckDuckGo
- Postgres for guides, chats, runs and agent sessions
- token usage tracked per run with an ADK plugin

## Running it locally

```bash
cp .env.example .env        # add your GEMINI_API_KEY
docker compose up -d --build
open http://localhost:8000
```

Run the tests with `pytest`.

## Deploying

It's set up for Render with a free Postgres database on Neon:

1. Create a database on [neon.tech](https://neon.tech) and copy the connection string (with connection pooling off).
2. On Render: **New → Blueprint** and pick this repo. Paste in `GEMINI_API_KEY` and `DATABASE_URL`, and Render handles the rest.
3. To keep the free instance from sleeping, set a repository variable `APP_URL` to the live URL. The `keep-alive` workflow pings it every 10 minutes.

On first start, the library loads from `seed/`.

## Choices I made along the way

- **Only the "get your OAuth app approved" problem.** That's where developers lose days. How to call the API afterwards is already well documented.
- **Evidence over confidence.** The agent shows what it actually tested and read, and code enforces the labels, so the model can't mark its own homework.
- **Your effort and the provider's wait shown separately.** "2 hours of work plus 6 weeks of waiting" is a very different plan from "2 days of work".
- **Spell out who does each step.** Every step is marked agent, you, or provider, so you know where an agent can save you time and where you have to step in.
- **Don't waste tokens.** Library guides cost nothing to open, each agent has a small search budget, and simple inputs skip the extra AI call.
