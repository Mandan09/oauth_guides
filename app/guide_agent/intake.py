"""First step for every message: is it an app name, or a need we should match to a service?"""

import logging
from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field

from app.config import settings
from app.guide_agent.llm import gemini

log = logging.getLogger(__name__)

PROMPT = """You help developers who are building AI agents that connect to third-party apps via OAuth.
Classify the developer's message and respond.

- kind "app": they named one specific app or website. Set app to its common name (or the URL if that is all
  they gave). If they name an app other than the current guide ({current}), it is always "app", even in a
  short message like "jira guide".
- kind "need": they described what their agent must do. Pick 2-4 well-known services that fit and support
  third-party OAuth; put the best fit first with a short, concrete reason. Summarise their use case as the
  actions the agent must perform (e.g. read projects, create tasks, update task status, assign users).
- kind "followup": a question about the guide currently open ({current}) or about OAuth setup in general
  (e.g. "which scopes for webhooks?", "how do refresh tokens work?", "do I need a privacy policy?").
  Leave reply empty; another agent will answer it.
- kind "clarify": they refer to a specific app, API, provider or OAuth app without saying which one
  (e.g. "an API documentation page", "the provider", "a third-party API"), so it cannot be researched.
  reply: ask ONE short question for the name or URL and say what you will do once you have it.
- kind "other": not about connecting an app via OAuth. Explain briefly what you can help with.

fresh: true only if they explicitly ask for new, fresh, updated or re-done research (e.g. "research Slack again").

use_case: whenever they say what their agent must do (for "app" or "need"), list those actions in one line.

reply: 1-3 friendly sentences to the developer in the same language they wrote in. For "need", say you are
researching the top pick now and they can open a guide for any alternative below. Do not invent approval
timelines or scopes; a researched guide will cover those.

Developer message:
{message}"""


class Candidate(BaseModel):
    name: str
    website: str
    why: str


class Intake(BaseModel):
    kind: Literal["app", "need", "followup", "clarify", "other"]
    app: str = ""
    use_case: str = Field("", description="The agent's required actions, one line")
    fresh: bool = False
    candidates: list[Candidate] = []
    reply: str


async def classify(message: str, current: str = "") -> Intake:
    if not current and len(message) <= 60 and "\n" not in message and "?" not in message:
        return Intake(kind="app", app=message.strip(), reply="")  # short input: treat as an app name, no LLM call
    try:
        resp = await gemini().aio.models.generate_content(
            model=settings.research_model, contents=PROMPT.replace("{current}", current or "none").replace("{message}", message),
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Intake),
        )
        return Intake.model_validate_json(resp.text)
    except Exception as e:
        log.warning("intake failed, treating input as an app name: %s", e)
        return Intake(kind="app", app=message[:200], reply="")
