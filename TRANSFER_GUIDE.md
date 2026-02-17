# 🚀 Storm Chase Dashboard - Streamlit Cloud Transfer Guide

Complete step-by-step instructions to transfer your Storm Chase Dashboard from Replit to Streamlit Community Cloud (100% FREE hosting).

---

## 📋 Prerequisites

Before starting, make sure you have:
- [ ] GitHub account (free) - https://github.com/signup
- [ ] Streamlit Cloud account (free) - https://streamlit.io/cloud
- [ ] OpenAI API key - https://platform.openai.com/api-keys

---

## Step 1: Download Your Project from Replit

### Option A: Download as ZIP (Easiest)
1. In Replit, click the three dots menu (⋮) in the file browser
2. Select "Download as ZIP"
3. Extract the ZIP file to your computer
4. **Important**: Rename `STREAMLIT_REQUIREMENTS.txt` to `requirements.txt`

### Option B: Use Git (Advanced)
```bash
git clone YOUR_REPLIT_REPO_URL
cd your-project-folder
mv STREAMLIT_REQUIREMENTS.txt requirements.txt
```

---

## Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `storm-chase-dashboard` (or your preferred name)
3. Description: "AI-powered storm chase dashboard with real-time radar and weather analysis"
4. **Make it Public** (required for free Streamlit Cloud hosting)
5. **DO NOT** initialize with README, .gitignore, or license (you already have these files)
6. Click "Create repository"

---

## Step 3: Upload Your Files to GitHub

### Option A: GitHub Web Interface (Easiest for Beginners)

1. On your new repository page, click "uploading an existing file"
2. **Drag and drop ALL files** from your downloaded project:
   ```
   ✅ app.py
   ✅ requirements.txt (renamed from STREAMLIT_REQUIREMENTS.txt)
   ✅ .gitignore
   ✅ DEPLOYMENT.md
   ✅ TRANSFER_GUIDE.md
   ✅ sw.js
   ✅ .streamlit/ folder (contains config.toml and secrets.toml.example)
   ✅ static/ folder (contains all PWA files and icons)
   ```
3. Add commit message: "Initial commit - Storm Chase Dashboard"
4. Click "Commit changes"

### Option B: Git Command Line (Advanced)

```bash
# Navigate to your project folder
cd path/to/storm-chase-dashboard

# Rename requirements file
mv STREAMLIT_REQUIREMENTS.txt requirements.txt

# Initialize git repository
git init
git add .
git commit -m "Initial commit - Storm Chase Dashboard"

# Connect to GitHub
git remote add origin https://github.com/YOUR_USERNAME/storm-chase-dashboard.git
git branch -M main
git push -u origin main
```

---

## Step 4: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click "New app" button
3. **Configure deployment:**
   - Repository: Select `your-username/storm-chase-dashboard`
   - Branch: `main`
   - Main file path: `app.py`
4. Click "Deploy!"

### What Happens Next:
- Streamlit Cloud will clone your repository
- Install all dependencies from `requirements.txt` (takes 2-5 minutes)
- Start your app automatically
- Give you a public URL like: `your-app-name.streamlit.app`

---

## Step 5: Configure OpenAI API Key (CRITICAL!)

Your AI-powered targeting features won't work without this step.

1. While app is deploying, click the "⚙️ Settings" button (bottom right)
2. Go to "Secrets" section
3. Paste the following (replace with your actual key):

```toml
OPENAI_API_KEY = "sk-your-actual-openai-api-key-here"
```

4. Click "Save"
5. App will automatically restart with the API key configured

---

## Step 6: Verify Deployment ✅

Once deployment completes, test these features:

### Critical Features:
- [ ] App loads without errors
- [ ] Interactive map displays centered on Valley, Nebraska
- [ ] Weather parameters show in two columns below map
- [ ] NEXRAD radar layers toggle on/off
- [ ] SPC outlook overlays display
- [ ] Collapsible legend works (click "🏷️ Legend" button)
- [ ] AI-powered intelligent targets generate (requires OpenAI key)
- [ ] GPS tracking button visible for mobile

### Advanced Features:
- [ ] All 16+ meteorological parameters display with correct values
- [ ] Parameter diagnostics expander shows comprehensive status
- [ ] Layer control (top-right) allows toggling radar/SPC layers
- [ ] Mobile PWA functionality works on iPad/iPhone
- [ ] Voice alerts work on mobile devices

---

## Step 7: Mobile/iPad Setup (Optional PWA)

