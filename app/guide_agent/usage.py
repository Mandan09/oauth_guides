"""Token accounting via ADK's plugin hook: every model response carries usage_metadata."""

from google.adk.plugins.base_plugin import BasePlugin


def add_usage(state, who: str, usage) -> None:
    """Accumulate one response's tokens under state["usage"][who]."""
    if not usage:
        return
    totals = dict(state.get("usage", {}))
    row = dict(totals.get(who, {"calls": 0, "input": 0, "output": 0}))
    row["calls"] += 1
    row["input"] += usage.prompt_token_count or 0
    row["output"] += (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    totals[who] = row
    state["usage"] = totals


class UsagePlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="usage")

    async def after_model_callback(self, *, callback_context, llm_response):
        if not llm_response.partial:  # streamed chunks repeat; count the complete response once
            add_usage(callback_context.state, callback_context.agent_name, llm_response.usage_metadata)
        return None


def summarize(state: dict) -> dict:
    usage = state.get("usage", {})
    tools = [k for k in state if k.startswith("tool_calls_")]
    return {
        "input_tokens": sum(r["input"] for r in usage.values()),
        "output_tokens": sum(r["output"] for r in usage.values()),
        "model_calls": sum(r["calls"] for r in usage.values()),
        "searches": len(state.get("search_providers", [])),
        "tool_calls": sum(state[k] for k in tools),
        "by_agent": usage,
    }
