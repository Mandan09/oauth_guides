import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    database_url: str = ""

    research_model: str = "gemini-flash-latest"
    writer_model: str = "gemini-pro-latest"
    search_model: str = "gemini-flash-latest"
    # LiteLLM model ids tried in order when Gemini fails
    fallback_models: str = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free,groq/openai/gpt-oss-120b"

    openrouter_api_key: str = ""
    groq_api_key: str = ""
    tavily_api_key: str = ""

    runs_per_ip_per_hour: int = 5
    runs_per_day: int = 50
    admin_token: str = ""

    @property
    def db_url(self) -> str:
        """Accept a plain Neon/Postgres URL and convert it for asyncpg."""
        url = (self.database_url or "sqlite+aiosqlite:///./local.db").replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)
        return url.replace("sslmode=require", "ssl=require").replace("&channel_binding=require", "")

    @property
    def fallbacks(self) -> list[str]:
        keys = {"openrouter": self.openrouter_api_key, "groq": self.groq_api_key}
        models = [m.strip() for m in self.fallback_models.split(",") if m.strip()]
        return [m for m in models if keys.get(m.split("/")[0], "x")]


settings = Settings()
# google-genai and LiteLLM read keys from the environment
for var, value in {
    "GEMINI_API_KEY": settings.gemini_api_key,
    "OPENROUTER_API_KEY": settings.openrouter_api_key,
    "GROQ_API_KEY": settings.groq_api_key,
}.items():
    if value:
        os.environ.setdefault(var, value)
