from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime

# ===============================
# USER SCHEMAS
# ===============================
class UserBaseSchema(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreateSchema(UserBaseSchema):
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "full_name": "John Doe",
                "is_active": True,
                "password": "yourpassword123"
            }
        }

class UserLoginSchema(BaseModel):
    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "yourpassword123"
            }
        }

class UserResponseSchema(UserBaseSchema):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===============================
# AUTH SCHEMAS
# ===============================
class TokenSchema(BaseModel):
    access_token: str
    token_type: str

class TokenDataSchema(BaseModel):
    username: Optional[str] = None


# ===============================
# SYSTEM SCHEMAS
# ===============================
class SystemBaseSchema(BaseModel):
    system_name: str
    system_type: str
    db_host: str
    db_port: int
    db_name: str
    db_username: str
    connection_params: Optional[Dict] = None
    table_mappings: Optional[Dict] = None
    field_aliases: Optional[Dict] = None
    business_rules: Optional[Dict] = None

class SystemCreateSchema(SystemBaseSchema):
    db_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "system_name": "Sales DB",
                "system_type": "mysql",
                "db_host": "127.0.0.1",
                "db_port": 3306,
                "db_name": "salesdb",
                "db_username": "root",
                "db_password": "secret123",
                "connection_params": {
                    "bridge_url": "https://astral.ai/bridge.php",
                    "bridge_api_key": "astral-secret-key"
                },
                "table_mappings": {
                    "products": "tbl_products"
                },
                "field_aliases": {
                    "product_name": "name"
                },
                "business_rules": {
                    "limit": "100"
                }
            }
        }

class SystemResponseSchema(SystemBaseSchema):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SystemTestSchema(BaseModel):
    system_type: str
    db_host: str
    db_port: int
    db_name: str
    db_username: str
    db_password: str
    connection_params: Optional[Dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "system_type": "mysql",
                "db_host": "127.0.0.1",
                "db_port": 3306,
                "db_name": "test_db",
                "db_username": "root",
                "db_password": "password123",
                "connection_params": {
                    "bridge_url": "https://example.com/bridge",
                    "bridge_api_key": "bridge-secret"
                }
            }
        }


# ===============================
# CHAT SCHEMAS
# ===============================
class ChatMessageBaseSchema(BaseModel):
    message: str
    session_id: Optional[int] = None
    system_id: Optional[int] = None

class ChatMessageCreateSchema(ChatMessageBaseSchema):
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Tampilkan list data dari tabel products",
                "session_id": 1,
                "system_id": 2
            }
        }

class ChatMessageResponseSchema(BaseModel):
    id: int
    message: str
    is_user: bool
    sql_query: Optional[str] = None
    query_result: Optional[Dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionBaseSchema(BaseModel):
    session_name: str
    system_id: Optional[int] = None

class ChatSessionCreateSchema(ChatSessionBaseSchema):
    class Config:
        json_schema_extra = {
            "example": {
                "session_name": "Sales Analytics 01",
                "system_id": 2
            }
        }

class ChatSessionResponseSchema(ChatSessionBaseSchema):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatWithSystemSchema(ChatSessionResponseSchema):
    system_name: Optional[str] = None

    class Config:
        from_attributes = True


# ===============================
# ADMIN SCHEMAS
# ===============================
class UserAdminSchema(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    is_superadmin: bool
    last_login: Optional[datetime] = None
    login_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreateAdminSchema(UserCreateSchema):
    is_admin: bool = False
    is_superadmin: bool = False

class UserUpdateAdminSchema(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_superadmin: Optional[bool] = None


class AdminStatsSchema(BaseModel):
    total_users: int
    total_systems: int
    total_chat_sessions: int
    total_messages: int
    active_users_today: int
    new_users_this_week: int


class SystemAdminSchema(BaseModel):
    id: int
    user_id: int
    user_email: str
    system_name: str
    system_type: str
    db_host: str
    db_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
