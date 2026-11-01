from functools import cache

from google import genai
from google.adk.models import FallbackModel
from google.adk.models.lite_llm import LiteLlm

from app.config import settings


def model(primary: str) -> str | FallbackModel:
    """Primary Gemini model, falling back to LiteLLM models on 429/5xx."""
    if not settings.fallbacks:
        return primary
    return FallbackModel(models=[primary, *[LiteLlm(model=m) for m in settings.fallbacks]])


@cache
def gemini() -> genai.Client:
    """One shared client; a throwaway client closes its HTTP session mid-request."""
    return genai.Client()
