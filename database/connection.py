from pymongo import MongoClient
import logging
from typing import Dict, List, Optional
from datetime import datetime
from config import MONGODB_URI

logger = logging.getLogger(__name__)

class DatabaseManager:
    """MongoDB database manager for AI Job Bot"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            if not MONGODB_URI:
                logger.warning("MongoDB URI not configured")
                return False
                
            self.client = MongoClient(MONGODB_URI)
            self.db = self.client['ai_job_bot']
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            return False
    
    def insert_job(self, job: Dict) -> bool:
        """Insert a job into the database"""
        try:
            if not self.db:
                return False
                
            # Add timestamp
            job['created_at'] = datetime.now()
            
            # Check if job already exists
            existing = self.db.jobs.find_one({
                'title': job['title'],
                'company': job['company'],
                'link': job['link']
            })
            
            if existing:
                logger.info(f"Job already exists: {job['title']} at {job['company']}")
                return True
            
            result = self.db.jobs.insert_one(job)
            logger.info(f"Inserted job: {job['title']} at {job['company']}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting job: {e}")
            return False
    
    def insert_application(self, application: Dict) -> bool:
        """Insert an application record"""
        try:
            if not self.db:
                return False
                
            # Add timestamp
            application['created_at'] = datetime.now()
            
            result = self.db.applications.insert_one(application)
            logger.info(f"Inserted application: {application.get('job_title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting application: {e}")
            return False
    
    def get_jobs(self, limit: int = 100) -> List[Dict]:
        """Get recent jobs"""
        try:
            if not self.db:
                return []
                
            jobs = list(self.db.jobs.find().sort('created_at', -1).limit(limit))
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting jobs: {e}")
            return []
    
    def get_applications(self, limit: int = 100) -> List[Dict]:
        """Get recent applications"""
        try:
            if not self.db:
                return []
                
            applications = list(self.db.applications.find().sort('created_at', -1).limit(limit))
            return applications
            
        except Exception as e:
            logger.error(f"Error getting applications: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get application statistics"""
        try:
            if not self.db:
                return {}
                
            total_jobs = self.db.jobs.count_documents({})
            total_applications = self.db.applications.count_documents({})
            
            # Get applications by status
            status_counts = {}
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            
            for doc in self.db.applications.aggregate(pipeline):
                status_counts[doc['_id']] = doc['count']
            
            # Get recent activity
            recent_applications = self.db.applications.count_documents({
                'created_at': {'$gte': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            return {
                'total_jobs': total_jobs,
                'total_applications': total_applications,
                'status_counts': status_counts,
                'applications_today': recent_applications
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Global database manager instance
db_manager = DatabaseManager() 