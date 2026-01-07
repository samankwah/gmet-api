# 🚀 Deploy GMet Weather API in 10 Minutes

## Step-by-Step Guide for Your CTO

### 1️⃣ Push to GitHub (5 minutes)

```bash
# In your project directory
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"

# Initialize git (if not already done)
git init
git add .
git commit -m "Production-ready GMet Weather API"

# Create NEW repository on GitHub.com:
# - Go to https://github.com/new
# - Name: gmet-weather-api
# - Make it Private
# - Don't add README (you already have one)
# - Click "Create repository"

# Then run these commands with YOUR username:
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/gmet-weather-api.git
git branch -M main
git push -u origin main
```

### 2️⃣ Deploy to Render (3 minutes)

1. **Sign up:** Go to https://render.com (free, no credit card)

2. **New Blueprint:**
   - Click "New +" → "Blueprint"
   - Click "Connect GitHub"
   - Select `gmet-weather-api` repository
   - Click "Apply"

3. **Render auto-creates:**
   - ✅ PostgreSQL database (free, 1GB)
   - ✅ Web service (free, with auto-sleep)
   - ✅ Environment variables (auto-configured)

4. **Wait 3-5 minutes** for deployment

5. **Get your URL:**
   ```
   https://gmet-weather-api-XXXX.onrender.com
   ```

### 3️⃣ Create API Key (1 minute)

Option A - Via deployed app:
```bash
# Replace with YOUR actual URL
curl -X POST "https://gmet-weather-api-XXXX.onrender.com/api/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "CTO Access", "role": "admin"}'
```

Option B - Via Render Shell:
```bash
# In Render dashboard: Shell tab
python scripts/create_admin_key.py
```

**Save the API key!** It's shown only once.

### 4️⃣ Test It (1 minute)

```bash
# Test public endpoint (no auth)
curl "https://gmet-weather-api-XXXX.onrender.com/api/v1/weather/stations"

# Test authenticated endpoint
curl "https://gmet-weather-api-XXXX.onrender.com/api/v1/current?location=Accra" \
  -H "X-API-Key: YOUR_API_KEY_HERE"

# Open interactive docs in browser
https://gmet-weather-api-XXXX.onrender.com/docs
```

### 5️⃣ Share with CTO

**Email to CTO:**

```
Subject: ✅ GMet Weather API - Live & Ready

Hi [CTO Name],

The GMet Weather API is deployed and live:

🌐 API Base URL: https://gmet-weather-api-XXXX.onrender.com
📖 Interactive Docs: https://gmet-weather-api-XXXX.onrender.com/docs

🔑 Admin API Key: [YOUR_API_KEY]

Quick test:
curl "https://gmet-weather-api-XXXX.onrender.com/api/v1/weather/stations"

Features:
✅ Real-time weather data for Ghana stations
✅ Historical weather queries (daily/hourly)
✅ RESTful API with OpenAPI docs
✅ Role-based authentication
✅ Rate limiting (100 req/min)
✅ PostgreSQL database
✅ Auto-scaling on Render

The API docs are interactive - you can test all endpoints directly in the browser.

Best,
[Your Name]
```

---

## 🔧 Important Notes

### First Request May Be Slow
- Free tier sleeps after 15 minutes
- First request after sleep takes 30-60 seconds
- Subsequent requests are instant

### Database Limits
- Free PostgreSQL: 1GB storage
- 90 days free trial, then $7/month
- Upgrade when needed

### Updating Production
```bash
# Make changes
git add .
git commit -m "Update: feature description"
git push origin main

# Render auto-deploys (takes 2-3 minutes)
```

---

## 🆘 Troubleshooting

### "Service Unavailable" error?
- Check Render dashboard logs
- Service might be starting (wait 60 seconds)
- Check environment variables are set

### Database connection error?
- Verify PostgreSQL service is running
- Check POSTGRES_* env vars in Render dashboard

### Can't create API key?
- Endpoint might still require auth (we removed it for stations, but api-keys creation was secured)
- Use Render Shell: `python scripts/create_admin_key.py`

---

## 💡 Pro Tips

1. **Custom Domain:** Render supports free custom domains
2. **Monitoring:** Use Render's built-in metrics (CPU, Memory, Requests)
3. **Logs:** Available in dashboard for 7 days (free tier)
4. **Health Checks:** Render pings `/docs` every 5 minutes
5. **SSL:** HTTPS enabled by default (free)

---

## 📊 What's Deployed

Your production API includes:

✅ All 81 security & performance fixes from our audit
✅ Admin-protected API key management
✅ Public weather data endpoints (no auth)
✅ Database constraints & validation
✅ UTC timezone handling
✅ Transaction-safe data imports
✅ Optimized queries (no N+1 problems)
✅ Rate limiting
✅ Comprehensive logging

---

## 📞 Need Help?

Check full docs: `DEPLOYMENT.md` in your repository

**Common issues solved:**
- Render deployment guide
- Environment configuration
- Database setup
- API key creation
- Testing examples
