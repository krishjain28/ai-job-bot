# AI Job Bot 🤖

An intelligent automated job application system that scrapes job listings from multiple sources, filters them using GPT, and automatically applies to the best matches with personalized cover letters.

## 🚀 Features

- **📄 Advanced Resume Parsing**: Extracts skills, experience, and keywords using NLP
- **🔍 Multi-Source Job Scraping**: LinkedIn, Indeed, RemoteOK, Wellfound (AngelList)
- **🤖 AI-Powered Filtering**: GPT-4/3.5 scoring and job matching (1-10 scale)
- **📝 Auto-Application**: Real form filling with resume upload and cover letters
- **📊 Google Sheets Integration**: Comprehensive application logging
- **🗄️ MongoDB Storage**: Jobs, applications, and run history
- **🌐 REST API**: FastAPI backend for dashboard and management
- **🎨 React Dashboard**: Beautiful Material-UI monitoring interface
- **⏰ Scheduled Runs**: Daily automated job runs (configurable)
- **📧 Email Notifications**: Run summaries and alerts
- **🛡️ Anti-Detection**: Proxy support, random delays, user agent rotation
- **📱 Cover Letter Generation**: GPT-powered personalized cover letters

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Background    │
│   (Vercel)      │◄──►│   (Render)      │◄──►│   Worker        │
│   Dashboard     │    │   FastAPI       │    │   (Render)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   MongoDB       │
                       │   Atlas         │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Google        │
                       │   Sheets        │
                       └─────────────────┘
```

## 🎯 Job Sources Supported

- **LinkedIn**: Professional job listings with Easy Apply
- **Indeed**: Large job database with application forms
- **RemoteOK**: Remote job specialist
- **Wellfound**: Startup and tech jobs (formerly AngelList)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd ai-job-bot
```

### 2. Install Dependencies

```bash
# Backend
pip install -r requirements.txt
playwright install chromium

# Frontend
cd frontend
npm install
```

### 3. Environment Setup

```bash
cp env.example .env
# Edit .env with your API keys and settings
```

**Required Environment Variables:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_SHEET_ID`: Google Sheets ID for logging
- `GOOGLE_CREDENTIALS_JSON`: Base64-encoded Google service account JSON
- `MONGODB_URI`: MongoDB Atlas connection string
- `PERSONAL_*`: Your personal information for applications

### 4. Add Your Resume

Place your resume as `resume.pdf` in the project root.

### 5. Run Locally

```bash
# Test setup
python test_setup.py

# Run job bot
python main.py

# Run API server
uvicorn api.main:app --reload

# Run frontend
cd frontend && npm start
```

### 6. Deploy to Production

```bash
# Use the deployment script
python deploy.py
```

## 📋 Configuration

### Job Search Settings

```bash
# Search keywords
SEARCH_KEYWORDS=software engineer,developer,full stack,backend,frontend

# Location preference
SEARCH_LOCATION=Remote

# Maximum jobs per run
MAX_JOBS_PER_RUN=20

# Maximum applications per run
MAX_APPLICATIONS_PER_RUN=10
```

### Application Settings

```bash
# Delay between applications (seconds)
APPLICATION_DELAY=30

# Require cover letters
REQUIRE_COVER_LETTER=false

# Personal information
PERSONAL_NAME=Your Name
PERSONAL_EMAIL=your.email@example.com
PERSONAL_PHONE=+1234567890
PERSONAL_LINKEDIN=https://linkedin.com/in/yourprofile
```

### Email Notifications

```bash
# Enable email notifications
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO_ADDRESS=your_email@gmail.com
```

### Scheduling

```bash
# Enable daily scheduling
SCHEDULE_ENABLED=true
SCHEDULE_TIME=10:00  # Daily at 10:00 AM
```

## 🔧 API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health check
- `GET /jobs` - Get recent jobs
- `GET /applications` - Get recent applications
- `GET /runs` - Get job run history
- `POST /run` - Trigger new job run
- `GET /stats` - Get application statistics

## 📊 Google Sheets Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project
   - Enable Google Sheets API

2. **Create Service Account**
   - Go to APIs & Services > Credentials
   - Create Service Account
   - Download JSON key file

3. **Encode Credentials**
   ```bash
   base64 -i your-service-account.json
   ```

4. **Create Google Sheet**
   - Create new sheet
   - Share with service account email
   - Copy sheet ID from URL

5. **Add to Environment**
   ```bash
   GOOGLE_SHEET_ID=your_sheet_id
   GOOGLE_CREDENTIALS_JSON=base64_encoded_json
   ```

## 🗄️ MongoDB Atlas Setup

1. **Create Cluster**
   - Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Create free cluster
   - Set up database user
   - Configure network access (0.0.0.0/0)

2. **Get Connection String**
   - Click "Connect" on cluster
   - Choose "Connect your application"
   - Copy connection string
   - Replace `<password>` with actual password

3. **Add to Environment**
   ```bash
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/ai-job-bot
   ```

## 🚀 Production Deployment

### Backend (Render)

1. Connect GitHub repo to Render
2. Create new Web Service using `render.yaml`
3. Set environment variables in Render dashboard
4. Deploy

### Frontend (Vercel)

1. Connect GitHub repo to Vercel
2. Set build settings:
   - Build Command: `cd frontend && npm install && npm run build`
   - Output Directory: `frontend/dist`
3. Set environment variable: `REACT_APP_API_URL`
4. Deploy

### Automated Deployment

Use the included deployment script:

```bash
python deploy.py
```

This will guide you through:
- Git repository setup
- GitHub integration
- MongoDB Atlas setup
- Google Sheets setup
- Render deployment
- Vercel deployment

## 📈 Monitoring

The dashboard provides:
- **Real-time Statistics**: Jobs found, applications sent, success rates
- **Job History**: All scraped jobs with GPT scores
- **Application Tracking**: Status of all applications
- **Run History**: Detailed execution logs
- **Manual Triggers**: Start job runs on demand

## 🛡️ Security & Anti-Detection

- **User Agent Rotation**: Random browser user agents
- **Proxy Support**: Optional proxy rotation
- **Random Delays**: Variable delays between actions
- **Request Headers**: Realistic browser headers
- **Viewport Randomization**: Different screen sizes
- **Error Handling**: Graceful failure recovery

## 📧 Email Notifications

Get detailed run summaries via email:
- Jobs found and filtered
- Applications sent
- Success rates
- Error reports
- Next run schedule

## 🔄 Scheduling

Configure daily automated runs:
- **Time-based**: Run at specific times
- **Flexible**: Adjust schedule as needed
- **Reliable**: Automatic retry on failure
- **Monitoring**: Email notifications for each run

## 🧪 Testing

Test your setup:

```bash
# Run comprehensive tests
python test_setup.py

# Test individual components
python -c "from resume_parser import ResumeParser; print('Resume parser OK')"
python -c "from gpt_filter import filter_jobs; print('GPT filter OK')"
```

## 📚 API Documentation

Once deployed, visit your Render URL + `/docs` for interactive API documentation.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:
- Check the [README](README.md) for setup instructions
- Review the [API docs](your-render-url/docs)
- Open a GitHub issue with detailed error information

## 🎯 Roadmap

- [ ] Additional job sources (Glassdoor, Stack Overflow)
- [ ] Advanced resume parsing with AI
- [ ] Interview scheduling automation
- [ ] Salary negotiation assistance
- [ ] Company research integration
- [ ] Multi-language support
- [ ] Mobile app dashboard

---

**Built with ❤️ for job seekers everywhere** 