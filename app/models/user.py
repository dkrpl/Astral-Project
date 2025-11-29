from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_superadmin = Column(Boolean, default=False)  # Full system access
    last_login = Column(DateTime(timezone=True))
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserSystem(Base):
    __tablename__ = "user_systems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    system_name = Column(String(255), nullable=False)
    system_type = Column(String(50), nullable=False)
    db_host = Column(String(255), nullable=False)
    db_port = Column(Integer, nullable=False)
    db_name = Column(String(255), nullable=False)
    db_username = Column(String(255), nullable=False)
    db_password = Column(String(255), nullable=False)
    
    connection_params = Column(JSON, default=dict)
    table_mappings = Column(JSON, default=dict)
    field_aliases = Column(JSON, default=dict)
    business_rules = Column(JSON, default=dict)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())