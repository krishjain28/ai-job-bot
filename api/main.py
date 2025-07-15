from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime

from database.connection import db_manager
from database.models import Job, Application, JobRun
from main import run as run_job_bot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Job Bot API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    link: str
    location: str
    salary: str
    tags: List[str]
    source: str
    gpt_score: Optional[int]
    gpt_reason: Optional[str]
    created_at: datetime

class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    status: str
    message: str
    timestamp: datetime
    response_received: bool
    response_date: Optional[datetime]

class JobRunResponse(BaseModel):
    id: str
    start_time: datetime
    end_time: Optional[datetime]
    jobs_found: int
    jobs_filtered: int
    applications_sent: int
    errors: List[str]
    status: str

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        db_manager.connect()
        logger.info("API started successfully")
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    db_manager.disconnect()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "AI Job Bot API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    db_healthy = db_manager.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.utcnow()
    }

@app.get("/jobs", response_model=List[JobResponse])
async def get_jobs(limit: int = 50, offset: int = 0):
    """Get recent jobs"""
    try:
        jobs_collection = db_manager.get_collection("jobs")
        jobs = list(jobs_collection.find().sort("created_at", -1).skip(offset).limit(limit))
        
        return [JobResponse(**job) for job in jobs]
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch jobs")

@app.get("/applications", response_model=List[ApplicationResponse])
async def get_applications(limit: int = 50, offset: int = 0):
    """Get recent applications"""
    try:
        applications_collection = db_manager.get_collection("applications")
        applications = list(applications_collection.find().sort("timestamp", -1).skip(offset).limit(limit))
        
        return [ApplicationResponse(**application) for application in applications]
    except Exception as e:
        logger.error(f"Error fetching applications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch applications")

@app.get("/runs", response_model=List[JobRunResponse])
async def get_runs(limit: int = 10):
    """Get recent job runs"""
    try:
        runs_collection = db_manager.get_collection("runs")
        runs = list(runs_collection.find().sort("start_time", -1).limit(limit))
        
        return [JobRunResponse(**run) for run in runs]
    except Exception as e:
        logger.error(f"Error fetching runs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch runs")

@app.post("/run")
async def trigger_job_run(background_tasks: BackgroundTasks):
    """Trigger a new job application run"""
    try:
        # Add job run to background tasks
        background_tasks.add_task(run_job_bot)
        
        return {"message": "Job run started in background", "status": "queued"}
    except Exception as e:
        logger.error(f"Error triggering job run: {e}")
        raise HTTPException(status_code=500, detail="Failed to start job run")

@app.get("/stats")
async def get_stats():
    """Get application statistics"""
    try:
        jobs_collection = db_manager.get_collection("jobs")
        applications_collection = db_manager.get_collection("applications")
        runs_collection = db_manager.get_collection("runs")
        
        total_jobs = jobs_collection.count_documents({})
        total_applications = applications_collection.count_documents({})
        successful_applications = applications_collection.count_documents({"status": "applied"})
        
        # Get recent run stats
        recent_run = runs_collection.find_one(sort=[("start_time", -1)])
        
        return {
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "successful_applications": successful_applications,
            "success_rate": (successful_applications / total_applications * 100) if total_applications > 0 else 0,
            "last_run": recent_run.get("start_time") if recent_run else None,
            "last_run_status": recent_run.get("status") if recent_run else None
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics") 