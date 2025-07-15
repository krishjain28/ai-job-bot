import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import PyMongoError, DuplicateKeyError
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class IndexType(Enum):
    """Index types"""
    SINGLE = "single"
    COMPOUND = "compound"
    TEXT = "text"
    UNIQUE = "unique"

@dataclass
class IndexInfo:
    """Index information"""
    name: str
    fields: List[Tuple[str, int]]
    type: IndexType
    created_at: float
    size_bytes: Optional[int] = None
    usage_count: int = 0

@dataclass
class BulkOperation:
    """Bulk operation information"""
    operation_type: str
    collection: str
    data: List[Dict[str, Any]]
    timestamp: float
    batch_size: int = 0

@dataclass
class PerformanceMetric:
    """Database performance metric"""
    operation: str
    duration: float
    timestamp: float
    collection: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)

class DatabaseOptimizer:
    """Database performance optimization and monitoring"""
    
    def __init__(self, db_client: MongoClient):
        self.db_client = db_client
        self.db = db_client.get_database()
        self.performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.indexes: Dict[str, List[IndexInfo]] = defaultdict(list)
        self.bulk_operations: List[BulkOperation] = []
        self.connection_pool_stats = {}
        self.initialize_indexes()
        self.initialize_connection_pool()
    
    def initialize_connection_pool(self):
        """Initialize connection pool settings"""
        # Configure connection pool
        self.db_client.max_pool_size = 50
        self.db_client.min_pool_size = 10
        self.db_client.max_idle_time_ms = 30000
        self.db_client.wait_queue_timeout_ms = 5000
        self.db_client.server_selection_timeout_ms = 5000
        
        logger.info("Database connection pool initialized")
    
    def initialize_indexes(self):
        """Initialize database indexes for optimal performance"""
        
        # Jobs collection indexes
        jobs_collection = self.db['jobs']
        
        # Create indexes for jobs collection
        self._create_index_if_not_exists(
            jobs_collection,
            'job_hash_unique',
            [('job_hash', ASCENDING)],
            IndexType.UNIQUE
        )
        
        self._create_index_if_not_exists(
            jobs_collection,
            'source_created_at',
            [('source', ASCENDING), ('created_at', DESCENDING)],
            IndexType.COMPOUND
        )
        
        self._create_index_if_not_exists(
            jobs_collection,
            'title_text',
            [('title', TEXT)],
            IndexType.TEXT
        )
        
        self._create_index_if_not_exists(
            jobs_collection,
            'company_location',
            [('company', ASCENDING), ('location', ASCENDING)],
            IndexType.COMPOUND
        )
        
        self._create_index_if_not_exists(
            jobs_collection,
            'status_created_at',
            [('status', ASCENDING), ('created_at', DESCENDING)],
            IndexType.COMPOUND
        )
        
        # Applications collection indexes
        applications_collection = self.db['applications']
        
        self._create_index_if_not_exists(
            applications_collection,
            'job_id_status',
            [('job_id', ASCENDING), ('status', ASCENDING)],
            IndexType.COMPOUND
        )
        
        self._create_index_if_not_exists(
            applications_collection,
            'applied_at',
            [('applied_at', DESCENDING)],
            IndexType.SINGLE
        )
        
        self._create_index_if_not_exists(
            applications_collection,
            'user_id_applied_at',
            [('user_id', ASCENDING), ('applied_at', DESCENDING)],
            IndexType.COMPOUND
        )
        
        # Users collection indexes
        users_collection = self.db['users']
        
        self._create_index_if_not_exists(
            users_collection,
            'email_unique',
            [('email', ASCENDING)],
            IndexType.UNIQUE
        )
        
        # Metrics collection indexes
        metrics_collection = self.db['metrics']
        
        self._create_index_if_not_exists(
            metrics_collection,
            'timestamp',
            [('timestamp', DESCENDING)],
            IndexType.SINGLE
        )
        
        self._create_index_if_not_exists(
            metrics_collection,
            'name_timestamp',
            [('name', ASCENDING), ('timestamp', DESCENDING)],
            IndexType.COMPOUND
        )
        
        logger.info("Database indexes initialized")
    
    def _create_index_if_not_exists(self, collection, index_name: str, fields: List[Tuple[str, int]], index_type: IndexType):
        """Create index if it doesn't exist"""
        try:
            # Check if index already exists
            existing_indexes = collection.list_indexes()
            index_exists = any(index['name'] == index_name for index in existing_indexes)
            
            if not index_exists:
                if index_type == IndexType.UNIQUE:
                    collection.create_index(fields, name=index_name, unique=True)
                elif index_type == IndexType.TEXT:
                    collection.create_index(fields, name=index_name)
                else:
                    collection.create_index(fields, name=index_name)
                
                logger.info(f"Created index {index_name} on {collection.name}")
                
                # Record index info
                index_info = IndexInfo(
                    name=index_name,
                    fields=fields,
                    type=index_type,
                    created_at=time.time()
                )
                self.indexes[collection.name].append(index_info)
            else:
                logger.debug(f"Index {index_name} already exists on {collection.name}")
                
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
    
    async def bulk_insert_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk insert jobs with performance optimization"""
        if not jobs:
            return {'inserted': 0, 'errors': 0, 'duration': 0}
        
        start_time = time.time()
        collection = self.db['jobs']
        
        # Prepare jobs for bulk insert
        prepared_jobs = []
        for job in jobs:
            # Add timestamps
            job['created_at'] = datetime.utcnow()
            job['updated_at'] = datetime.utcnow()
            
            # Generate job hash for deduplication
            if 'job_hash' not in job:
                job['job_hash'] = self._generate_job_hash(job)
            
            prepared_jobs.append(job)
        
        # Perform bulk insert
        try:
            result = collection.insert_many(prepared_jobs, ordered=False)
            duration = time.time() - start_time
            
            # Record performance metric
            self._record_performance_metric(
                'bulk_insert_jobs',
                duration,
                'jobs',
                True,
                {'inserted_count': len(result.inserted_ids), 'batch_size': len(jobs)}
            )
            
            # Record bulk operation
            bulk_op = BulkOperation(
                operation_type='insert_many',
                collection='jobs',
                data=prepared_jobs,
                timestamp=time.time(),
                batch_size=len(jobs)
            )
            self.bulk_operations.append(bulk_op)
            
            logger.info(f"Bulk inserted {len(result.inserted_ids)} jobs in {duration:.2f}s")
            
            return {
                'inserted': len(result.inserted_ids),
                'errors': 0,
                'duration': duration
            }
            
        except DuplicateKeyError as e:
            # Handle duplicate key errors gracefully
            duration = time.time() - start_time
            
            self._record_performance_metric(
                'bulk_insert_jobs',
                duration,
                'jobs',
                False,
                {'error': 'duplicate_key', 'batch_size': len(jobs)}
            )
            
            logger.warning(f"Duplicate jobs detected during bulk insert: {e}")
            return {
                'inserted': 0,
                'errors': len(jobs),
                'duration': duration,
                'error': 'duplicate_key'
            }
            
        except Exception as e:
            duration = time.time() - start_time
            
            self._record_performance_metric(
                'bulk_insert_jobs',
                duration,
                'jobs',
                False,
                {'error': str(e), 'batch_size': len(jobs)}
            )
            
            logger.error(f"Bulk insert failed: {e}")
            return {
                'inserted': 0,
                'errors': len(jobs),
                'duration': duration,
                'error': str(e)
            }
    
    async def bulk_insert_applications(self, applications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk insert applications with performance optimization"""
        if not applications:
            return {'inserted': 0, 'errors': 0, 'duration': 0}
        
        start_time = time.time()
        collection = self.db['applications']
        
        # Prepare applications for bulk insert
        prepared_applications = []
        for app in applications:
            # Add timestamps
            app['created_at'] = datetime.utcnow()
            app['updated_at'] = datetime.utcnow()
            
            # Ensure required fields
            if 'applied_at' not in app:
                app['applied_at'] = datetime.utcnow()
            
            prepared_applications.append(app)
        
        # Perform bulk insert
        try:
            result = collection.insert_many(prepared_applications, ordered=False)
            duration = time.time() - start_time
            
            # Record performance metric
            self._record_performance_metric(
                'bulk_insert_applications',
                duration,
                'applications',
                True,
                {'inserted_count': len(result.inserted_ids), 'batch_size': len(applications)}
            )
            
            # Record bulk operation
            bulk_op = BulkOperation(
                operation_type='insert_many',
                collection='applications',
                data=prepared_applications,
                timestamp=time.time(),
                batch_size=len(applications)
            )
            self.bulk_operations.append(bulk_op)
            
            logger.info(f"Bulk inserted {len(result.inserted_ids)} applications in {duration:.2f}s")
            
            return {
                'inserted': len(result.inserted_ids),
                'errors': 0,
                'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            
            self._record_performance_metric(
                'bulk_insert_applications',
                duration,
                'applications',
                False,
                {'error': str(e), 'batch_size': len(applications)}
            )
            
            logger.error(f"Bulk insert applications failed: {e}")
            return {
                'inserted': 0,
                'errors': len(applications),
                'duration': duration,
                'error': str(e)
            }
    
    async def bulk_update_jobs(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk update jobs with performance optimization"""
        if not updates:
            return {'updated': 0, 'errors': 0, 'duration': 0}
        
        start_time = time.time()
        collection = self.db['jobs']
        
        # Prepare bulk operations
        bulk_operations = []
        for update in updates:
            filter_criteria = update.get('filter', {})
            update_data = update.get('update', {})
            
            # Add timestamp
            update_data['$set'] = update_data.get('$set', {})
            update_data['$set']['updated_at'] = datetime.utcnow()
            
            bulk_operations.append({
                'updateOne': {
                    'filter': filter_criteria,
                    'update': update_data,
                    'upsert': update.get('upsert', False)
                }
            })
        
        # Perform bulk operations
        try:
            result = collection.bulk_write(bulk_operations, ordered=False)
            duration = time.time() - start_time
            
            # Record performance metric
            self._record_performance_metric(
                'bulk_update_jobs',
                duration,
                'jobs',
                True,
                {
                    'modified_count': result.modified_count,
                    'upserted_count': result.upserted_count,
                    'batch_size': len(updates)
                }
            )
            
            logger.info(f"Bulk updated {result.modified_count} jobs in {duration:.2f}s")
            
            return {
                'updated': result.modified_count,
                'upserted': result.upserted_count,
                'errors': 0,
                'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            
            self._record_performance_metric(
                'bulk_update_jobs',
                duration,
                'jobs',
                False,
                {'error': str(e), 'batch_size': len(updates)}
            )
            
            logger.error(f"Bulk update jobs failed: {e}")
            return {
                'updated': 0,
                'upserted': 0,
                'errors': len(updates),
                'duration': duration,
                'error': str(e)
            }
    
    def _generate_job_hash(self, job: Dict[str, Any]) -> str:
        """Generate hash for job deduplication"""
        import hashlib
        
        # Create normalized version for hashing
        normalized_data = {
            'title': job.get('title', '').lower().strip(),
            'company': job.get('company', '').lower().strip(),
            'source': job.get('source', '').lower().strip(),
            'location': job.get('location', '').lower().strip()
        }
        
        # Sort keys for consistent hashing
        sorted_data = json.dumps(normalized_data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def _record_performance_metric(self, operation: str, duration: float, collection: str, success: bool, details: Dict[str, Any] = None):
        """Record performance metric"""
        if details is None:
            details = {}
        
        metric = PerformanceMetric(
            operation=operation,
            duration=duration,
            timestamp=time.time(),
            collection=collection,
            success=success,
            details=details
        )
        
        self.performance_metrics[operation].append(metric)
    
    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        try:
            # Get connection pool stats from MongoDB
            stats = self.db_client.admin.command('serverStatus')
            connections = stats.get('connections', {})
            
            self.connection_pool_stats = {
                'current': connections.get('current', 0),
                'available': connections.get('available', 0),
                'pending': connections.get('pending', 0),
                'active': connections.get('active', 0),
                'max_pool_size': self.db_client.max_pool_size,
                'min_pool_size': self.db_client.min_pool_size
            }
            
            return self.connection_pool_stats
            
        except Exception as e:
            logger.error(f"Failed to get connection pool stats: {e}")
            return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        summary = {}
        
        for operation, metrics_queue in self.performance_metrics.items():
            if not metrics_queue:
                continue
            
            metrics = list(metrics_queue)
            durations = [m.duration for m in metrics]
            success_count = sum(1 for m in metrics if m.success)
            error_count = len(metrics) - success_count
            
            summary[operation] = {
                'total_operations': len(metrics),
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': success_count / len(metrics) if metrics else 0,
                'avg_duration': statistics.mean(durations) if durations else 0,
                'min_duration': min(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'recent_avg_duration': statistics.mean(durations[-10:]) if len(durations) >= 10 else statistics.mean(durations) if durations else 0
            }
        
        return summary
    
    def get_index_performance(self) -> Dict[str, Any]:
        """Get index performance information"""
        summary = {}
        
        for collection_name, indexes in self.indexes.items():
            collection = self.db[collection_name]
            
            try:
                # Get index stats from MongoDB
                index_stats = collection.aggregate([
                    {'$indexStats': {}}
                ])
                
                collection_summary = []
                for index_stat in index_stats:
                    index_name = index_stat.get('name', 'unknown')
                    
                    # Find corresponding index info
                    index_info = next((idx for idx in indexes if idx.name == index_name), None)
                    
                    collection_summary.append({
                        'name': index_name,
                        'type': index_info.type.value if index_info else 'unknown',
                        'accesses': index_stat.get('accesses', {}),
                        'size': index_stat.get('spec', {}).get('size', 0),
                        'usage_count': index_stat.get('accesses', {}).get('ops', 0)
                    })
                
                summary[collection_name] = collection_summary
                
            except Exception as e:
                logger.error(f"Failed to get index stats for {collection_name}: {e}")
                summary[collection_name] = []
        
        return summary
    
    def get_bulk_operations_summary(self) -> Dict[str, Any]:
        """Get bulk operations summary"""
        if not self.bulk_operations:
            return {'total_operations': 0, 'recent_operations': []}
        
        total_operations = len(self.bulk_operations)
        total_batch_size = sum(op.batch_size for op in self.bulk_operations)
        
        # Recent operations (last 24 hours)
        cutoff_time = time.time() - 86400
        recent_operations = [
            {
                'type': op.operation_type,
                'collection': op.collection,
                'batch_size': op.batch_size,
                'timestamp': op.timestamp
            }
            for op in self.bulk_operations if op.timestamp > cutoff_time
        ]
        
        return {
            'total_operations': total_operations,
            'total_batch_size': total_batch_size,
            'avg_batch_size': total_batch_size / total_operations if total_operations > 0 else 0,
            'recent_operations_24h': len(recent_operations),
            'recent_operations': recent_operations[-10:]  # Last 10 operations
        }
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            # Get database stats
            db_stats = self.db.command('dbStats')
            
            # Get collection stats
            collections_stats = {}
            for collection_name in self.db.list_collection_names():
                try:
                    coll_stats = self.db.command('collStats', collection_name)
                    collections_stats[collection_name] = {
                        'count': coll_stats.get('count', 0),
                        'size': coll_stats.get('size', 0),
                        'avg_obj_size': coll_stats.get('avgObjSize', 0),
                        'storage_size': coll_stats.get('storageSize', 0),
                        'indexes': coll_stats.get('nindexes', 0),
                        'index_size': coll_stats.get('totalIndexSize', 0)
                    }
                except Exception as e:
                    logger.error(f"Failed to get stats for collection {collection_name}: {e}")
            
            return {
                'database': {
                    'name': self.db.name,
                    'collections': db_stats.get('collections', 0),
                    'data_size': db_stats.get('dataSize', 0),
                    'storage_size': db_stats.get('storageSize', 0),
                    'indexes': db_stats.get('indexes', 0),
                    'index_size': db_stats.get('indexSize', 0)
                },
                'collections': collections_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'timestamp': time.time(),
            'connection_pool': self.get_connection_pool_stats(),
            'performance_metrics': self.get_performance_metrics(),
            'index_performance': self.get_index_performance(),
            'bulk_operations': self.get_bulk_operations_summary(),
            'database_stats': self.get_database_stats()
        }

# Global database optimizer instance
_db_optimizer: Optional[DatabaseOptimizer] = None

def get_db_optimizer(db_client: MongoClient = None) -> DatabaseOptimizer:
    """Get global database optimizer instance"""
    global _db_optimizer
    if _db_optimizer is None and db_client:
        _db_optimizer = DatabaseOptimizer(db_client)
    return _db_optimizer

def reset_db_optimizer():
    """Reset global database optimizer (useful for testing)"""
    global _db_optimizer
    _db_optimizer = None 