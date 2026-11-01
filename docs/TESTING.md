# Live test results

Run on 2026-11-01 against the local Docker stack, through the chat UI. Each test was typed as a developer would, in its own chat.

## Tests run

| # | Prompt (short) | What happened | Time | Result |
|---|---|---|---|---|
| 1 | OAuth for Google Drive | Live research → guide rated **hard**: testing mode is easy, but `drive.readonly` / `drive` are restricted scopes needing verification plus a paid CASA assessment; `drive.file` only needs light verification | 146 s · 10 searches · 63.3k tokens | Pass |
| 7 | HubSpot: customer records + deals | Library guide opened instantly, then the advisor mapped the use case to `crm.objects.contacts.read`, `crm.objects.companies.read`, `crm.objects.deals.read/write` | ~35 s | Pass (after fix) |
| 11 | Vague: manage projects, assign tasks | Recommended Asana with alternatives, opened the library guide | ~5 s | Pass |
| 18 | "Unverified app" warning | Streamed general answer (Google verification, Microsoft publisher verification) | ~25 s | Pass |
| 21 | Zoho CRM, investigate the portal | Live research → rated **easy**, scopes like `ZohoCRM.modules.ALL`, 14 sources all on zoho.com | 146 s | Pass |
| 22 | `https://example.com` | Identified a reserved placeholder domain (RFC 2606), stopped after one step, reported "no OAuth" instead of inventing a guide | ~30 s | Pass (after fix) |
| 22b | Real unfamiliar site: keka.com (HR) | Live research → rated **moderate**: sandbox approval plus a 2–3 week marketplace review; 7 sources on keka.com | 107 s | Pass, scopes unverified |
| 5 | Dropbox: upload, download, search | Rated **moderate**; scopes `files.content.write/read`, `files.metadata.read` confirmed against the research | 155 s · 9 searches · 64.3k tokens | Pass |
| 6 | Gmail: read and send replies | Rated **hard**: Google verification plus annual CASA for restricted Gmail scopes; draft canvas showed findings from 36 s | 147 s · 9 searches · 53.9k tokens | Pass |
| 9 | GitHub: repositories and pull requests | Live research, new guide | 170 s | Pass |
| 23 | "An API documentation page" (no URL) | Asked one clarifying question for the name or URL | ~4 s | Pass |
| 25 | "The provider hasn't approved my app" (no provider) | Asked which provider | ~4 s | Pass |

Earlier sessions also generated Notion, Slack, HubSpot, Asana, Linear and Jira guides.

## Scorecard (12 checks)

| Check | Verdict | Notes |
|---|---|---|
| Identifies the provider | ✅ | Including need-based prompts and placeholder URLs |
| Finds official documentation | ✅ | Drive: developers/support.google.com; Zoho: zoho.com; Keka: developers.keka.com |
| Identifies the authentication method | ✅ | Resolver reports OAuth yes/no/unknown and the method actually used |
| Required scopes and permissions | ✅ | "Permissions your agent needs" table; library guides get a scope answer for the stated use case |
| Registration prerequisites | ✅ | First stage of every guide |
| Actionable step-by-step | ✅ | Ordered stages with owners and durations |
| Hands-on effort vs approval wait | ✅ | Separate tiles for hands-on work, approval wait, first connection and production |
| Verification and publishing requirements | ✅ | e.g. Google CASA, HubSpot Marketplace, Keka marketplace review |
| Agent vs human steps | ✅ | Owner on every step, plus "What an agent can do" and "Where you take over" |
| Cites sources | ✅ | Every claim carries source ids; the validator flags sources the agent never opened |
| Marks assumptions and unverified info | ✅ (after fix) | Writer rules tightened; the validator now downgrades timelines and scope strings that never appear in the research, and every guide lists its assumptions and estimates. Dropbox retest: all 3 scopes confirmed against the research, 2 assumptions listed |
| Persistent, shareable guide | ✅ | `/g/<slug>` link, PDF, DOCX, Markdown, HTML, JSON |

## Bugs found by these tests and fixed

- Library guides created before the permissions feature had no use-case scopes → the advisor now answers the scope question automatically.
- A run that finished while the user was in another chat never added its guide card → added when the chat is replayed.
- Prompts naming no app made the agent guess → new "clarify" step asks for the name or URL.
- Apps without OAuth still went through full research and writing → the pipeline stops after identification and reports the finding (needed a wrapper agent, because ADK validates any writer output against the guide schema).
- Markdown headings and dividers in answers showed as raw text.

## Known gaps

- Guides generated before this fix keep their old labels until regenerated; their permission rows show as "uncertain" because they were never checked.
- Not independently verified yet: the Keka scope names, and whether the Zoho guide covers region-specific accounts domains.
- When a library guide matches, the intake's reply can say "researching", which is wrong.
- A new guide takes about 2–2.5 minutes and about 60k tokens.
