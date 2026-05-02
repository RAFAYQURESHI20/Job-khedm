"""
backend/api/routes/jobs.py
--------------------------
CRUD and search endpoints for job listings.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.db import get_async_session
from backend.services.jobs_service import JobsService
from models import JobCategory, JobListingFilter, JobListingRead, JobType, PaginatedJobListings

router = APIRouter(prefix="/jobs")


@router.get("", response_model=PaginatedJobListings, summary="List & search job listings")
async def list_jobs(
    q: Optional[str] = Query(None, description="Full-text search query"),
    category: Optional[JobCategory] = None,
    job_type: Optional[JobType] = None,
    location: Optional[str] = None,
    source: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    filters = JobListingFilter(
        query=q,
        category=category,
        job_type=job_type,
        location=location,
        source=source,
        page=page,
        page_size=page_size,
    )
    svc = JobsService(session)
    return await svc.search(filters)


@router.get("/{job_id}", response_model=JobListingRead, summary="Get a single job listing")
async def get_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    svc = JobsService(session)
    job = await svc.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
