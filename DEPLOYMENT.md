# GMet Weather API - Deployment Guide

## 🚀 Quick Deployment to Render (Recommended)

### Prerequisites
- GitHub account
- Code pushed to GitHub repository

### Step 1: Push Code to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Prepare for production deployment"

# Create repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/gmet-weather-api.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Render

1. **Go to [Render.com](https://render.com)** and sign up (free)

2. **Connect GitHub:**
   - Click "New +" → "Blueprint"
   - Connect your GitHub account
   - Select your `gmet-weather-api` repository
   - Render will detect `render.yaml` and create:
     - ✅ PostgreSQL database (free tier)
     - ✅ Web service (free tier)

3. **Wait for deployment** (3-5 minutes)
   - Render will automatically:
     - Install dependencies
     - Run database migrations
     - Start your API

4. **Get your live URL:**
   - Format: `https://gmet-weather-api.onrender.com`
   - API docs: `https://gmet-weather-api.onrender.com/docs`

### Step 3: Create Admin API Key

Once deployed, create an admin API key:

```bash
# SSH into your Render service or use Python shell
python scripts/create_admin_key.py
```

Or create via API (one-time setup):

```bash
curl -X POST "https://gmet-weather-api.onrender.com/api/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CTO Access Key",
    "role": "admin"
  }'
```

**Important:** Save the returned API key - it's shown only once!

### Step 4: Test Your Live API

```bash
# Test public endpoint (no auth required)
curl "https://gmet-weather-api.onrender.com/api/v1/weather/stations"

# Test with API key
curl "https://gmet-weather-api.onrender.com/api/v1/current?location=Accra" \
  -H "X-API-Key: YOUR_API_KEY_HERE"
```

### Step 5: Share with CTO

Send your CTO:

**📧 Email Template:**
```
Subject: GMet Weather API - Live Deployment

Hi [CTO Name],

The GMet Weather API is now live and ready for testing:

🌐 Live API: https://gmet-weather-api.onrender.com
📖 Interactive Docs: https://gmet-weather-api.onrender.com/docs

🔑 API Key (Admin Access): [PASTE_API_KEY_HERE]

Example requests:
- List stations: GET /api/v1/weather/stations (public, no auth)
- Current weather: GET /v1/current?location=Accra (public)
- Historical data: GET /v1/historical?station=Accra&start=2024-01-01&end=2024-12-31

All endpoints are documented in the interactive Swagger UI.

Best regards,
[Your Name]
```

---

## 🐳 Alternative: Docker Deployment

If you prefer Docker:

```bash
# Build image
docker build -t gmet-weather-api .

# Run with PostgreSQL
docker-compose up -d
```

---

## ☁️ Alternative: Railway.app

1. Go to [Railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository
4. Railway auto-detects Python and deploys
5. Add PostgreSQL: "New" → "Database" → "PostgreSQL"
6. Set environment variables (Railway provides UI)

---

## 🔒 Production Security Checklist

Before sharing with CTO:

- ✅ SECRET_KEY is set (not using random default)
- ✅ DEBUG=False in production
- ✅ CORS origins configured (not "*" wildcard)
- ✅ Database migrations applied
- ✅ Admin API key created
- ✅ Rate limiting enabled
- ✅ HTTPS enabled (Render provides free SSL)

---

## 📊 Monitoring & Logs

**Render Dashboard:**
- Logs: `https://dashboard.render.com/web/[service-id]/logs`
- Metrics: CPU, Memory, Request count
- Health checks: Automatic

**Check API Health:**
```bash
curl "https://gmet-weather-api.onrender.com/docs"
```

Should return 200 OK with Swagger UI.

---

## 🔄 Updating Production

```bash
# Make changes locally
git add .
git commit -m "Update: [description]"
git push origin main

# Render auto-deploys on push to main branch
```

---

## 💰 Costs

**Render Free Tier:**
- ✅ Web Service: Free (sleeps after 15 min inactivity)
- ✅ PostgreSQL: 90 days free, then $7/month
- ⚠️ Database size limit: 1GB

**Upgrade when needed:**
- Starter: $7/month (no sleep, 512MB RAM)
- Standard: $25/month (1GB RAM)

---

## 🆘 Troubleshooting

**Service won't start?**
```bash
# Check logs in Render dashboard
# Common issues:
# 1. Missing environment variables
# 2. Database connection failed
# 3. Migration errors
```

**Database connection errors?**
- Verify POSTGRES_* environment variables
- Check database is in same region
- Ensure asyncpg is installed

**API responds slowly?**
- Free tier sleeps after inactivity
- First request takes 30-60 seconds (cold start)
- Upgrade to paid tier for 24/7 availability

---

## 📝 Notes

- **Database:** SQLite is replaced with PostgreSQL in production (Render requirement)
- **Migrations:** Auto-run on deployment via `start.sh`
- **Static files:** Served via FastAPI (no separate CDN needed)
- **Logs:** Available in Render dashboard for 7 days (free tier)
