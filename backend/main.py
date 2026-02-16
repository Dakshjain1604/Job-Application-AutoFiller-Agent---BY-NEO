"""
FastAPI Backend for AutoCareer Application.
Orchestrates all modules and provides API endpoints.
"""

import os
import asyncio
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from database import get_db
from profile_engine import ProfileEngine
from scraper import JobScraper
from intelligence import IntelligenceEngine
from applier import ApplicationAutomation

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AutoCareer API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
profile_engine = ProfileEngine()
intelligence_engine = IntelligenceEngine()


# Request/Response Models
class SearchJobsRequest(BaseModel):
    keywords: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    max_jobs: int = 50


class AnalyzeJobRequest(BaseModel):
    profile_id: int = 1
    api_key: Optional[str] = None


class GenerateDraftRequest(BaseModel):
    profile_id: int = 1
    api_key: Optional[str] = None


class UpdateDraftRequest(BaseModel):
    cover_letter: Optional[str] = None
    custom_answers: Optional[str] = None
    status: Optional[str] = None


class SubmitApplicationRequest(BaseModel):
    profile_id: int = 1
    draft_id: Optional[int] = None
    dry_run: bool = True


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "AutoCareer API",
        "version": "1.0.0"
    }


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...), profile_id: Optional[int] = None):
    """
    Upload and parse resume PDF.
    Returns: profile_id and parsing results
    """
    try:
        # Save uploaded file temporarily
        temp_path = f"./backend/data/temp_resume_{profile_id or 'new'}.pdf"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Parse and ingest
        profile_id, vector_db_id = profile_engine.ingest_resume(temp_path, profile_id)
        
        # Get profile details
        db = get_db()
        profile = db.get_profile(profile_id)
        
        # Clean up temp file
        os.remove(temp_path)
        
        logger.info(f"Resume uploaded and parsed for profile {profile_id}")
        
        return {
            "success": True,
            "profile_id": profile_id,
            "vector_db_id": vector_db_id,
            "profile": {
                "name": profile['name'],
                "email": profile['email'],
                "skills": profile['skills'][:200] if profile['skills'] else None
            }
        }
        
    except Exception as e:
        logger.error(f"Resume upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search-jobs")
async def search_jobs(request: SearchJobsRequest, background_tasks: BackgroundTasks):
    """
    Search for jobs matching criteria.
    Returns: list of jobs found
    """
    try:
        salary_range = None
        if request.salary_min and request.salary_max:
            salary_range = (request.salary_min, request.salary_max)
        
        # Run scraper
        scraper = JobScraper()
        jobs = await scraper.search_jobs(
            keywords=request.keywords,
            salary_range=salary_range,
            max_jobs=request.max_jobs
        )
        
        logger.info(f"Job search completed: {len(jobs)} jobs found")
        
        return {
            "success": True,
            "count": len(jobs),
            "jobs": [
                {
                    "id": job.get('id'),
                    "title": job['title'],
                    "company": job['company'],
                    "location": job.get('location'),
                    "url": job['url'],
                    "source": job['source'],
                    "fit_score": job.get('fit_score')
                }
                for job in jobs
            ]
        }
        
    except Exception as e:
        logger.error(f"Job search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-job/{job_id}")
async def analyze_job(job_id: int, request: AnalyzeJobRequest):
    """
    Analyze job fit against resume.
    Returns: fit score and rationale
    """
    try:
        # Use provided API key or fall back to engine's default
        engine = IntelligenceEngine(api_key=request.api_key) if request.api_key else intelligence_engine
        result = engine.analyze_job(job_id, request.profile_id)
        
        logger.info(f"Job {job_id} analyzed: score {result['score']:.1f}")
        
        return {
            "success": True,
            "analysis": result
        }
        
    except Exception as e:
        logger.error(f"Job analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-draft/{job_id}")
async def generate_draft(job_id: int, request: GenerateDraftRequest):
    """
    Generate cover letter draft for job.
    Returns: draft content
    """
    try:
        # Use provided API key or fall back to engine's default
        engine = IntelligenceEngine(api_key=request.api_key) if request.api_key else intelligence_engine
        cover_letter = engine.generate_cover_letter(
            job_id, 
            request.profile_id
        )
        
        logger.info(f"Draft generated for job {job_id}")
        
        # Get draft from DB
        db = get_db()
        draft = db.get_draft_by_job(job_id)
        
        return {
            "success": True,
            "draft_id": draft['id'] if draft else None,
            "cover_letter": cover_letter
        }
        
    except Exception as e:
        logger.error(f"Draft generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/draft/{draft_id}")
async def update_draft(draft_id: int, request: UpdateDraftRequest):
    """
    Update draft content or status.
    Returns: success status
    """
    try:
        db = get_db()
        db.update_draft(
            draft_id=draft_id,
            cover_letter=request.cover_letter,
            custom_answers=request.custom_answers,
            status=request.status
        )
        
        logger.info(f"Draft {draft_id} updated")
        
        return {
            "success": True,
            "draft_id": draft_id
        }
        
    except Exception as e:
        logger.error(f"Draft update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/manage-queue")
async def manage_queue(status: str = "pending"):
    """
    Get application queue items.
    Returns: list of queued applications
    """
    try:
        db = get_db()
        queue_items = db.get_queue(status=status)
        
        return {
            "success": True,
            "count": len(queue_items),
            "queue": queue_items
        }
        
    except Exception as e:
        logger.error(f"Queue management error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit-application/{job_id}")
async def submit_application(job_id: int, request: SubmitApplicationRequest):
    """
    Submit job application (with dry run option).
    Returns: submission status
    """
    try:
        applier = ApplicationAutomation(dry_run=request.dry_run)
        result = await applier.apply_to_job(
            job_id=job_id,
            profile_id=request.profile_id,
            draft_id=request.draft_id
        )
        
        logger.info(f"Application submission result for job {job_id}: {result['status']}")
        
        return {
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Application submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def get_jobs(status: Optional[str] = None, limit: int = 50):
    """
    Get stored jobs with optional filtering.
    Returns: list of jobs with properly serialized URLs
    """
    try:
        db = get_db()
        jobs = db.get_jobs(status=status, limit=limit)
        
        # Ensure all jobs have valid URLs
        for job in jobs:
            if not job.get('url'):
                job['url'] = '#'  # Fallback for missing URLs
        
        return {
            "success": True,
            "count": len(jobs),
            "jobs": jobs
        }
        
    except Exception as e:
        logger.error(f"Get jobs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/application-logs")
async def get_application_logs(limit: int = 100):
    """
    Get application audit logs.
    Returns: list of log entries
    """
    try:
        db = get_db()
        logs = db.get_application_logs(limit=limit)
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Get logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/profile/{profile_id}")
async def get_profile(profile_id: int = 1):
    """
    Get user profile details.
    Returns: profile information
    """
    try:
        db = get_db()
        profile = db.get_profile(profile_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return {
            "success": True,
            "profile": profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting AutoCareer API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
