#!/usr/bin/env python3
"""
Test script to verify AI Job Bot setup
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing imports...")
    
    try:
        import openai
        print("✓ OpenAI")
    except ImportError:
        print("✗ OpenAI - Run: pip install openai")
        
    try:
        import fitz  # PyMuPDF
        print("✓ PyMuPDF")
    except ImportError:
        print("✗ PyMuPDF - Run: pip install PyMuPDF")
        
    try:
        import gspread
        print("✓ gspread")
    except ImportError:
        print("✗ gspread - Run: pip install gspread")
        
    try:
        import pymongo
        print("✓ pymongo")
    except ImportError:
        print("✗ pymongo - Run: pip install pymongo")
        
    try:
        from playwright.sync_api import sync_playwright
        print("✓ playwright")
    except ImportError:
        print("✗ playwright - Run: pip install playwright && playwright install")
        
    try:
        import fastapi
        print("✓ fastapi")
    except ImportError:
        print("✗ fastapi - Run: pip install fastapi uvicorn")

def test_files():
    """Test if required files exist"""
    print("\nTesting files...")
    
    files_to_check = [
        "config.py",
        "main.py",
        "resume_parser.py",
        "gpt_filter.py",
        "apply.py",
        "sheets_logger.py",
        "requirements.txt",
        "render.yaml",
        "README.md"
    ]
    
    for file in files_to_check:
        if Path(file).exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file}")

def test_directories():
    """Test if required directories exist"""
    print("\nTesting directories...")
    
    dirs_to_check = [
        "api",
        "database",
        "job_scraper",
        "frontend/src",
        "frontend/public"
    ]
    
    for dir_path in dirs_to_check:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/")

def test_env_vars():
    """Test environment variables"""
    print("\nTesting environment variables...")
    
    env_vars = [
        "OPENAI_API_KEY",
        "GOOGLE_SHEET_ID", 
        "GOOGLE_CREDENTIALS_JSON",
        "MONGODB_URI"
    ]
    
    for var in env_vars:
        if os.getenv(var):
            print(f"✓ {var}")
        else:
            print(f"✗ {var} (not set)")

def main():
    print("AI Job Bot Setup Test")
    print("=" * 30)
    
    test_imports()
    test_files()
    test_directories()
    test_env_vars()
    
    print("\n" + "=" * 30)
    print("Setup test completed!")
    print("\nNext steps:")
    print("1. Set up environment variables in .env file")
    print("2. Add your resume.pdf to the project root")
    print("3. Run: python main.py (for testing)")
    print("4. Run: uvicorn api.main:app --reload (for API)")
    print("5. Deploy to Render/Vercel for production")

if __name__ == "__main__":
    main() 