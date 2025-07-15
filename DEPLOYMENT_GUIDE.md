# AI Job BOT Deployment Guide

This guide will help you deploy the AI Job BOT on Render (backend) and Vercel (frontend).

## Prerequisites

1. **GitHub Repository**: Your code should be pushed to GitHub
2. **Environment Variables**: Prepare your environment variables
3. **MongoDB Atlas**: Set up your database
4. **Google Cloud**: Set up Google Sheets API credentials

## Environment Variables Setup

### Required Environment Variables

```bash
# MongoDB Atlas
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/ai_job_bot

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Google Sheets
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_CREDENTIALS_JSON={"type": "service_account", ...}

# Optional
DEBUG=false
```

## Step 1: Deploy Backend on Render

### 1.1 Create Render Account
- Go to [render.com](https://render.com)
- Sign up with your GitHub account

### 1.2 Deploy Backend API
1. Click "New +" → "Blueprint"
2. Connect your GitHub repository: `krishjain28/ai-job-bot`
3. Render will automatically detect the `render.yaml` file
4. Configure environment variables:
   - `MONGODB_URI`
   - `OPENAI_API_KEY`
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_CREDENTIALS_JSON`
   - `DEBUG=false`
5. Click "Apply"

### 1.3 Deploy Background Worker
The worker will be automatically deployed from the blueprint.

### 1.4 Deploy Scheduled Job
The cron job will be automatically deployed from the blueprint.

## Step 2: Deploy Frontend on Vercel

### 2.1 Create Vercel Account
- Go to [vercel.com](https://vercel.com)
- Sign up with your GitHub account

### 2.2 Deploy Frontend
1. Click "New Project"
2. Import your GitHub repository: `krishjain28/ai-job-bot`
3. Configure project settings:
   - **Framework Preset**: Other
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
4. Add environment variable:
   - `REACT_APP_API_URL`: `https://your-render-api-url.onrender.com`
5. Click "Deploy"

## Step 3: Configure Domains

### 3.1 Custom Domain (Optional)
- **Render**: Add custom domain in your service settings
- **Vercel**: Add custom domain in your project settings

### 3.2 Update API URL
After deployment, update the `REACT_APP_API_URL` in Vercel with your actual Render API URL.

## Step 4: Verify Deployment

### 4.1 Test Backend API
```bash
curl https://your-render-api-url.onrender.com/health
```

### 4.2 Test Frontend
- Visit your Vercel URL
- Check if the dashboard loads
- Test API connectivity

### 4.3 Test Background Jobs
- Check Render logs for worker and cron job execution
- Verify job scraping and application processes

## Step 5: Monitoring and Maintenance

### 5.1 Render Monitoring
- Monitor service logs in Render dashboard
- Set up alerts for service failures
- Monitor resource usage

### 5.2 Vercel Monitoring
- Monitor build logs and deployment status
- Set up performance monitoring
- Monitor API calls to backend

### 5.3 Database Monitoring
- Monitor MongoDB Atlas performance
- Set up database alerts
- Monitor connection usage

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check build logs for dependency issues
   - Verify Python/Node.js versions
   - Check for missing environment variables

2. **Runtime Errors**
   - Check application logs
   - Verify environment variables are set correctly
   - Check database connectivity

3. **CORS Issues**
   - Ensure frontend URL is allowed in backend CORS settings
   - Check API endpoint configuration

4. **Playwright Issues**
   - Verify Playwright browsers are installed
   - Check system dependencies in Dockerfile

### Support Resources
- [Render Documentation](https://render.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com)

## Security Considerations

1. **Environment Variables**: Never commit sensitive data to Git
2. **API Keys**: Rotate keys regularly
3. **Database Access**: Use IP whitelisting
4. **HTTPS**: Both Render and Vercel provide HTTPS by default

## Cost Optimization

1. **Render**: Use appropriate instance sizes
2. **Vercel**: Free tier is usually sufficient for frontend
3. **MongoDB Atlas**: Use shared clusters for development
4. **OpenAI**: Monitor API usage and costs

## Next Steps

1. Set up monitoring and alerting
2. Configure CI/CD pipelines
3. Set up staging environment
4. Implement backup strategies
5. Plan for scaling 