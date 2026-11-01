from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    client_id: str = Field(min_length=8, max_length=36)
    title: str = Field(max_length=200)
    items: list[dict] = Field(max_length=200)


class AnswerIn(BaseModel):
    client_id: str = Field(min_length=8, max_length=36)
    message: str = Field(min_length=1, max_length=2000)
    slug: str = Field("", max_length=80)
