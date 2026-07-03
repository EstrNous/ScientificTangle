from uuid import UUID
from pydantic import BaseModel, ConfigDict

class ExportJobCreate(BaseModel):
    user_id: UUID
    format: str  # 'pdf', 'markdown', 'json', 'json-ld'

class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    status: str
    format: str
    file_url: str | None = None