Your Storm Chase Dashboard includes Progressive Web App functionality:

### iOS/iPad:
1. Open your Streamlit Cloud URL in Safari
2. Tap the "Share" button
3. Select "Add to Home Screen"
4. Tap "Add"
5. App icon appears on home screen - works like a native app!

### Android:
1. Open your Streamlit Cloud URL in Chrome
2. Tap the three dots menu
3. Select "Add to Home Screen"
4. Confirm

**PWA Features:**
- ✅ Works offline with cellular data
- ✅ Automatic GPS tracking every 30 seconds
- ✅ Voice alerts for tornado warnings
- ✅ Full-screen experience without browser chrome

---

## 🎯 Post-Deployment Configuration

### Custom Domain (Optional)
Streamlit Cloud allows custom domains on paid plans:
- Free plan: `your-app.streamlit.app`
- Teams plan: `chase.yourdomain.com`

### App Settings
In Streamlit Cloud settings, you can:
- **Reboot app**: If it becomes unresponsive
- **View logs**: Debug any issues
- **Manage secrets**: Update API keys
- **Delete app**: Remove deployment

---

## 📊 Monitoring & Analytics

Streamlit Cloud provides basic analytics:
1. Click on your app in the dashboard
2. View metrics:
   - Number of viewers
   - CPU/memory usage
   - Error logs
   - Deployment history

---

## 🔧 Troubleshooting Common Issues

### Issue: "App is not loading"
**Solution**: Check deployment logs in Streamlit Cloud dashboard for errors

### Issue: "No module named 'folium'"
**Solution**: Verify `requirements.txt` was uploaded correctly (renamed from STREAMLIT_REQUIREMENTS.txt)

### Issue: "OpenAI API key not found"
**Solution**: 
1. Go to app Settings → Secrets
2. Add: `OPENAI_API_KEY = "sk-your-key-here"`
3. Save and reboot app

### Issue: "Radar layers not showing"
**Solution**: External services (NEXRAD, SPC) may have temporary outages. Wait and refresh.

### Issue: "GPS tracking not working"
**Solution**: HTTPS is required for geolocation. Streamlit Cloud provides HTTPS automatically.

### Issue: "Icons/PWA not loading"
**Solution**: Ensure the entire `static/` folder was uploaded to GitHub

---

## 💰 Cost Comparison

| Platform | Cost | Features |
|----------|------|----------|
| **Streamlit Cloud** | **$0/month** (Public apps) | Unlimited visitors, automatic HTTPS, analytics |
| Replit Autoscale | ~$5-15/month | Custom domain, more resources |
| Replit Reserved VM | $20-160/month | Dedicated resources |

**Winner**: Streamlit Cloud for free public storm chase tools! 🎉

---

## 🔄 Making Updates After Deployment

### Method 1: GitHub Web Interface
1. Go to your repository on GitHub
2. Navigate to the file you want to edit
3. Click the pencil icon (✏️) to edit
4. Make your changes
5. Commit changes
6. **Streamlit Cloud auto-deploys within 1-2 minutes!**

### Method 2: Git Command Line
```bash
# Make your changes to app.py or other files
git add .
git commit -m "Description of changes"
git push

# Streamlit Cloud automatically detects changes and redeploys
```

---

## 📚 Additional Resources

- **Streamlit Documentation**: https://docs.streamlit.io/
- **Streamlit Community Forum**: https://discuss.streamlit.io/
- **GitHub Basics**: https://docs.github.com/en/get-started
- **OpenAI API Docs**: https://platform.openai.com/docs/

---

## ✨ You're All Set!

Your Storm Chase Dashboard is now:
- ✅ Running 24/7 on free Streamlit Cloud
- ✅ Accessible from any device worldwide
- ✅ Equipped with 16+ professional meteorological parameters
- ✅ Powered by AI for intelligent storm targeting
- ✅ Mobile-optimized with PWA functionality
- ✅ Featuring real-time NEXRAD radar and SPC data

**Share your app URL with fellow storm chasers and enjoy free, reliable hosting!** 🌪️⛈️

---

## 🆘 Need Help?

If you encounter any issues during transfer:
1. Check the troubleshooting section above
2. Review Streamlit Cloud deployment logs
3. Verify all files were uploaded to GitHub correctly
4. Ensure `requirements.txt` exists (not STREAMLIT_REQUIREMENTS.txt)
5. Confirm OpenAI API key is set in Streamlit Cloud secrets

Happy storm chasing! 🚗💨
