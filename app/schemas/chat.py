from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class ChatMessageBase(BaseModel):
    message: str
    session_id: Optional[int] = None
    system_id: Optional[int] = None

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(BaseModel):
    id: int
    message: str
    is_user: bool
    sql_query: Optional[str] = None
    query_result: Optional[Dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    session_name: str
    system_id: Optional[int] = None

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ChatWithSystem(ChatSession):
    system_name: Optional[str] = None

    class Config:
        from_attributes = True