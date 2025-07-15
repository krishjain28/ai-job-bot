import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import datetime
import asyncio
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError
import hashlib

logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

@dataclass
class TransactionInfo:
    """Transaction information"""
    transaction_id: str
    operations: List[Dict[str, Any]]
    status: TransactionStatus
    start_time: float
    end_time: Optional[float] = None
    error: Optional[str] = None
    rollback_operations: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class DataValidationResult:
    """Data validation result"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class DataConsistencyManager:
    """Manages data consistency, transactions, and validation"""
    
    def __init__(self, db_client: MongoClient):
        self.db_client = db_client
        self.active_transactions: Dict[str, TransactionInfo] = {}
        self.transaction_history: List[TransactionInfo] = []
        self.validation_rules: Dict[str, Callable] = {}
        self.initialize_validation_rules()
    
    def initialize_validation_rules(self):
        """Initialize data validation rules"""
        
        # Job validation rules
        self.validation_rules['job'] = self._validate_job_data
        self.validation_rules['application'] = self._validate_application_data
        self.validation_rules['user'] = self._validate_user_data
    
    def _validate_job_data(self, job_data: Dict[str, Any]) -> DataValidationResult:
        """Validate job data"""
        result = DataValidationResult(is_valid=True)
        
        # Required fields
        required_fields = ['title', 'company', 'source']
        for field in required_fields:
            if not job_data.get(field):
                result.is_valid = False
                result.errors.append(f"Missing required field: {field}")
        
        # Title validation
        title = job_data.get('title', '')
        if len(title) < 3:
            result.is_valid = False
            result.errors.append("Job title too short")
        elif len(title) > 200:
            result.is_valid = False
            result.errors.append("Job title too long")
        
        # Company validation
        company = job_data.get('company', '')
        if len(company) < 2:
            result.is_valid = False
            result.errors.append("Company name too short")
        
        # URL validation
        url = job_data.get('url', '')
        if url and not url.startswith(('http://', 'https://')):
            result.warnings.append("Job URL may be invalid")
        
        # Source validation
        valid_sources = ['linkedin', 'indeed', 'remoteok', 'wellfound']
        source = job_data.get('source', '').lower()
        if source not in valid_sources:
            result.warnings.append(f"Unknown job source: {source}")
        
        return result
    
    def _validate_application_data(self, app_data: Dict[str, Any]) -> DataValidationResult:
        """Validate application data"""
        result = DataValidationResult(is_valid=True)
        
        # Required fields
        required_fields = ['job_id', 'status', 'applied_at']
        for field in required_fields:
            if not app_data.get(field):
                result.is_valid = False
                result.errors.append(f"Missing required field: {field}")
        
        # Status validation
        valid_statuses = ['applied', 'failed', 'pending', 'rejected']
        status = app_data.get('status', '')
        if status not in valid_statuses:
            result.is_valid = False
            result.errors.append(f"Invalid application status: {status}")
        
        # Date validation
        applied_at = app_data.get('applied_at')
        if applied_at:
            try:
                datetime.fromisoformat(applied_at.replace('Z', '+00:00'))
            except ValueError:
                result.is_valid = False
                result.errors.append("Invalid applied_at date format")
        
        return result
    
    def _validate_user_data(self, user_data: Dict[str, Any]) -> DataValidationResult:
        """Validate user data"""
        result = DataValidationResult(is_valid=True)
        
        # Required fields
        required_fields = ['email', 'name']
        for field in required_fields:
            if not user_data.get(field):
                result.is_valid = False
                result.errors.append(f"Missing required field: {field}")
        
        # Email validation
        email = user_data.get('email', '')
        if '@' not in email or '.' not in email:
            result.is_valid = False
            result.errors.append("Invalid email format")
        
        # Name validation
        name = user_data.get('name', '')
        if len(name) < 2:
            result.is_valid = False
            result.errors.append("Name too short")
        
        return result
    
    def validate_data(self, data_type: str, data: Dict[str, Any]) -> DataValidationResult:
        """Validate data using appropriate validation rules"""
        validator = self.validation_rules.get(data_type)
        if validator:
            return validator(data)
        else:
            # Default validation - just check for required fields
            result = DataValidationResult(is_valid=True)
            if not data:
                result.is_valid = False
                result.errors.append("Data cannot be empty")
            return result
    
    def generate_job_hash(self, job_data: Dict[str, Any]) -> str:
        """Generate unique hash for job data to detect duplicates"""
        # Create a normalized version for hashing
        normalized_data = {
            'title': job_data.get('title', '').lower().strip(),
            'company': job_data.get('company', '').lower().strip(),
            'source': job_data.get('source', '').lower().strip(),
            'location': job_data.get('location', '').lower().strip()
        }
        
        # Sort keys for consistent hashing
        sorted_data = json.dumps(normalized_data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def start_transaction(self) -> str:
        """Start a new transaction"""
        transaction_id = f"tx_{int(time.time() * 1000)}_{hash(time.time()) % 10000}"
        
        transaction = TransactionInfo(
            transaction_id=transaction_id,
            operations=[],
            status=TransactionStatus.PENDING,
            start_time=time.time()
        )
        
        self.active_transactions[transaction_id] = transaction
        logger.info(f"Started transaction: {transaction_id}")
        
        return transaction_id
    
    async def add_operation(self, transaction_id: str, operation: Dict[str, Any]) -> bool:
        """Add operation to transaction"""
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction = self.active_transactions[transaction_id]
        
        # Validate operation
        if not self._validate_operation(operation):
            logger.error(f"Invalid operation in transaction {transaction_id}")
            return False
        
        # Add rollback operation
        rollback_op = self._create_rollback_operation(operation)
        transaction.rollback_operations.append(rollback_op)
        
        # Add operation
        transaction.operations.append(operation)
        
        logger.debug(f"Added operation to transaction {transaction_id}: {operation.get('type')}")
        return True
    
    def _validate_operation(self, operation: Dict[str, Any]) -> bool:
        """Validate operation structure"""
        required_fields = ['type', 'collection', 'data']
        
        for field in required_fields:
            if field not in operation:
                logger.error(f"Operation missing required field: {field}")
                return False
        
        valid_types = ['insert', 'update', 'delete', 'upsert']
        if operation['type'] not in valid_types:
            logger.error(f"Invalid operation type: {operation['type']}")
            return False
        
        return True
    
    def _create_rollback_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Create rollback operation for the given operation"""
        op_type = operation['type']
        
        if op_type == 'insert':
            # Rollback insert with delete
            return {
                'type': 'delete',
                'collection': operation['collection'],
                'filter': {'_id': operation.get('data', {}).get('_id')}
            }
        
        elif op_type == 'delete':
            # Rollback delete with insert (if we have the original data)
            return {
                'type': 'insert',
                'collection': operation['collection'],
                'data': operation.get('original_data', {})
            }
        
        elif op_type == 'update':
            # Rollback update with reverse update
            return {
                'type': 'update',
                'collection': operation['collection'],
                'filter': operation.get('filter', {}),
                'data': operation.get('original_data', {})
            }
        
        elif op_type == 'upsert':
            # Rollback upsert based on whether it was insert or update
            return {
                'type': 'delete',
                'collection': operation['collection'],
                'filter': {'_id': operation.get('data', {}).get('_id')}
            }
        
        return {}
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit transaction"""
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction {transaction_id} not found")
            return False
        
        transaction = self.active_transactions[transaction_id]
        
        try:
            # Execute all operations
            for operation in transaction.operations:
                success = await self._execute_operation(operation)
                if not success:
                    # Rollback on failure
                    await self._rollback_transaction(transaction_id)
                    return False
            
            # Mark as committed
            transaction.status = TransactionStatus.COMMITTED
            transaction.end_time = time.time()
            
            # Move to history
            self.transaction_history.append(transaction)
            del self.active_transactions[transaction_id]
            
            logger.info(f"Committed transaction: {transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error committing transaction {transaction_id}: {e}")
            await self._rollback_transaction(transaction_id)
            return False
    
    async def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback transaction"""
        return await self._rollback_transaction(transaction_id)
    
    async def _rollback_transaction(self, transaction_id: str) -> bool:
        """Internal rollback implementation"""
        if transaction_id not in self.active_transactions:
            logger.error(f"Transaction {transaction_id} not found for rollback")
            return False
        
        transaction = self.active_transactions[transaction_id]
        
        try:
            # Execute rollback operations in reverse order
            for rollback_op in reversed(transaction.rollback_operations):
                if rollback_op:  # Skip empty rollback operations
                    await self._execute_operation(rollback_op)
            
            # Mark as rolled back
            transaction.status = TransactionStatus.ROLLED_BACK
            transaction.end_time = time.time()
            
            # Move to history
            self.transaction_history.append(transaction)
            del self.active_transactions[transaction_id]
            
            logger.info(f"Rolled back transaction: {transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back transaction {transaction_id}: {e}")
            transaction.status = TransactionStatus.FAILED
            transaction.error = str(e)
            transaction.end_time = time.time()
            
            # Move to history even if rollback failed
            self.transaction_history.append(transaction)
            del self.active_transactions[transaction_id]
            
            return False
    
    async def _execute_operation(self, operation: Dict[str, Any]) -> bool:
        """Execute a single database operation"""
        try:
            op_type = operation['type']
            collection_name = operation['collection']
            collection = self.db_client.get_database()[collection_name]
            
            if op_type == 'insert':
                result = collection.insert_one(operation['data'])
                return result.inserted_id is not None
            
            elif op_type == 'update':
                result = collection.update_one(
                    operation['filter'],
                    {'$set': operation['data']}
                )
                return result.modified_count > 0
            
            elif op_type == 'delete':
                result = collection.delete_one(operation['filter'])
                return result.deleted_count > 0
            
            elif op_type == 'upsert':
                result = collection.replace_one(
                    operation['filter'],
                    operation['data'],
                    upsert=True
                )
                return True
            
            return False
            
        except PyMongoError as e:
            logger.error(f"Database operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in database operation: {e}")
            return False
    
    async def bulk_insert_jobs(self, jobs: List[Dict[str, Any]], validate: bool = True) -> Dict[str, Any]:
        """Bulk insert jobs with deduplication and validation"""
        results = {
            'total': len(jobs),
            'inserted': 0,
            'duplicates': 0,
            'invalid': 0,
            'errors': []
        }
        
        # Validate jobs
        valid_jobs = []
        for job in jobs:
            if validate:
                validation_result = self.validate_data('job', job)
                if not validation_result.is_valid:
                    results['invalid'] += 1
                    results['errors'].extend(validation_result.errors)
                    continue
            
            # Generate hash for deduplication
            job['job_hash'] = self.generate_job_hash(job)
            valid_jobs.append(job)
        
        if not valid_jobs:
            return results
        
        # Start transaction for bulk insert
        transaction_id = self.start_transaction()
        
        try:
            # Check for duplicates
            existing_hashes = set()
            job_hashes = [job['job_hash'] for job in valid_jobs]
            
            # Query existing hashes
            collection = self.db_client.get_database()['jobs']
            existing_jobs = collection.find(
                {'job_hash': {'$in': job_hashes}},
                {'job_hash': 1}
            )
            
            for job in existing_jobs:
                existing_hashes.add(job['job_hash'])
            
            # Filter out duplicates
            unique_jobs = [job for job in valid_jobs if job['job_hash'] not in existing_hashes]
            results['duplicates'] = len(valid_jobs) - len(unique_jobs)
            
            # Insert unique jobs
            if unique_jobs:
                for job in unique_jobs:
                    await self.add_operation(transaction_id, {
                        'type': 'insert',
                        'collection': 'jobs',
                        'data': job
                    })
                
                # Commit transaction
                success = await self.commit_transaction(transaction_id)
                if success:
                    results['inserted'] = len(unique_jobs)
                else:
                    results['errors'].append("Transaction commit failed")
            else:
                # No unique jobs to insert
                await self.rollback_transaction(transaction_id)
        
        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            results['errors'].append(str(e))
            await self.rollback_transaction(transaction_id)
        
        return results
    
    def get_transaction_metrics(self) -> Dict[str, Any]:
        """Get transaction metrics"""
        total_transactions = len(self.transaction_history)
        committed = sum(1 for tx in self.transaction_history if tx.status == TransactionStatus.COMMITTED)
        rolled_back = sum(1 for tx in self.transaction_history if tx.status == TransactionStatus.ROLLED_BACK)
        failed = sum(1 for tx in self.transaction_history if tx.status == TransactionStatus.FAILED)
        
        success_rate = 0.0
        if total_transactions > 0:
            success_rate = committed / total_transactions
        
        return {
            'total_transactions': total_transactions,
            'committed': committed,
            'rolled_back': rolled_back,
            'failed': failed,
            'success_rate': success_rate,
            'active_transactions': len(self.active_transactions),
            'recent_transactions': [
                {
                    'id': tx.transaction_id,
                    'status': tx.status.value,
                    'operations': len(tx.operations),
                    'duration': tx.end_time - tx.start_time if tx.end_time else None
                }
                for tx in self.transaction_history[-10:]  # Last 10 transactions
            ]
        }

# Global data consistency manager instance
_data_consistency_manager: Optional[DataConsistencyManager] = None

def get_data_consistency_manager(db_client: MongoClient = None) -> DataConsistencyManager:
    """Get global data consistency manager instance"""
    global _data_consistency_manager
    if _data_consistency_manager is None and db_client:
        _data_consistency_manager = DataConsistencyManager(db_client)
    return _data_consistency_manager

def reset_data_consistency_manager():
    """Reset global data consistency manager (useful for testing)"""
    global _data_consistency_manager
    _data_consistency_manager = None 