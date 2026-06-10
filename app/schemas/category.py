from pydantic_settings import BaseSettings
from app.config import settings
import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}

