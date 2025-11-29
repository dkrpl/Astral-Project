from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    system_id = Column(Integer, nullable=True)  # Connected system
    session_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    is_user = Column(Boolean, default=True)  # True for user, False for AI
    sql_query = Column(Text)
    query_result = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())