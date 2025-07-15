from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class Job:
    """Job data model"""
    title: str
    company: str
    link: str
    location: str = "Remote"
    salary: str = ""
    description: str = ""
    tags: List[str] = None
    source: str = "unknown"
    gpt_score: Optional[int] = None
    gpt_reason: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class Application:
    """Application data model"""
    job_title: str
    company: str
    job_link: str
    status: str = "applied"
    message: str = ""
    gpt_score: Optional[int] = None
    source: str = "unknown"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class RunHistory:
    """Run history data model"""
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    jobs_found: int = 0
    jobs_filtered: int = 0
    applications_sent: int = 0
    errors: List[str] = None
    status: str = "running"
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

def job_from_dict(data: Dict) -> Job:
    """Create Job object from dictionary"""
    return Job(
        title=data.get('title', ''),
        company=data.get('company', ''),
        link=data.get('link', ''),
        location=data.get('location', 'Remote'),
        salary=data.get('salary', ''),
        description=data.get('description', ''),
        tags=data.get('tags', []),
        source=data.get('source', 'unknown'),
        gpt_score=data.get('gpt_score'),
        gpt_reason=data.get('gpt_reason', ''),
        created_at=data.get('created_at')
    )

def application_from_dict(data: Dict) -> Application:
    """Create Application object from dictionary"""
    return Application(
        job_title=data.get('job_title', ''),
        company=data.get('company', ''),
        job_link=data.get('job_link', ''),
        status=data.get('status', 'applied'),
        message=data.get('message', ''),
        gpt_score=data.get('gpt_score'),
        source=data.get('source', 'unknown'),
        created_at=data.get('created_at')
    ) 