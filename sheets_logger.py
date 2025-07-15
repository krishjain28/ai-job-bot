import gspread
from google.oauth2.service_account import Credentials
import json
import logging
from datetime import datetime
from typing import Dict, List
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON

logger = logging.getLogger(__name__)

def setup_sheet_headers():
    """Setup headers for the Google Sheet"""
    try:
        if not GOOGLE_CREDENTIALS_JSON or not GOOGLE_SHEET_ID:
            logger.warning("Google Sheets not configured")
            return False
            
        # Parse credentials
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ])
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        
        # Set headers if sheet is empty
        if not sheet.get_all_values():
            headers = [
                'Timestamp', 'Job Title', 'Company', 'Location', 'Salary',
                'Source', 'Status', 'GPT Score', 'Application Message', 'Link'
            ]
            sheet.append_row(headers)
            logger.info("Google Sheet headers set up successfully")
            
        return True
        
    except Exception as e:
        logger.error(f"Error setting up Google Sheet headers: {e}")
        return False

def log_to_sheet(job: Dict, status: str = "Applied", message: str = ""):
    """Log job application to Google Sheet"""
    try:
        if not GOOGLE_CREDENTIALS_JSON or not GOOGLE_SHEET_ID:
            logger.warning("Google Sheets not configured, skipping log")
            return False
            
        # Parse credentials
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ])
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        
        # Prepare row data
        row_data = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            job.get('title', ''),
            job.get('company', ''),
            job.get('location', ''),
            job.get('salary', ''),
            job.get('source', ''),
            status,
            job.get('gpt_score', ''),
            message,
            job.get('link', '')
        ]
        
        # Append to sheet
        sheet.append_row(row_data)
        logger.info(f"Logged job application: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error logging to Google Sheet: {e}")
        return False

def get_application_history() -> List[Dict]:
    """Get application history from Google Sheet"""
    try:
        if not GOOGLE_CREDENTIALS_JSON or not GOOGLE_SHEET_ID:
            return []
            
        # Parse credentials
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ])
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        
        # Get all data
        data = sheet.get_all_records()
        
        return data
        
    except Exception as e:
        logger.error(f"Error getting application history: {e}")
        return [] 