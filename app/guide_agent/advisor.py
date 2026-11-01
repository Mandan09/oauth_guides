"""Answers follow-up questions in a chat, grounded in the guide that is open. One ADK session per chat."""

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import Runner

from app.config import settings
from app.guide_agent.agent import TOOL_BUDGET, _limit_tools
from app.guide_agent.llm import model
from app.guide_agent.tools.fetch import fetch_page
from app.guide_agent.tools.search import search_web
from app.guide_agent.usage import UsagePlugin

TOOL_BUDGET["advisor"] = 3
PROMPT = """You help a developer set up and get approval for an OAuth app so their AI agent can connect to users'
accounts. Answer their follow-up questions concisely and practically, in the language they write in.

Use the guide below first. Only if it does not answer the question, use search_web / fetch_page on official docs
(at most 3 calls), and say what you looked up. Cite sources inline as [title](url). Say plainly when something is
uncertain. Use short paragraphs or bullets; no long preambles.

Current guide:
"""


def _instruction(ctx) -> str:
    # a callable instruction skips ADK's {placeholder} templating, so guide text with braces is safe
    return PROMPT + (ctx.state.get("guide_md") or "No guide is open. Answer from general OAuth knowledge and search.")


advisor = LlmAgent(name="advisor", model=model(settings.research_model), instruction=_instruction,
                   tools=[search_web, fetch_page], before_tool_callback=_limit_tools)


def make_runner(session_service) -> Runner:
    return Runner(app=App(name="oauth_advisor", root_agent=advisor, plugins=[UsagePlugin()]), session_service=session_service)
