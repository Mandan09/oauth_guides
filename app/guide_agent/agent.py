from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.genai import types

from app.config import settings
from app.guide_agent import prompts
from app.guide_agent.llm import model
from app.guide_agent.tools.fetch import fetch_page
from app.guide_agent.tools.probe import check_discovery, probe_authorize
from app.guide_agent.tools.search import search_web
from app.guides.schemas import GuideDraft

TOOL_BUDGET = {"resolver": 3, "review_researcher": 6, "oauth_researcher": 5, "prober": 5}


def _limit_tools(tool, args, tool_context):
    """Cap tool calls per agent so runs stay fast and within free quotas."""
    key = f"tool_calls_{tool_context.agent_name}"
    tool_context.state[key] = tool_context.state.get(key, 0) + 1
    if tool_context.state[key] > TOOL_BUDGET.get(tool_context.agent_name, 5):
        return {"error": "Tool budget used up. Write your final answer now from what you have."}
    return None


def _agent(name: str, instruction: str, tools: list, output_key: str, **kw) -> LlmAgent:
    # include_contents="none": each agent works from state, not the full chat history
    if name in TOOL_BUDGET:
        instruction += f"\nHard limit: at most {TOOL_BUDGET[name]} tool calls in total, so choose them carefully."
    return LlmAgent(name=name, model=model(kw.pop("llm", settings.research_model)), instruction=instruction,
                    tools=tools, output_key=output_key, include_contents="none",
                    before_tool_callback=_limit_tools, **kw)


resolver = _agent("resolver", prompts.RESOLVER, [search_web], "app_profile")
review = _agent("review_researcher", prompts.REVIEW_RESEARCHER, [search_web, fetch_page], "review_notes")
oauth = _agent("oauth_researcher", prompts.OAUTH_RESEARCHER, [search_web, fetch_page], "oauth_notes")
prober = _agent("prober", prompts.PROBER, [check_discovery, probe_authorize, fetch_page], "probe_notes")
writer = _agent("writer", prompts.WRITER, [], "guide_draft", llm=settings.writer_model, output_schema=GuideDraft)

def _stop_without_oauth(callback_context):
    """Skip research and writing when the resolver found no third-party OAuth (saves most of the tokens)."""
    profile = callback_context.state.get("app_profile", "").lower()
    if "supports oauth: no" in profile or "app: unknown" in profile:
        return types.Content(role="model", parts=[types.Part(text="Stopped: no third-party OAuth to research.")])
    return None


investigate = ParallelAgent(name="investigate", sub_agents=[review, oauth, prober])
# the skip sits on a wrapper: on the writer itself ADK would validate the skip message against its output schema
research = SequentialAgent(name="research", sub_agents=[investigate, writer], before_agent_callback=_stop_without_oauth)
root_agent = SequentialAgent(name="guide_pipeline", sub_agents=[resolver, research])
