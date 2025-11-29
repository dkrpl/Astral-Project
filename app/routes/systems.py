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
    current_user: User = Depends(get_current_active_user)
):
    """Test database connection via BRIDGE"""
    try:
        # Validate bridge configuration
        if not test_config.connection_params.get('bridge_url'):
            raise HTTPException(status_code=400, detail="bridge_url is required")
        if not test_config.connection_params.get('bridge_api_key'):
            raise HTTPException(status_code=400, detail="bridge_api_key is required")
        
        db_config = {
            'system_type': test_config.system_type,
            'db_host': test_config.db_host,
            'db_port': test_config.db_port,
            'db_name': test_config.db_name,
            'db_username': test_config.db_username,
            'db_password': test_config.db_password,
            'connection_params': test_config.connection_params
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
    """Create system - BRIDGE REQUIRED"""
    
    # Validate bridge configuration
    if not system_data.connection_params.get('bridge_url'):
        raise HTTPException(status_code=400, detail="bridge_url is required in connection_params")
    if not system_data.connection_params.get('bridge_api_key'):
        raise HTTPException(status_code=400, detail="bridge_api_key is required in connection_params")
    
    # Test connection via bridge first
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
            detail=f"Bridge connection failed: {test_result.get('message')}"
        )
    
    # Create system - bridge configuration is stored
    db_system = UserSystem(
        user_id=current_user.id,
        system_name=system_data.system_name,
        system_type=system_data.system_type,
        db_host=system_data.db_host,
        db_port=system_data.db_port,
        db_name=system_data.db_name,
        db_username=system_data.db_username,
        db_password=system_data.db_password,
        connection_params=system_data.connection_params,  # Bridge config stored here
        table_mappings={},
        field_aliases={}, 
        business_rules={}
    )
    
    db.add(db_system)
    db.commit()
    db.refresh(db_system)
    
    logger.info(f"User {current_user.id} created bridge-enabled system: {system_data.system_name}")
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

@router.delete("/{system_id}")
async def delete_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete system"""
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
    """Get database schema via BRIDGE"""
    system = db.query(UserSystem).filter(
        UserSystem.id == system_id,
        UserSystem.user_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    db_config = {
        'system_type': system.system_type,
        'db_host': system.db_host,
        'db_port': system.db_port,
        'db_name': system.db_name,
        'db_username': system.db_username,
        'db_password': system.db_password,
        'connection_params': system.connection_params or {}
    }
    
    db_service = DatabaseService(db_config)
    schema_result = await db_service.get_table_schema()
    
    return {
        "system_id": system_id,
        "system_name": system.system_name,
        "schema_result": schema_result
    }

@router.post("/{system_id}/test")
async def test_existing_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Test existing system connection via BRIDGE"""
    system = db.query(UserSystem).filter(
        UserSystem.id == system_id,
        UserSystem.user_id == current_user.id
    ).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    db_config = {
        'system_type': system.system_type,
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