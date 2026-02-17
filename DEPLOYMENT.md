# Storm Chase Dashboard - Deployment Guide

## 📦 Streamlit Cloud Deployment Instructions

### Prerequisites
- Streamlit Cloud account (https://streamlit.io/cloud)
- OpenAI API key
- GitHub repository (optional but recommended)

### Required Python Packages
The following packages are required and already configured in the project:
- `streamlit>=1.28.0`
- `folium>=0.14.0`
- `streamlit-folium>=0.15.0`
- `pandas>=2.0.0`
- `numpy>=1.24.0`
- `openai>=1.0.0`
- `requests>=2.31.0`
- `geopandas>=0.14.0`
- `geopy>=2.4.0`
- `matplotlib>=3.7.0`
- `netCDF4>=1.6.0`
- `pyproj>=3.6.0`
- `shapely>=2.0.0`
- `trafilatura>=1.6.0`
- `xarray>=2023.0.0`
- `Pillow>=10.0.0`

### Deployment Steps

#### 1. Prepare Your Repository
Ensure the following files are in your repository:
- `app.py` (main application)
- `.streamlit/config.toml` (server configuration)
- `static/` directory with PWA files (icons, service worker, etc.)
- All Python dependencies configured

#### 2. Configure Secrets in Streamlit Cloud
In your Streamlit Cloud dashboard:
1. Go to your app settings
2. Navigate to "Secrets" section
3. Add your OpenAI API key:

```toml
OPENAI_API_KEY = "sk-your-actual-openai-api-key-here"
```

#### 3. Deploy
1. Connect your GitHub repository to Streamlit Cloud
2. Select `app.py` as the main file
3. Click "Deploy"
4. Wait for deployment to complete

### Important Configuration Notes

#### Server Configuration (Already Set)
The `.streamlit/config.toml` file is already configured for proper deployment:
- Server runs on `0.0.0.0:5000` (Streamlit Cloud will handle port mapping)
- Headless mode enabled
- CORS and XSRF protection configured

#### Static Files
The following static files are required for PWA functionality:
- `static/icon-192x192.png`
- `static/icon-512x512.png`
- `static/manifest.json`
- `static/mobile-styles.css`
- `static/gps-tracker.js`
- `sw.js`

These files enable offline functionality and mobile optimization.

#### External Services Used
The application connects to these external services (no additional configuration needed):
- **NEXRAD Radar**: Iowa State Mesonet WMS services
- **SPC Products**: Storm Prediction Center WMS overlays
- **OpenAI API**: Requires your API key (configured in secrets)

### Post-Deployment Verification

After deployment, verify:
1. ✅ App loads without errors
2. ✅ Interactive map displays correctly
3. ✅ Weather parameters show in two columns below map
4. ✅ GPS tracking functionality works on mobile devices
5. ✅ AI-powered target recommendations generate properly
6. ✅ Collapsible legend toggles on/off
7. ✅ Radar overlays load from external services

### Performance Optimization

The app is optimized for performance:
- Session state caching for weather data
- Efficient folium map rendering
- Lazy loading of radar overlays
- Optimized AI query caching

### Troubleshooting

**Issue: App shows "OpenAI API key not found"**
- Solution: Add `OPENAI_API_KEY` to Streamlit Cloud secrets

**Issue: Radar overlays not loading**
- Solution: Check external service availability (Iowa State Mesonet, SPC)

**Issue: GPS tracking not working**
- Solution: Ensure HTTPS deployment (required for geolocation API)

**Issue: Static files (icons) not found**
- Solution: Verify `static/` directory is included in deployment

### Support Resources
- Streamlit Documentation: https://docs.streamlit.io/
- Streamlit Cloud: https://streamlit.io/cloud
- OpenAI API: https://platform.openai.com/

---

## 🚀 Production Ready
This Storm Chase Dashboard is production-ready with:
- 16+ professional meteorological parameters
- Real-time radar and SPC data integration
- AI-powered intelligent targeting
- Mobile-optimized PWA functionality
- GPS breadcrumb tracking
- Advanced composite indices (SCP, STP, EHI, BRN)

Happy storm chasing! ⛈️
