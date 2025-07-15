#!/usr/bin/env python3
"""
AI Job Bot Deployment Script
Helps users deploy the bot to Render and Vercel
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        "config.py",
        "main.py",
        "resume_parser.py",
        "gpt_filter.py",
        "apply.py",
        "sheets_logger.py",
        "requirements.txt",
        "render.yaml",
        "vercel.json",
        "README.md"
    ]
    
    required_dirs = [
        "api",
        "database",
        "job_scraper",
        "frontend"
    ]
    
    missing_files = []
    missing_dirs = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
            
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
            
    if missing_files or missing_dirs:
        print("❌ Missing required files/directories:")
        for file in missing_files:
            print(f"   - {file}")
        for dir_path in missing_dirs:
            print(f"   - {dir_path}/")
        return False
        
    print("✅ All required files and directories found")
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not Path(".env").exists():
        print("❌ .env file not found")
        print("   Please copy env.example to .env and configure your settings")
        return False
        
    print("✅ .env file found")
    return True

def check_resume():
    """Check if resume file exists"""
    resume_path = os.getenv("RESUME_PATH", "resume.pdf")
    if not Path(resume_path).exists():
        print(f"❌ Resume file not found: {resume_path}")
        print("   Please add your resume.pdf to the project root")
        return False
        
    print(f"✅ Resume file found: {resume_path}")
    return True

def setup_git():
    """Initialize git repository if not already done"""
    if Path(".git").exists():
        print("✅ Git repository already initialized")
        return True
        
    try:
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
        print("✅ Git repository initialized")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error initializing git: {e}")
        return False

def create_github_repo():
    """Guide user to create GitHub repository"""
    print("\n📋 GitHub Repository Setup:")
    print("1. Go to https://github.com/new")
    print("2. Create a new repository named 'ai-job-bot'")
    print("3. Make it public or private (your choice)")
    print("4. Don't initialize with README (we already have one)")
    print("5. Copy the repository URL")
    
    repo_url = input("\nEnter your GitHub repository URL: ").strip()
    
    if not repo_url:
        print("❌ No repository URL provided")
        return False
        
    try:
        subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
        print("✅ Code pushed to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error pushing to GitHub: {e}")
        return False

def deploy_to_render():
    """Guide user to deploy to Render"""
    print("\n🚀 Render Deployment:")
    print("1. Go to https://render.com")
    print("2. Sign up/Login with your GitHub account")
    print("3. Click 'New +' and select 'Blueprint'")
    print("4. Connect your GitHub repository")
    print("5. Render will automatically detect the render.yaml file")
    print("6. Set the following environment variables:")
    
    env_vars = [
        "OPENAI_API_KEY",
        "GOOGLE_SHEET_ID", 
        "GOOGLE_CREDENTIALS_JSON",
        "MONGODB_URI",
        "EMAIL_USERNAME",
        "EMAIL_PASSWORD",
        "EMAIL_TO_ADDRESS"
    ]
    
    for var in env_vars:
        print(f"   - {var}")
        
    print("\n7. Click 'Apply' to deploy")
    print("8. Wait for deployment to complete")
    
    input("\nPress Enter when deployment is complete...")
    return True

def deploy_to_vercel():
    """Guide user to deploy frontend to Vercel"""
    print("\n🎨 Vercel Frontend Deployment:")
    print("1. Go to https://vercel.com")
    print("2. Sign up/Login with your GitHub account")
    print("3. Click 'New Project'")
    print("4. Import your GitHub repository")
    print("5. Configure build settings:")
    print("   - Framework Preset: Other")
    print("   - Build Command: cd frontend && npm install && npm run build")
    print("   - Output Directory: frontend/dist")
    print("6. Add environment variable:")
    print("   - REACT_APP_API_URL: Your Render API URL")
    print("7. Click 'Deploy'")
    
    input("\nPress Enter when deployment is complete...")
    return True

def setup_mongodb():
    """Guide user to set up MongoDB Atlas"""
    print("\n🗄️  MongoDB Atlas Setup:")
    print("1. Go to https://www.mongodb.com/atlas")
    print("2. Create a free account")
    print("3. Create a new cluster (free tier)")
    print("4. Set up database access:")
    print("   - Create a database user")
    print("   - Set username and password")
    print("5. Set up network access:")
    print("   - Allow access from anywhere (0.0.0.0/0)")
    print("6. Get connection string:")
    print("   - Click 'Connect' on your cluster")
    print("   - Choose 'Connect your application'")
    print("   - Copy the connection string")
    print("7. Replace <password> with your actual password")
    print("8. Add to your .env file as MONGODB_URI")
    
    input("\nPress Enter when MongoDB is set up...")
    return True

def setup_google_sheets():
    """Guide user to set up Google Sheets integration"""
    print("\n📊 Google Sheets Setup:")
    print("1. Go to https://console.cloud.google.com")
    print("2. Create a new project")
    print("3. Enable Google Sheets API:")
    print("   - Go to APIs & Services > Library")
    print("   - Search for 'Google Sheets API'")
    print("   - Click 'Enable'")
    print("4. Create service account:")
    print("   - Go to APIs & Services > Credentials")
    print("   - Click 'Create Credentials' > 'Service Account'")
    print("   - Fill in details and create")
    print("5. Download JSON key:")
    print("   - Click on the service account")
    print("   - Go to 'Keys' tab")
    print("   - Add new key (JSON)")
    print("   - Download the JSON file")
    print("6. Encode JSON to base64:")
    print("   - Run: base64 -i your-key.json")
    print("   - Copy the output")
    print("7. Create Google Sheet:")
    print("   - Go to https://sheets.google.com")
    print("   - Create new sheet")
    print("   - Share with service account email")
    print("8. Add to .env file:")
    print("   - GOOGLE_SHEET_ID: Your sheet ID (from URL)")
    print("   - GOOGLE_CREDENTIALS_JSON: Base64 encoded JSON")
    
    input("\nPress Enter when Google Sheets is set up...")
    return True

def test_local_setup():
    """Test the local setup"""
    print("\n🧪 Testing Local Setup:")
    
    try:
        # Test imports
        import config
        print("✅ Config imported successfully")
        
        # Test resume parsing
        from resume_parser import ResumeParser
        parser = ResumeParser("resume.pdf")
        sections = parser.parse_resume()
        print(f"✅ Resume parsed successfully ({len(sections.get('skills', {}).get('technical', []))} skills found)")
        
        # Test database connection
        from database.connection import db_manager
        db_manager.connect()
        print("✅ Database connection successful")
        db_manager.disconnect()
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main deployment script"""
    print("🤖 AI Job Bot Deployment Script")
    print("=" * 50)
    
    # Check prerequisites
    if not check_requirements():
        print("\n❌ Please fix the missing files/directories before continuing")
        return
        
    if not check_env_file():
        print("\n❌ Please set up your .env file before continuing")
        return
        
    if not check_resume():
        print("\n❌ Please add your resume file before continuing")
        return
        
    # Setup steps
    print("\n📋 Setup Steps:")
    print("1. ✅ Check requirements")
    print("2. ✅ Check environment file")
    print("3. ✅ Check resume file")
    
    # Git setup
    if not setup_git():
        print("❌ Git setup failed")
        return
    print("4. ✅ Git repository setup")
    
    # GitHub setup
    if not create_github_repo():
        print("❌ GitHub setup failed")
        return
    print("5. ✅ GitHub repository created")
    
    # MongoDB setup
    setup_mongodb()
    print("6. ✅ MongoDB Atlas setup")
    
    # Google Sheets setup
    setup_google_sheets()
    print("7. ✅ Google Sheets setup")
    
    # Test local setup
    if not test_local_setup():
        print("❌ Local setup test failed")
        return
    print("8. ✅ Local setup tested")
    
    # Deploy to Render
    deploy_to_render()
    print("9. ✅ Render deployment")
    
    # Deploy to Vercel
    deploy_to_vercel()
    print("10. ✅ Vercel deployment")
    
    print("\n🎉 Deployment Complete!")
    print("\n📋 Next Steps:")
    print("1. Test your deployed application")
    print("2. Monitor the first job run")
    print("3. Check Google Sheets for application logs")
    print("4. Configure email notifications if desired")
    print("5. Adjust search keywords and settings as needed")
    
    print("\n📚 Documentation:")
    print("- README.md: Complete setup and usage guide")
    print("- API docs: Available at your Render URL/docs")
    print("- Dashboard: Available at your Vercel URL")

if __name__ == "__main__":
    main() 