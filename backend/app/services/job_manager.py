"""Job management system for progressive test generation."""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from loguru import logger

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SectionStatus(str, Enum):
    WAITING = "waiting"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class SectionProgress:
    section_type: str
    status: SectionStatus
    section_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: int = 0
    progress_message: str = "Waiting"
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetime objects to ISO strings for JSON serialization
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data

@dataclass
class TestGenerationJob:
    job_id: str
    status: JobStatus
    request_data: Dict[str, Any]
    sections: Dict[str, SectionProgress]
    created_at: datetime
    updated_at: datetime
    completed_sections: int = 0
    total_sections: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "request_data": self.request_data,
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_sections": self.completed_sections,
            "total_sections": self.total_sections,
            "error": self.error,
            "progress_percentage": int((self.completed_sections / max(self.total_sections, 1)) * 100)
        }

class JobManager:
    """In-memory job manager for progressive test generation."""
    
    def __init__(self):
        self.jobs: Dict[str, TestGenerationJob] = {}
        self.cleanup_interval = 3600  # Clean up jobs older than 1 hour
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_old_jobs())
    
    async def _cleanup_old_jobs(self):
        """Clean up old completed/failed jobs periodically."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                jobs_to_remove = []
                for job_id, job in self.jobs.items():
                    if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] 
                        and job.updated_at < cutoff_time):
                        jobs_to_remove.append(job_id)
                
                for job_id in jobs_to_remove:
                    del self.jobs[job_id]
                    logger.info(f"Cleaned up old job: {job_id}")
                    
            except Exception as e:
                logger.error(f"Error in job cleanup: {e}")
    
    def create_job(self, request_data: Dict[str, Any]) -> str:
        """Create a new test generation job."""
        job_id = str(uuid.uuid4())
        
        # Initialize section progress
        include_sections = request_data.get('include_sections', [])
        sections = {}
        for section_type in include_sections:
            sections[section_type] = SectionProgress(
                section_type=section_type,
                status=SectionStatus.WAITING
            )
        
        job = TestGenerationJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            request_data=request_data,
            sections=sections,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            total_sections=len(include_sections)
        )
        
        self.jobs[job_id] = job
        logger.info(f"Created job {job_id} with {len(include_sections)} sections")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[TestGenerationJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    def update_job_status(self, job_id: str, status: JobStatus, error: Optional[str] = None):
        """Update overall job status."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = status
            job.updated_at = datetime.utcnow()
            if error:
                job.error = error
            logger.info(f"Updated job {job_id} status to {status}")
    
    def start_section(self, job_id: str, section_type: str):
        """Mark a section as started."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if section_type in job.sections:
                job.sections[section_type].status = SectionStatus.GENERATING
                job.sections[section_type].started_at = datetime.utcnow()
                job.sections[section_type].progress_percentage = 0
                job.sections[section_type].progress_message = "Starting generation..."
                job.updated_at = datetime.utcnow()
                logger.info(f"Started section {section_type} for job {job_id}")
    
    def update_section_progress(self, job_id: str, section_type: str, progress_percentage: int, message: str = ""):
        """Update progress within a section."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if section_type in job.sections:
                job.sections[section_type].progress_percentage = progress_percentage
                job.sections[section_type].progress_message = message
                job.updated_at = datetime.utcnow()
                logger.debug(f"Updated progress for {section_type} in job {job_id}: {progress_percentage}% - {message}")
    
    def complete_section(self, job_id: str, section_type: str, section_data: Dict[str, Any]):
        """Mark a section as completed with its data."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if section_type in job.sections:
                job.sections[section_type].status = SectionStatus.COMPLETED
                job.sections[section_type].section_data = section_data
                job.sections[section_type].completed_at = datetime.utcnow()
                job.sections[section_type].progress_percentage = 100
                job.sections[section_type].progress_message = "Complete"
                job.completed_sections = sum(1 for s in job.sections.values() 
                                           if s.status == SectionStatus.COMPLETED)
                job.updated_at = datetime.utcnow()
                
                # Check if all sections are complete
                if job.completed_sections == job.total_sections:
                    job.status = JobStatus.COMPLETED
                
                logger.info(f"Completed section {section_type} for job {job_id} "
                           f"({job.completed_sections}/{job.total_sections})")
    
    def fail_section(self, job_id: str, section_type: str, error: str):
        """Mark a section as failed."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if section_type in job.sections:
                job.sections[section_type].status = SectionStatus.FAILED
                job.sections[section_type].error = error
                job.updated_at = datetime.utcnow()
                logger.error(f"Failed section {section_type} for job {job_id}: {error}")
    
    def get_completed_sections(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all completed sections for a job."""
        if job_id not in self.jobs:
            return []
        
        job = self.jobs[job_id]
        completed_sections = []
        
        for section_progress in job.sections.values():
            if (section_progress.status == SectionStatus.COMPLETED 
                and section_progress.section_data):
                completed_sections.append(section_progress.section_data)
        
        return completed_sections
    

# Global job manager instance
job_manager = JobManager()