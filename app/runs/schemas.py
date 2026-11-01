from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200, description="App name or website")
    use_case: str = Field("", max_length=2000, description="What the agent must do, if known")
    force: bool = Field(False, description="Research again even if a guide exists (still rate limited)")


class RunStarted(BaseModel):
    run_id: str | None = None
    slug: str | None = None


class AskRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    slug: str = Field("", max_length=80, description="Guide open in the chat, for follow-up questions")
