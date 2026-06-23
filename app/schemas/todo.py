import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: uuid.UUID | None = None

class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_completed: bool | None = None
    category_id: uuid.UUID | None = None

class TodoResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    is_completed: bool
    category_id: uuid.UUID | None = None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class TodoListResponse(BaseModel):
    items: list[TodoResponse]
    total: int
