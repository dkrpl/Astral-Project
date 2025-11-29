from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json
import logging
from datetime import datetime
from app.database import get_db
from app.models.user import User, UserSystem
from app.models.chat import ChatSession, ChatMessage
from app.schemas import (
    ChatMessageCreateSchema, 
    ChatMessageResponseSchema, 
    ChatSessionCreateSchema, 
    ChatSessionResponseSchema, 
    ChatWithSystemSchema
)
from app.dependencies import get_current_active_user
from app.services.websocket import manager
from app.services.gemini_service import GeminiService
from app.services.database_service import DatabaseService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping-pong for keep alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@router.post("/sessions", response_model=ChatSessionResponseSchema)
async def create_chat_session(
    session_data: ChatSessionCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat session"""
    db_session = ChatSession(
        user_id=current_user.id,
        system_id=session_data.system_id,
        session_name=session_data.session_name
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    logger.info(f"User {current_user.id} created chat session: {session_data.session_name}")
    return db_session

@router.get("/sessions", response_model=list[ChatWithSystemSchema])
async def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all chat sessions for current user with system info"""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).all()
    
    # Enhance with system names
    enhanced_sessions = []
    for session in sessions:
        system_name = None
        if session.system_id:
            system = db.query(UserSystem).filter(
                UserSystem.id == session.system_id,
                UserSystem.user_id == current_user.id
            ).first()
            system_name = system.system_name if system else None
        
        session_dict = {
            "id": session.id,
            "user_id": session.user_id,
            "system_id": session.system_id,
            "session_name": session.session_name,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "system_name": system_name
        }
        enhanced_sessions.append(session_dict)
    
    return enhanced_sessions

@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponseSchema])
async def get_chat_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all messages in a chat session"""
    # Verify session belongs to user
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    # Parse query_result from JSON string to dict
    enhanced_messages = []
    for msg in messages:
        query_result = None
        if msg.query_result:
            try:
                query_result = json.loads(msg.query_result)
            except:
                query_result = {"raw": msg.query_result}
        
        msg_dict = {
            "id": msg.id,
            "message": msg.message,
            "is_user": msg.is_user,
            "sql_query": msg.sql_query,
            "query_result": query_result,
            "created_at": msg.created_at
        }
        enhanced_messages.append(msg_dict)
    
    return enhanced_messages

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponseSchema)
async def send_chat_message(
    session_id: int,
    message_data: ChatMessageCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message in chat session"""
    # Verify session belongs to user
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Determine which system to use
    system_id = message_data.system_id or session.system_id
    system_config = None
    db_service = None
    table_schema = {}
    
    if system_id:
        system = db.query(UserSystem).filter(
            UserSystem.id == system_id,
            UserSystem.user_id == current_user.id,
            UserSystem.is_active == True
        ).first()
        
        if system:
            # Prepare system configuration
            system_config = {
                'table_mappings': system.table_mappings or {},
                'field_aliases': system.field_aliases or {},
                'business_rules': system.business_rules or {}
            }
            
            # Initialize database service
            db_config = {
                'db_host': system.db_host,
                'db_port': system.db_port,
                'db_name': system.db_name,
                'db_username': system.db_username,
                'db_password': system.db_password,
                'connection_params': system.connection_params or {}
            }
            
            db_service = DatabaseService(db_config)
            table_schema = await db_service.get_table_schema()
    
    # Save user message
    user_message = ChatMessage(
        session_id=session_id,
        user_id=current_user.id,
        message=message_data.message,
        is_user=True
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Process with AI
    ai_response = "Halo! Saya Astral AI Assistant. Silakan tanyakan apa saja tentang data Anda."
    
    if system_id and system and db_service and table_schema:
        try:
            gemini_service = GeminiService()
            ai_result = await gemini_service.process_chat_message(
                user_query=message_data.message,
                table_schema=table_schema,
                db_service=db_service,
                system_config=system_config
            )
            
            ai_response = ai_result['response']
            
            # Save AI response
            ai_message = ChatMessage(
                session_id=session_id,
                user_id=current_user.id,
                message=ai_response,
                is_user=False,
                sql_query=ai_result.get('sql_query'),
                query_result=json.dumps(ai_result.get('query_result')) if ai_result.get('query_result') else None
            )
            
        except Exception as e:
            logger.error(f"AI processing error: {str(e)}")
            ai_message = ChatMessage(
                session_id=session_id,
                user_id=current_user.id,
                message=f"Maaf, terjadi error: {str(e)}",
                is_user=False
            )
    else:
        # No system connected - basic response
        if system_id and not system:
            ai_response = "Sistem tidak ditemukan atau tidak aktif. Silakan periksa koneksi sistem Anda."
        elif not system_id:
            ai_response = "Silakan pilih sistem terlebih dahulu atau hubungkan sistem Anda untuk bertanya tentang data."
        
        ai_message = ChatMessage(
            session_id=session_id,
            user_id=current_user.id,
            message=ai_response,
            is_user=False
        )
    
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)
    
    # Update session timestamp - FIX: Use datetime.utcnow() instead of undefined db_message
    session.updated_at = datetime.utcnow()
    db.commit()
    
    # Send real-time update via WebSocket
    await manager.send_personal_message(
        json.dumps({
            "type": "new_message",
            "message": ai_message.message,
            "is_user": False,
            "session_id": session_id,
            "created_at": ai_message.created_at.isoformat()
        }),
        current_user.id
    )
    
    # Prepare response
    query_result = None
    if ai_message.query_result:
        try:
            query_result = json.loads(ai_message.query_result)
        except:
            query_result = {"raw": ai_message.query_result}
    
    return ChatMessageResponseSchema(
        id=ai_message.id,
        message=ai_message.message,
        is_user=ai_message.is_user,
        sql_query=ai_message.sql_query,
        query_result=query_result,
        created_at=ai_message.created_at
    )

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat session and all its messages"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete all messages in the session
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    
    # Delete the session
    db.delete(session)
    db.commit()
    
    logger.info(f"User {current_user.id} deleted chat session: {session_id}")
    return {"message": "Chat session deleted successfully"}

@router.get("/sessions/{session_id}/info")
async def get_session_info(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed information about a chat session"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get message count
    message_count = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).count()
    
    # Get system info if available
    system_info = None
    if session.system_id:
        system = db.query(UserSystem).filter(
            UserSystem.id == session.system_id,
            UserSystem.user_id == current_user.id
        ).first()
        if system:
            system_info = {
                "id": system.id,
                "name": system.system_name,
                "type": system.system_type,
                "database": system.db_name
            }
    
    return {
        "session": {
            "id": session.id,
            "name": session.session_name,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": message_count
        },
        "system": system_info
    }