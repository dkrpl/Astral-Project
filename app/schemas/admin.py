from pydantic import BaseModel

class AdminStats(BaseModel):
    total_users: int
    total_systems: int
    total_chat_sessions: int
    total_messages: int
    active_users_today: int
    new_users_this_week: int