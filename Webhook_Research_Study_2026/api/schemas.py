
from typing import Any

from pydantic import BaseModel, Field


class WebhookRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]


class WebhookResponse(BaseModel):
    event_id: str
    status: str
    message: str
