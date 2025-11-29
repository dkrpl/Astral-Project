from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_router, users_router, systems_router, chat_router, admin_router
from app.database import engine, Base
from app.utils.helpers import setup_logging
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created successfully")
except Exception as e:
    logger.error(f"❌ Error creating database tables: {e}")

app = FastAPI(
    title="Astral Project API",
    description="AI Assistant for Multiple Database Systems - Enhanced Version",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS middleware
from app.config import settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(systems_router, prefix="/systems", tags=["Systems"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

@app.get("/")
async def root():
    return {
        "message": "🚀 Welcome to Astral Project API v2.0",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "features": [
            "Multi-database support",
            "AI-powered SQL generation", 
            "Real-time chat",
            "Admin dashboard",
            "Enhanced error handling"
        ]
    }

@app.get("/health")
async def health_check():
    """Enhanced health check dengan database connection test"""
    try:
        # Test database connection
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected", 
            "ai_service": "ready",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "database": "error",
            "ai_service": "ready", 
            "error": str(e)
        }

@app.get("/info")
async def system_info():
    """System information endpoint"""
    return {
        "name": "Astral AI",
        "version": "2.0.0",
        "description": "AI-powered database assistant",
        "supported_databases": ["MySQL", "PostgreSQL", "SQL Server"],
        "features": [
            "Natural language to SQL",
            "Multi-database support", 
            "Real-time chat interface",
            "Admin monitoring",
            "User management"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )