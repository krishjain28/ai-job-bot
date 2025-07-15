import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# Database
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/ai-job-bot")

# App Settings
RESUME_PATH = "test_resume.txt"  # Change to "resume.pdf" for production
MAX_JOBS_PER_RUN = int(os.getenv("MAX_JOBS_PER_RUN", "20"))
APPLICATION_DELAY = int(os.getenv("APPLICATION_DELAY", "30"))  # seconds between applications

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Email Notification Settings
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "False").lower() == "true"
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # App password for Gmail
EMAIL_TO_ADDRESS = os.getenv("EMAIL_TO_ADDRESS")

# Scheduling Settings
SCHEDULE_ENABLED = os.getenv("SCHEDULE_ENABLED", "False").lower() == "true"
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "10:00")  # Daily run time (HH:MM)

# Job Search Settings
SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "software engineer,developer,full stack,backend,frontend").split(",")
SEARCH_LOCATION = os.getenv("SEARCH_LOCATION", "Remote")

# Personal Information (for applications)
PERSONAL_NAME = os.getenv("PERSONAL_NAME", "Your Name")
PERSONAL_EMAIL = os.getenv("PERSONAL_EMAIL", "your.email@example.com")
PERSONAL_PHONE = os.getenv("PERSONAL_PHONE", "+1234567890")
PERSONAL_LOCATION = os.getenv("PERSONAL_LOCATION", "Remote")
PERSONAL_LINKEDIN = os.getenv("PERSONAL_LINKEDIN", "https://linkedin.com/in/yourprofile")

# Application Settings
MAX_APPLICATIONS_PER_RUN = int(os.getenv("MAX_APPLICATIONS_PER_RUN", "10"))
REQUIRE_COVER_LETTER = os.getenv("REQUIRE_COVER_LETTER", "False").lower() == "true"

# Anti-Detection Settings
USE_PROXY = os.getenv("USE_PROXY", "False").lower() == "true"
PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else []
RANDOM_DELAYS = os.getenv("RANDOM_DELAYS", "True").lower() == "true" 

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_JOB_TTL = int(os.getenv('REDIS_JOB_TTL', 24*60*60))  # 24 hours

# Redis URL for compatibility
REDIS_URL = os.getenv('REDIS_URL', f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}") 