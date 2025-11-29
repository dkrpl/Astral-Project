from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserSystem
from app.schemas import SystemCreateSchema, SystemResponseSchema, SystemTestSchema
from app.dependencies import get_current_active_user
from app.services.database_service import DatabaseService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/test-connection")
async def test_system_connection(
    test_config: SystemTestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)  # ✅ Now User is defined
):
    """Test database connection before saving"""
    try:
        db_config = {
            'db_host': test_config.db_host,
            'db_port': test_config.db_port,
            'db_name': test_config.db_name,
            'db_username': test_config.db_username,
            'db_password': test_config.db_password,
            'connection_params': test_config.connection_params or {}
        }
        
        db_service = DatabaseService(db_config)
        result = await db_service.test_connection()
        
        return result
            
    except Exception as e:
        logger.error(f"Connection test error: {str(e)}")
        return {"success": False, "message": str(e)}

@router.post("/", response_model=SystemResponseSchema)
async def create_system(
    system_data: SystemCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new system connection"""
    
    # Test database connection first
    test_config = SystemTestSchema(
        system_type=system_data.system_type,
        db_host=system_data.db_host,
        db_port=system_data.db_port,
        db_name=system_data.db_name,
        db_username=system_data.db_username,
        db_password=system_data.db_password,
        connection_params=system_data.connection_params
    )
    
    test_result = await test_system_connection(test_config, db, current_user)
    if not test_result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=f"Connection test failed: {test_result.get('message')}"
        )
    
    # Create system record
    db_system = UserSystem(
        user_id=current_user.id,
        system_name=system_data.system_name,
        system_type=system_data.system_type,
        db_host=system_data.db_host,
        db_port=system_data.db_port,
        db_name=system_data.db_name,
        db_username=system_data.db_username,
        db_password=system_data.db_password,
        connection_params=system_data.connection_params or {},
        table_mappings=system_data.table_mappings or {},
        field_aliases=system_data.field_aliases or {},
        business_rules=system_data.business_rules or {}
    )
    
    db.add(db_system)
    db.commit()
    db.refresh(db_system)
    
    logger.info(f"User {current_user.id} created system: {system_data.system_name}")
    return db_system

@router.get("/", response_model=list[SystemResponseSchema])
async def get_systems(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all systems for current user"""
    systems = db.query(UserSystem).filter(
        UserSystem.user_id == current_user.id,
        UserSystem.is_active == True
    ).all()
    
    return systems

@router.get("/{system_id}", response_model=SystemResponseSchema)
async def get_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific system"""
    system = db.query(UserSystem).filter(
        UserSystem.id == system_id,
        UserSystem.user_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    return system

@router.put("/{system_id}", response_model=SystemResponseSchema)
async def update_system(
    system_id: int,
    system_data: SystemCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update system configuration"""
    system = db.query(UserSystem).filter(
        UserSystem.id == system_id,
        UserSystem.user_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    # Update fields
    system.system_name = system_data.system_name
    system.system_type = system_data.system_type
    system.db_host = system_data.db_host
    system.db_port = system_data.db_port
    system.db_name = system_data.db_name
    system.db_username = system_data.db_username
    system.db_password = system_data.db_password
    system.connection_params = system_data.connection_params or {}
    system.table_mappings = system_data.table_mappings or {}
    system.field_aliases = system_data.field_aliases or {}
    system.business_rules = system_data.business_rules or {}
    
    db.commit()
    db.refresh(system)
    
    logger.info(f"User {current_user.id} updated system: {system.system_name}")
    return system

@router.delete("/{system_id}")
async def delete_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete system (soft delete)"""
    system = db.query(UserSystem).filter(
        UserSystem.id == system_id,
        UserSystem.user_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    system.is_active = False
    db.commit()
    
    logger.info(f"User {current_user.id} deleted system: {system.system_name}")
    return {"message": "System deleted successfully"}

@router.get("/{system_id}/schema")
async def get_system_schema(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get database schema for a system"""
    system = db.query(UserSystem).filter(
        UserSystem.id == system_id,
        UserSystem.user_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    db_config = {
        'db_host': system.db_host,
        'db_port': system.db_port,
        'db_name': system.db_name,
        'db_username': system.db_username,
        'db_password': system.db_password,
        'connection_params': system.connection_params or {}
    }
    
    db_service = DatabaseService(db_config)
    schema = await db_service.get_table_schema()
    
    return {
        "system_id": system_id,
        "system_name": system.system_name,
        "schema": schema,
        "table_count": len(schema)
    }

@router.post("/{system_id}/test")
async def test_existing_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Test connection for an existing system"""
    system = db.query(UserSystem).filter(
        UserSystem.id == system_id,
        UserSystem.user_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    db_config = {
        'db_host': system.db_host,
        'db_port': system.db_port,
        'db_name': system.db_name,
        'db_username': system.db_username,
        'db_password': system.db_password,
        'connection_params': system.connection_params or {}
    }
    
    db_service = DatabaseService(db_config)
    result = await db_service.test_connection()
    
    return {
        "system_id": system_id,
        "system_name": system.system_name,
        **result
    }
