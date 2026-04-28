from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging

from backend.routes import chat, graph, review, models
from backend.config import DATABASE_URL, NEO4J_URI
from backend.database.session import init_db, engine
from backend.graph_db.neo4j_client import init_neo4j
from backend.scheduler import init_scheduler, shutdown_scheduler, schedule_periodic_scans, schedule_startup_catchup_scan
from backend.scheduler.config import scheduler
# Import models to register with SQLAlchemy Base
from backend.database import model

app = FastAPI(
    title="AI Chatbox API",
    description="Backend for AI chatbox with knowledge graph and review system",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(graph.router, prefix="/api", tags=["graph"])
app.include_router(review.router, prefix="/api", tags=["review"])
app.include_router(models.router, prefix="/api", tags=["models"])

@app.on_event("startup")
async def startup_event():
    """Initialize databases on startup"""
    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Set root logger level
    logging.getLogger().setLevel(numeric_level)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting AI Chatbox API with log level: {log_level}")

    print("Initializing databases...")
    init_db()
    init_neo4j()
    print(f"SQL Database URL: {DATABASE_URL}")
    print(f"Neo4j URI: {NEO4J_URI}")
    print("Databases initialized.")

    # Initialize scheduler for background review generation
    print("Initializing scheduler...")
    try:
        init_scheduler()
        schedule_periodic_scans()
        schedule_startup_catchup_scan()
        print("Scheduler initialized and periodic scans scheduled")
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")
        print(f"Warning: Scheduler initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger = logging.getLogger(__name__)
    logger.info("Shutting down AI Chatbox API...")

    # Shutdown scheduler
    try:
        shutdown_scheduler()
        logger.info("Scheduler shutdown completed")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")

@app.get("/")
async def root():
    return {"message": "AI Chatbox API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-chatbox-api"}

@app.get("/health/scheduler")
async def scheduler_health_check():
    """Check scheduler status"""
    if scheduler.running:
        jobs = scheduler.get_jobs()
        return {
            "status": "running",
            "job_count": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                for job in jobs[:10]  # Limit to first 10 jobs
            ]
        }
    else:
        return {"status": "stopped", "job_count": 0, "jobs": []}

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )