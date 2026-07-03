from uuid import UUID
from pydantic import BaseModel, ConfigDict

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    type: str
    message: str
    is_read: bool

class UserInterestRequest(BaseModel):
    raw_text: str
    extracted_entities: dict | None = None