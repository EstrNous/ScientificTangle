from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    reason: str
    type: str
    reference_id: str | None
    read: bool
    created_at: datetime

class UserInterestRequest(BaseModel):
    raw_text: str
    extracted_entities: dict | None = None