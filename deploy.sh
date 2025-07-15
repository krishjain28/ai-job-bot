#!/bin/bash

echo "🚀 AI Job BOT Deployment Script"
echo "================================"

# Check if git is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: Git repository has uncommitted changes"
    echo "Please commit all changes before deploying"
    exit 1
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to GitHub"
else
    echo "❌ Failed to push to GitHub"
    exit 1
fi

echo ""
echo "🎯 Next Steps:"
echo "=============="
echo ""
echo "1. 📋 Deploy Backend on Render:"
echo "   - Go to https://render.com"
echo "   - Click 'New +' → 'Blueprint'"
echo "   - Connect repository: krishjain28/ai-job-bot"
echo "   - Configure environment variables"
echo "   - Click 'Apply'"
echo ""
echo "2. 🌐 Deploy Frontend on Vercel:"
echo "   - Go to https://vercel.com"
echo "   - Click 'New Project'"
echo "   - Import repository: krishjain28/ai-job-bot"
echo "   - Set Root Directory: frontend"
echo "   - Set Build Command: npm run build"
echo "   - Set Output Directory: build"
echo "   - Add REACT_APP_API_URL environment variable"
echo "   - Click 'Deploy'"
echo ""
echo "3. 🔧 Environment Variables to Set:"
echo "   - MONGODB_URI"
echo "   - OPENAI_API_KEY"
echo "   - GOOGLE_SHEET_ID"
echo "   - GOOGLE_CREDENTIALS_JSON"
echo "   - REACT_APP_API_URL (for Vercel)"
echo ""
echo "4. 📖 Read the full deployment guide: DEPLOYMENT_GUIDE.md"
echo ""
echo "🎉 Happy deploying!" 