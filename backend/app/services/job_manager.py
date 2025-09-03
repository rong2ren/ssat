"""Job management system for progressive test generation."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from loguru import logger
import threading

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some sections succeeded, some failed
    CANCELLED = "cancelled"

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
    user_id: Optional[str] = None
    
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
        self._cleanup_started = False
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if not self._cleanup_started:
            try:
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(self._cleanup_old_jobs())
                    self._cleanup_started = True
            except RuntimeError:
                # No event loop running yet, cleanup will be started later
                logger.debug("No event loop running, cleanup task will be started on first use")
                pass
    
    async def _cleanup_old_jobs(self):
        """Clean up old completed/failed jobs periodically."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                jobs_to_remove = []
                for job_id, job in self.jobs.items():
                    if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL, JobStatus.CANCELLED] 
                        and job.updated_at < cutoff_time):
                        jobs_to_remove.append(job_id)
                
                for job_id in jobs_to_remove:
                    del self.jobs[job_id]
                    logger.info(f"Cleaned up old job: {job_id}")
                    
            except Exception as e:
                logger.error(f"Error in job cleanup: {e}")
    
    def create_job(self, request_data: Dict[str, Any], user_id: Optional[str] = None) -> str:
        """Create a new test generation job."""
        # Start cleanup task if not already started
        self._start_cleanup_task()
        
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
            total_sections=len(include_sections),
            user_id=user_id
        )
        
        self.jobs[job_id] = job
        logger.info(f"Created job {job_id} with {len(include_sections)} sections for user {user_id}")
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
            
            # When job status becomes RUNNING, set all sections to generating
            if status == JobStatus.RUNNING:
                for section_type in job.sections:
                    if job.sections[section_type].status == SectionStatus.WAITING:
                        job.sections[section_type].status = SectionStatus.GENERATING
                        job.sections[section_type].started_at = datetime.utcnow()
                        job.sections[section_type].progress_percentage = 0
                        job.sections[section_type].progress_message = "Starting generation..."
                logger.info(f"Set all sections to generating for job {job_id}")
    
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
                
                # Check if job is finished (all sections done)
                if self._is_job_finished(job_id):
                    final_status = self._determine_final_job_status(job_id)
                    job.status = final_status
                    logger.info(f"Job {job_id} finished with status: {final_status}")
                
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
                
                # Check if job is finished (all sections done)
                if self._is_job_finished(job_id):
                    final_status = self._determine_final_job_status(job_id)
                    job.status = final_status
                    logger.info(f"Job {job_id} finished with status: {final_status}")
                
                logger.error(f"Failed section {section_type} for job {job_id}: {error}")
    
    def _is_job_finished(self, job_id: str) -> bool:
        """Check if all sections are done (completed or failed)."""
        job = self.jobs[job_id]
        finished_sections = sum(1 for s in job.sections.values() 
                              if s.status in [SectionStatus.COMPLETED, SectionStatus.FAILED])
        return finished_sections == job.total_sections

    def _determine_final_job_status(self, job_id: str) -> JobStatus:
        """Determine final job status when all sections are done."""
        job = self.jobs[job_id]
        
        completed_count = sum(1 for s in job.sections.values() 
                             if s.status == SectionStatus.COMPLETED)
        failed_count = sum(1 for s in job.sections.values() 
                          if s.status == SectionStatus.FAILED)
        total_sections = job.total_sections
        
        if completed_count == total_sections:
            return JobStatus.COMPLETED
        elif failed_count == total_sections:
            return JobStatus.FAILED
        else:
            return JobStatus.PARTIAL

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
    
    def get_job_status(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get job status with user authorization."""
        logger.info(f"🔍 DEBUG: Getting job status for job_id={job_id}, user_id={user_id} (type: {type(user_id)}) in JobManager instance {id(self)}")
        
        job = self.jobs.get(job_id)
        if not job:
            logger.warning(f"🔍 DEBUG: Job {job_id} not found in job manager instance {id(self)}")
            return None
        
        logger.info(f"🔍 DEBUG: Found job {job_id}, job.user_id={job.user_id} (type: {type(job.user_id)}), requesting user_id={user_id} (type: {type(user_id)})")
        
        # Check if user is authorized to access this job
        if job.user_id and job.user_id != user_id:
            logger.warning(f"User {user_id} attempted to access job {job_id} owned by user {job.user_id}")
            logger.warning(f"🔍 DEBUG: Authorization failed - job.user_id != user_id: {job.user_id} != {user_id}")
            return None
        
        logger.info(f"🔍 DEBUG: User {user_id} authorized to access job {job_id}")
        
        # Get completed sections in the proper format
        completed_sections = self.get_completed_sections(job_id)
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "progress": {
                "completed": job.completed_sections,
                "total": job.total_sections,
                "percentage": int((job.completed_sections / max(job.total_sections, 1)) * 100)
            },
            "sections": completed_sections,
            "section_details": {k: v.to_dict() for k, v in job.sections.items()},
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }

# Thread-safe singleton implementation
_job_manager_instance: Optional[JobManager] = None
_job_manager_lock = threading.Lock()

def get_job_manager() -> JobManager:
    """Get the global singleton instance of JobManager (thread-safe)."""
    global _job_manager_instance
    if _job_manager_instance is None:
        with _job_manager_lock:
            # Double-check pattern to prevent race conditions
            if _job_manager_instance is None:
                _job_manager_instance = JobManager()
    return _job_manager_instance

# Export the instance for backward compatibility
job_manager = get_job_manager()