"""
models.py
---------
Shared Pydantic schemas (request/response) and SQLAlchemy ORM models
for the JobPulse platform.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum, Float,
    ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, relationship


# ═══════════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════════

class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    REMOTE = "remote"


class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class JobCategory(str, Enum):
    ENGINEERING = "Engineering"
    MARKETING = "Marketing"
    FINANCE = "Finance"
    HEALTHCARE = "Healthcare"
    DESIGN = "Design"
    DATA_SCIENCE = "Data Science"
    OPERATIONS = "Operations"
    SALES = "Sales"
    LEGAL = "Legal"
    HR = "Human Resources"
    EDUCATION = "Education"
    OTHER = "Other"


# ═══════════════════════════════════════════════════════════════════════
#  SQLAlchemy ORM
# ═══════════════════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    pass


class JobListing(Base):
    __tablename__ = "job_listings"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    title = Column(String(512), nullable=False)
    company = Column(String(256), nullable=False, index=True)
    location = Column(String(256), nullable=True)
    job_type = Column(SAEnum(JobType), nullable=True)
    experience_level = Column(SAEnum(ExperienceLevel), nullable=True)
    category = Column(SAEnum(JobCategory), nullable=True)
    salary_raw = Column(String(128), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    url = Column(String(1024), nullable=False)
    source = Column(String(64), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    classification_score = Column(Float, nullable=True)
    scraped_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source = Column(String(64), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    listings_scraped = Column(Integer, default=0)
    listings_new = Column(Integer, default=0)
    listings_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    success = Column(Boolean, default=True)


# ═══════════════════════════════════════════════════════════════════════
#  Pydantic Schemas
# ═══════════════════════════════════════════════════════════════════════

class JobListingBase(BaseModel):
    title: str = Field(..., max_length=512)
    company: str = Field(..., max_length=256)
    location: Optional[str] = Field(None, max_length=256)
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    category: Optional[JobCategory] = None
    salary_raw: Optional[str] = None
    description: Optional[str] = None
    url: str
    source: str


class JobListingCreate(JobListingBase):
    external_id: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    classification_score: Optional[float] = None


class JobListingRead(JobListingBase):
    id: UUID
    scraped_at: datetime
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class JobListingFilter(BaseModel):
    query: Optional[str] = None
    category: Optional[JobCategory] = None
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    source: Optional[str] = None
    location: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedJobListings(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[JobListingRead]
