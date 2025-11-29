from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

# =====================================================================================
# BASE SYSTEM
# =====================================================================================

class SystemBase(BaseModel):
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


# =====================================================================================
# CREATE SYSTEM (Swagger Example Ditambahkan)
# =====================================================================================

class SystemCreate(SystemBase):
    db_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "system_name": "My Remote DB",
                "system_type": "mysql",
                "db_host": "127.0.0.1",
                "db_port": 3306,
                "db_name": "mydb",
                "db_username": "user",
                "db_password": "pass",
                "connection_params": {
                    "bridge_url": "https://example.com/api-bridge.php",
                    "bridge_api_key": "astral-ai-secret-key-2024"
                },
                "table_mappings": {},
                "field_aliases": {},
                "business_rules": {}
            }
        }


# =====================================================================================
# SYSTEM MODEL RETURNED TO USER
# =====================================================================================

class System(SystemBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =====================================================================================
# TEST CONNECTION (Swagger Example Ditambahkan)
# =====================================================================================

class SystemTest(BaseModel):
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
                "db_name": "mydb",
                "db_username": "user",
                "db_password": "pass",
                "connection_params": {
                    "bridge_url": "https://example.com/api-bridge.php",
                    "bridge_api_key": "astral-ai-secret-key-2024"
                }
            }
        }


# =====================================================================================
# ADMIN VIEW
# =====================================================================================

class SystemAdmin(BaseModel):
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
