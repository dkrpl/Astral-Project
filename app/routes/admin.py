from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from app.database import get_db
from app.models.user import User, UserSystem
from app.models.chat import ChatSession, ChatMessage
from app.schemas import (
    UserAdminSchema, 
    UserCreateAdminSchema, 
    UserUpdateAdminSchema, 
    AdminStatsSchema, 
    SystemAdminSchema
)
from app.dependencies import get_current_admin_user, get_current_superadmin_user
from app.utils.admin_utils import AdminUtils

router = APIRouter()
logger = logging.getLogger(__name__)

# ... (rest of the code remains the same)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ===== ADMIN DASHBOARD =====
@router.get("/dashboard/stats")
async def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get comprehensive statistics for admin dashboard"""
    try:
        stats = AdminUtils.get_system_stats(db)
        return {
            "success": True,
            "data": stats,
            "message": "Dashboard stats retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving dashboard statistics")

@router.get("/dashboard/user-activity")
async def get_user_activity(
    days: int = Query(7, description="Number of days to look back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get user activity data for admin monitoring"""
    try:
        activity_data = AdminUtils.get_user_activity(db, days)
        return {
            "success": True,
            "data": activity_data,
            "message": f"User activity for last {days} days retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving user activity")

@router.get("/dashboard/system-usage")
async def get_system_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get system usage statistics across all users"""
    try:
        system_usage = AdminUtils.get_system_usage(db)
        return {
            "success": True,
            "data": system_usage,
            "message": "System usage data retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting system usage: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving system usage data")

# ===== USER MANAGEMENT =====
@router.get("/users", response_model=List[UserAdminSchema])
async def get_all_users_admin(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Number of records to return"),
    active_only: bool = Query(True, description="Return only active users"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all users (admin only)"""
    query = db.query(User)
    
    if active_only:
        query = query.filter(User.is_active == True)
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.post("/users", response_model=UserAdminSchema)
async def create_user_admin(
    user_data: UserCreateAdminSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin_user)
):
    """Create new user (superadmin only)"""
    # Check if user already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create new user with admin privileges
    from app.utils.security import get_password_hash
    hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=user_data.is_active,
        is_admin=user_data.is_admin,
        is_superadmin=user_data.is_superadmin
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Admin {current_user.username} created user: {user_data.username}")
    return db_user

@router.get("/users/{user_id}", response_model=UserAdminSchema)
async def get_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get specific user details (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.put("/users/{user_id}", response_model=UserAdminSchema)
async def update_user_admin(
    user_id: int,
    user_data: UserUpdateAdminSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin_user)
):
    """Update user (superadmin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields if provided
    if user_data.email is not None:
        # Check if email is already taken by another user
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already taken")
        user.email = user_data.email
    
    if user_data.username is not None:
        # Check if username is already taken by another user
        existing = db.query(User).filter(User.username == user_data.username, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = user_data.username
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    
    if user_data.is_superadmin is not None:
        user.is_superadmin = user_data.is_superadmin
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Superadmin {current_user.username} updated user: {user.username}")
    return user

@router.delete("/users/{user_id}")
async def deactivate_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin_user)
):
    """Deactivate user (soft delete) - superadmin only"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    db.commit()
    
    logger.info(f"Superadmin {current_user.username} deactivated user: {user.username}")
    return {"message": "User deactivated successfully"}

# ===== SYSTEM MANAGEMENT =====
@router.get("/systems", response_model=List[SystemAdminSchema])
async def get_all_systems_admin(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Number of records to return"),
    active_only: bool = Query(True, description="Return only active systems"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all systems across all users (admin only)"""
    query = db.query(UserSystem).join(User, UserSystem.user_id == User.id)
    
    if active_only:
        query = query.filter(UserSystem.is_active == True)
    
    systems = query.offset(skip).limit(limit).all()
    
    # Convert to response model
    result = []
    for system in systems:
        result.append({
            "id": system.id,
            "user_id": system.user_id,
            "user_email": system.user.email,
            "system_name": system.system_name,
            "system_type": system.system_type,
            "db_host": system.db_host,
            "db_name": system.db_name,
            "is_active": system.is_active,
            "created_at": system.created_at
        })
    
    return result

@router.get("/systems/{system_id}")
async def get_system_admin(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get specific system details (admin only)"""
    system = db.query(UserSystem).filter(UserSystem.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    user = db.query(User).filter(User.id == system.user_id).first()
    
    return {
        "id": system.id,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        },
        "system_name": system.system_name,
        "system_type": system.system_type,
        "db_host": system.db_host,
        "db_port": system.db_port,
        "db_name": system.db_name,
        "db_username": system.db_username,
        "connection_params": system.connection_params,
        "table_mappings": system.table_mappings,
        "field_aliases": system.field_aliases,
        "business_rules": system.business_rules,
        "is_active": system.is_active,
        "created_at": system.created_at,
        "updated_at": system.updated_at
    }

# ===== CHAT MONITORING =====
@router.get("/chats/recent")
async def get_recent_chats_admin(
    limit: int = Query(50, description="Number of recent messages to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get recent chat messages across all users (admin only)"""
    messages = db.query(ChatMessage).join(
        ChatSession, ChatMessage.session_id == ChatSession.id
    ).join(
        User, ChatSession.user_id == User.id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    result = []
    for msg in messages:
        session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
        user = db.query(User).filter(User.id == msg.user_id).first()
        
        result.append({
            "id": msg.id,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "session_id": msg.session_id,
            "session_name": session.session_name if session else "Unknown",
            "message": msg.message,
            "is_user": msg.is_user,
            "sql_query": msg.sql_query,
            "created_at": msg.created_at.isoformat()
        })
    
    return {
        "success": True,
        "data": result,
        "message": "Recent chats retrieved successfully"
    }

@router.get("/chats/sessions")
async def get_all_sessions_admin(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all chat sessions across all users (admin only)"""
    sessions = db.query(ChatSession).join(
        User, ChatSession.user_id == User.id
    ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for session in sessions:
        user = db.query(User).filter(User.id == session.user_id).first()
        system = db.query(UserSystem).filter(UserSystem.id == session.system_id).first() if session.system_id else None
        message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
        
        result.append({
            "id": session.id,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "session_name": session.session_name,
            "system": {
                "id": system.id if system else None,
                "name": system.system_name if system else None
            },
            "message_count": message_count,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat() if session.updated_at else None
        })
    
    return {
        "success": True,
        "data": result,
        "message": "Chat sessions retrieved successfully"
    }