from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class ChatSessionCreate(BaseModel):
    title: str

class ChatMessageCreate(BaseModel):
    content: str
    query_run_id: UUID | None = None

class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: str
    content: str
    created_at: datetime