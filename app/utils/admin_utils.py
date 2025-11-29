from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.models.user import User, UserSystem
from app.models.chat import ChatSession, ChatMessage
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class AdminUtils:
    
    @staticmethod
    def get_system_stats(db: Session) -> Dict[str, Any]:
        """Get comprehensive system statistics for admin dashboard"""
        
        # User statistics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.is_admin == True).count()
        
        # Today's active users (logged in today)
        today = datetime.utcnow().date()
        active_today = db.query(User).filter(
            User.last_login >= today,
            User.is_active == True
        ).count()
        
        # New users this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = db.query(User).filter(
            User.created_at >= week_ago
        ).count()
        
        # System statistics
        total_systems = db.query(UserSystem).count()
        active_systems = db.query(UserSystem).filter(UserSystem.is_active == True).count()
        
        # Chat statistics
        total_sessions = db.query(ChatSession).count()
        total_messages = db.query(ChatMessage).count()
        
        # Recent activity (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.created_at >= day_ago
        ).count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "admins": admin_users,
                "active_today": active_today,
                "new_this_week": new_users_week
            },
            "systems": {
                "total": total_systems,
                "active": active_systems
            },
            "chat": {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "recent_messages_24h": recent_messages
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_user_activity(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Get user activity data for admin monitoring"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get users with their activity counts
        user_activity = db.query(
            User.id,
            User.username,
            User.email,
            User.full_name,
            User.last_login,
            User.login_count,
            User.created_at,
            func.count(ChatSession.id).label('session_count'),
            func.count(ChatMessage.id).label('message_count')
        ).outerjoin(ChatSession, User.id == ChatSession.user_id)\
         .outerjoin(ChatMessage, User.id == ChatMessage.user_id)\
         .filter(
            ChatSession.created_at >= start_date if days > 0 else True,
            ChatMessage.created_at >= start_date if days > 0 else True
         )\
         .group_by(User.id)\
         .order_by(desc(User.last_login))\
         .all()
        
        result = []
        for user in user_activity:
            result.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "login_count": user.login_count,
                "created_at": user.created_at.isoformat(),
                "session_count": user.session_count,
                "message_count": user.message_count
            })
        
        return result
    
    @staticmethod
    def get_system_usage(db: Session) -> List[Dict[str, Any]]:
        """Get system usage statistics across all users"""
        
        system_usage = db.query(
            UserSystem.id,
            UserSystem.system_name,
            UserSystem.system_type,
            UserSystem.db_host,
            UserSystem.db_name,
            UserSystem.is_active,
            UserSystem.created_at,
            User.username,
            User.email,
            func.count(ChatSession.id).label('usage_count')
        ).join(User, UserSystem.user_id == User.id)\
         .outerjoin(ChatSession, UserSystem.id == ChatSession.system_id)\
         .group_by(UserSystem.id)\
         .order_by(desc('usage_count'))\
         .all()
        
        result = []
        for system in system_usage:
            result.append({
                "id": system.id,
                "system_name": system.system_name,
                "system_type": system.system_type,
                "db_host": system.db_host,
                "db_name": system.db_name,
                "is_active": system.is_active,
                "created_at": system.created_at.isoformat(),
                "user": {
                    "username": system.username,
                    "email": system.email
                },
                "usage_count": system.usage_count
            })
        
        return result