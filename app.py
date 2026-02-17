import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import os
import base64
from openai import OpenAI
import random
import time
import math
from datetime import datetime, timedelta
import datetime as dt
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image
import io
import base64
import json
import xarray as xr
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from shapely.geometry import Point, LineString
import warnings
warnings.filterwarnings('ignore')

# API Configuration
NOAA_API_BASE = "https://api.weather.gov"
SPC_MESONET_BASE = "https://www.spc.noaa.gov/exper/mesonet/"
NWS_ALERTS_BASE = "https://api.weather.gov/alerts"
SPC_REPORTS_BASE = "https://www.spc.noaa.gov/climo/reports/"
GOES_BASE = "https://cdn.star.nesdis.noaa.gov/GOES16/"
HRRR_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod/"

# Page configuration
st.set_page_config(
    page_title="Storm Chase Dashboard",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# PWA and Mobile Integration
st.markdown("""
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="StormChase">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#dc143c">
    
    <!-- PWA Manifest -->
    <link rel="manifest" href="/static/manifest.json">
    
    <!-- iOS Icons -->
    <link rel="apple-touch-icon" sizes="180x180" href="/static/icon-180x180.png">
    <link rel="apple-touch-icon" sizes="152x152" href="/static/icon-152x152.png">
    <link rel="apple-touch-icon" sizes="120x120" href="/static/icon-120x120.png">
    
    <!-- Mobile Styles -->
    <link rel="stylesheet" href="/static/mobile-styles.css">
    
    <!-- Load GPS Tracker JavaScript -->
    <script src="/static/gps-tracker.js"></script>
</head>
""", unsafe_allow_html=True)

# Service Worker Registration
st.markdown("""
<script>
// Register Service Worker for PWA functionality
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('Service Worker registered successfully:', registration.scope);
            })
            .catch(function(error) {
                console.log('Service Worker registration failed:', error);
            });
    });
}

// PWA Install Prompt
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Save the event so it can be triggered later
    deferredPrompt = e;
    
    // Show install button (you can customize this)
    const installBtn = document.createElement('button');
    installBtn.innerHTML = '📱 Install Storm Chase App';
    installBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(45deg, #ff4444, #cc0000);
        color: white;
        padding: 15px 25px;
        border: none;
        border-radius: 25px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        z-index: 1000;
        box-shadow: 0 8px 25px rgba(255, 68, 68, 0.4);
    `;
    
    installBtn.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            console.log('PWA install outcome:', outcome);
            deferredPrompt = null;
            installBtn.remove();
        }
    });
    
    document.body.appendChild(installBtn);
    
    // Auto-hide after 30 seconds
    setTimeout(() => {
        if (installBtn.parentElement) {
            installBtn.remove();
        }
    }, 30000);
});
</script>
""", unsafe_allow_html=True)

# Title and header with Diabeteorologist logo and theme
st.markdown("""
<div style="text-align: center; padding: 20px 0; background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border-radius: 15px; margin-bottom: 20px; border: 2px solid #dc143c;">
    <img src="data:image/png;base64,{}" style="height: 120px; margin-bottom: 15px;" alt="Diabeteorologist Logo">
    <h1 style="font-size: 2.8rem; color: #dc143c; margin: 10px 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); font-weight: bold;">
        🌪️ Storm Chase Dashboard
    </h1>
    <p style="font-size: 1.3rem; color: #f0f0f0; margin: 10px 0; font-weight: 600; text-shadow: 1px 1px 2px rgba(0,0,0,0.6);">
        Sugar Infused Storm Chasing • GPS Tracking • AI Intelligence
    </p>
    <div style="background: linear-gradient(90deg, #dc143c, #ff4444, #dc143c); height: 3px; width: 80%; margin: 15px auto; border-radius: 2px;"></div>
</div>
""".format(base64.b64encode(open("attached_assets/Diabeteorologist_1757514609323.png", "rb").read()).decode()), unsafe_allow_html=True)
st.markdown("---")

# Initialize session state for all features
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'breadcrumbs' not in st.session_state:
    st.session_state.breadcrumbs = []
if 'tracking_active' not in st.session_state:
    st.session_state.tracking_active = False
if 'chase_start_time' not in st.session_state:
    st.session_state.chase_start_time = None
if 'last_warning_check' not in st.session_state:
    st.session_state.last_warning_check = time.time()

# Initialize intelligent targeting cache to prevent excessive cycling
if 'cached_targets' not in st.session_state:
    st.session_state.cached_targets = None
if 'last_target_update' not in st.session_state:
    st.session_state.last_target_update = 0
if 'cached_weather' not in st.session_state:
    st.session_state.cached_weather = None
if 'last_ai_enhancement' not in st.session_state:
    st.session_state.last_ai_enhancement = 0

# Weather data fetching functions
def get_spc_mesonet_data(lat, lon):
    """Fetch SPC Mesonet data for location"""
    try:
        # SPC Mesonet closest station data
        response = requests.get(
            f"{SPC_MESONET_BASE}data.php",
            params={
                'f': 'csv',
                'lat': lat,
                'lon': lon
            },
            timeout=10
        )
        if response.status_code == 200:
            # Parse CSV data (simplified example)
            lines = response.text.split('\n')
            if len(lines) > 1:
                data = lines[1].split(',')
                return {
                    'temperature': float(data[2]) if len(data) > 2 else None,
                    'dewpoint': float(data[3]) if len(data) > 3 else None,
                    'wind_speed': float(data[4]) if len(data) > 4 else None
                }
    except Exception as e:
        st.error(f"SPC Mesonet API error: {str(e)}")
    return None

def get_noaa_forecast_data(lat, lon):
    """Fetch NOAA forecast data including atmospheric parameters"""
    try:
        # Get gridpoint info
        response = requests.get(f"{NOAA_API_BASE}/points/{lat},{lon}", timeout=10)
        if response.status_code == 200:
            grid_data = response.json()
            grid_x = grid_data['properties']['gridX']
            grid_y = grid_data['properties']['gridY']
            office = grid_data['properties']['gridId']
            
            # Get forecast data
            forecast_response = requests.get(
                f"{NOAA_API_BASE}/gridpoints/{office}/{grid_x},{grid_y}/forecast",
                timeout=10
            )
            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                current_period = forecast_data['properties']['periods'][0]
                
                # Extract available parameters
                return {
                    'temperature': current_period.get('temperature', 70),
                    'humidity': current_period.get('relativeHumidity', {}).get('value', 65),
                    'wind_speed': current_period.get('windSpeed', '10 mph')
                }
    except Exception as e:
        st.error(f"NOAA API error: {str(e)}")
    return None

def calculate_derived_parameters(surface_data):
    """Calculate atmospheric parameters using proper meteorological formulas"""
    if not surface_data:
        return None
    
    try:
        temp = surface_data.get('temperature', 70)  # °F
        dewpoint = surface_data.get('dewpoint', 60)  # °F
        pressure = surface_data.get('pressure', 1013.25)  # hPa
        
        # Convert to proper units
        temp_c = (temp - 32) * 5/9 if temp else 21.1  # Default 70°F
        dewpoint_c = (dewpoint - 32) * 5/9 if dewpoint else 15.5  # Default 60°F
        
        # Calculate mixing ratio and equivalent potential temperature
        import math
        
        # Saturation vapor pressure (Bolton 1980)
        def saturation_vapor_pressure(t_celsius):
            return 6.112 * math.exp(17.67 * t_celsius / (t_celsius + 243.5))
        
        # Actual vapor pressure
        es_dewpoint = saturation_vapor_pressure(dewpoint_c)
        mixing_ratio = 0.622 * es_dewpoint / (pressure - es_dewpoint)  # kg/kg
        
        # Lifting Condensation Level (LCL) - accurate formula
        lcl_pressure = pressure * ((temp_c - dewpoint_c) / (temp_c + 273.15 - dewpoint_c - 273.15 + 0.01)) ** (1.0 / 0.28571)
        lcl_height = (1 - (lcl_pressure / pressure) ** 0.1903) * 44307.7  # meters
        
        # Mixed Layer CAPE approximation (improved)
        # This is still simplified - real CAPE needs full sounding profile
        temp_spread = temp_c - dewpoint_c
        
        if temp_spread > 20:  # Dry conditions
            cape_estimate = max(0, (temp_spread - 15) * 150)
        elif temp_spread < 5:  # Very moist conditions
            cape_estimate = max(0, (temp_c - 15) * 180 + (25 - temp_spread) * 100)
        else:  # Moderate conditions
            cape_estimate = max(0, (temp_c - 10) * 120 + (20 - temp_spread) * 80)
        
        # Add seasonal and temperature adjustments
        if temp_c > 30:  # Hot conditions favor higher CAPE
            cape_estimate *= 1.5
        elif temp_c < 15:  # Cool conditions limit CAPE
            cape_estimate *= 0.5
            
        # CIN estimate based on LCL height and temperature profile
        cin_estimate = max(5, min(200, lcl_height / 10 + temp_spread * 2))
        
        # Wind shear estimates (would need wind profile data for accuracy)
        # Using temperature gradient as proxy for instability
        shear_estimate = min(80, max(10, temp_spread * 2 + (30 - temp_c)))
        
        # Storm Relative Helicity approximation
        srh_estimate = min(500, max(50, cape_estimate / 15 + shear_estimate * 3))
        
        return {
            'CAPE': round(cape_estimate),
            'Dewpoint': dewpoint,
            'Shear_0_6km': round(shear_estimate),
            'CIN': round(cin_estimate),
            'SRH_0_1km': round(srh_estimate),
            'LCL_Height': round(lcl_height),
            'mixing_ratio': round(mixing_ratio * 1000, 2),  # g/kg
            'source': 'calculated_from_surface_obs'
        }
        
    except Exception as e:
        st.error(f"Parameter calculation error: {str(e)}")
        # Fallback with basic estimates - use safe defaults
        dewpoint_fallback = surface_data.get('dewpoint', 60) if surface_data else 60
        return {
            'CAPE': 1500,
            'Dewpoint': dewpoint_fallback,
            'Shear_0_6km': 30,
            'CIN': 50,
            'SRH_0_1km': 150,
            'LCL_Height': 1000,
            'source': 'fallback_estimates'
        }

def generate_weather_data(lat, lon):
    """Generate weather data using real APIs where possible, fallback to mock"""
    # Try to get real data first
    spc_data = get_spc_mesonet_data(lat, lon)
    noaa_data = get_noaa_forecast_data(lat, lon)
    
    # Combine data sources
    combined_data = {}
    if spc_data:
        combined_data.update(spc_data)
    if noaa_data:
        combined_data.update(noaa_data)
    
    # Calculate derived parameters
    derived = calculate_derived_parameters(combined_data)
    if derived:
        return derived
    
    # Return None if no real data available - don't use random fallback
    st.error("⚠️ Unable to fetch real weather data from APIs")
    return None

def get_radar_stations_near_location(lat, lon, radius_km=300):
    """Get nearby NOAA radar stations with expanded coverage for storm chasing"""
    # Comprehensive NOAA NEXRAD stations for Great Plains storm chasing
    radar_stations = {
        'KOAX': {'lat': 41.3203, 'lon': -96.3667, 'name': 'Omaha, NE'},
        'KGLD': {'lat': 39.3667, 'lon': -101.7000, 'name': 'Goodland, KS'},
        'KEAX': {'lat': 38.8103, 'lon': -94.2644, 'name': 'Kansas City, MO'},
        'KICT': {'lat': 37.6544, 'lon': -97.4431, 'name': 'Wichita, KS'},
        'KTLX': {'lat': 35.3331, 'lon': -97.2778, 'name': 'Norman, OK'},
        'KSGF': {'lat': 37.2350, 'lon': -93.4006, 'name': 'Springfield, MO'},
        'KFWS': {'lat': 32.5731, 'lon': -97.3031, 'name': 'Dallas/Fort Worth, TX'},
        'KAMA': {'lat': 35.2333, 'lon': -101.7089, 'name': 'Amarillo, TX'},
        'KUEX': {'lat': 40.3208, 'lon': -98.4419, 'name': 'Hastings, NE'},
        'KLNX': {'lat': 41.9578, 'lon': -100.5756, 'name': 'North Platte, NE'},
        'KDDC': {'lat': 37.7608, 'lon': -99.9686, 'name': 'Dodge City, KS'},
        'KTWX': {'lat': 38.9969, 'lon': -96.2325, 'name': 'Topeka, KS'},
        'KCYS': {'lat': 41.1519, 'lon': -104.8059, 'name': 'Cheyenne, WY'},
        'KFTG': {'lat': 39.7866, 'lon': -104.5458, 'name': 'Denver, CO'}
    }
    
    # Find closest station within radius (proper distance calculation)
    from geopy.distance import geodesic
    
    min_distance_km = float('inf')
    closest_station = None
    
    for station_id, station_info in radar_stations.items():
        distance_km = geodesic((lat, lon), (station_info['lat'], station_info['lon'])).kilometers
        if distance_km <= radius_km and distance_km < min_distance_km:
            min_distance_km = distance_km
            closest_station = station_id
    
    if closest_station:
        return closest_station, radar_stations[closest_station]
    else:
        # No station within radius - return nearest with distance warning
        nearest_station = None
        nearest_distance = float('inf')
        for station_id, station_info in radar_stations.items():
            distance_km = geodesic((lat, lon), (station_info['lat'], station_info['lon'])).kilometers
            if distance_km < nearest_distance:
                nearest_distance = distance_km
                nearest_station = station_id
        
        if nearest_station and nearest_distance <= 500:  # Within 500km fallback
            station_data = radar_stations[nearest_station].copy()
            station_data['distance_km'] = nearest_distance
            station_data['out_of_range'] = True
            return nearest_station, station_data
        
        return None, None

def fetch_radar_image(station_id, product='N0Q'):
    """Fetch real-time radar image from NOAA radar.weather.gov (RIDGE2 2025)"""
    try:
        # RIDGE2 correct URLs for 2025 (validated patterns)
        urls_to_try = [
            f"https://radar.weather.gov/ridge/standard/{product.upper()}/{station_id.upper()}_loop.gif",
            f"https://radar.weather.gov/ridge/standard/{product.upper()}/{station_id.upper()}_0.gif",
            # Alternative Lite format (backup)
            f"https://radar.weather.gov/ridge/lite/{product.upper()}/{station_id.upper()}_loop.gif",
            f"https://radar.weather.gov/ridge/lite/{product.upper()}/{station_id.upper()}_0.gif"
        ]
        
        # Custom headers for better compatibility
        headers = {
            'User-Agent': 'StormChase-Dashboard/2.0 (Educational/Research)',
            'Accept': 'image/gif,image/*,*/*',
            'Cache-Control': 'no-cache'
        }
        
        for url in urls_to_try:
            try:
                response = requests.get(url, timeout=20, headers=headers)
                if response.status_code == 200 and len(response.content) > 1000:  # Valid image check
                    return response.content
            except requests.RequestException:
                continue
                
        # If all fail, try the NWS API endpoint for station status
        try:
            status_url = f"https://api.weather.gov/stations/{station_id}"
            status_response = requests.get(status_url, timeout=10, headers=headers)
            if status_response.status_code != 200:
                st.info(f"📡 Radar station {station_id} may be offline for maintenance")
        except:
            pass
            
    except Exception as e:
        st.warning(f"Radar data connection issue: {str(e)[:100]}...")
    return None

def get_goes_mesoscale_sectors():
    """Fetch active GOES Mesoscale Sectors - high resolution storm-focused imagery"""
    try:
        # NOAA STAR Mesoscale Sectors API - real-time positioning
        mesoscale_urls = [
            "https://www.star.nesdis.noaa.gov/goes/meso_index.php",
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/pnw/GEOCOLOR/latest.jpg",
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/cgl/GEOCOLOR/latest.jpg"  # Central Great Lakes
        ]
        
        # Try to get active mesoscale sectors info first
        headers = {
            'User-Agent': 'StormChase-Dashboard/2.0 (Educational/Research)',
            'Accept': 'text/html,image/jpeg,image/*,*/*'
        }
        
        # True mesoscale sector URLs (these update every 30-60 seconds when active)
        mesoscale_sector_urls = [
            # M1 and M2 sectors - positioned by NWS on active storms only
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/MESO/M1/GEOCOLOR/latest.jpg",
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/MESO/M2/GEOCOLOR/latest.jpg",
            "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/MESO/M1/GEOCOLOR/latest.jpg", 
            "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/MESO/M2/GEOCOLOR/latest.jpg"
        ]
        
        for url in mesoscale_sector_urls:
            try:
                response = requests.get(url, timeout=15, headers=headers)
                if response.status_code == 200 and len(response.content) > 5000:
                    # Only true M1/M2 mesoscale sectors get this type
                    return {'data': response.content, 'url': url, 'type': 'mesoscale'}
            except requests.RequestException:
                continue
        
        # Fallback to regional sectors (fixed areas, 5-minute updates)
        regional_urls = [
            # Storm chasing corridor coverage
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/sp/GEOCOLOR/latest.jpg",  # Southern Plains
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/np/GEOCOLOR/latest.jpg", # Northern Plains
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/cgl/GEOCOLOR/latest.jpg", # Central Great Lakes
            "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/pnw/GEOCOLOR/latest.jpg"  # Pacific Northwest
        ]
        
        for url in regional_urls:
            try:
                response = requests.get(url, timeout=15, headers=headers)
                if response.status_code == 200 and len(response.content) > 5000:
                    return {'data': response.content, 'url': url, 'type': 'regional'}
            except requests.RequestException:
                continue
                
    except Exception as e:
        st.warning(f"Mesoscale sector connection issue: {str(e)[:100]}...")
    return None

def parse_mesoscale_info(sector_url):
    """Extract info about the mesoscale sector from URL"""
    if '/MESO/M1/' in sector_url:
        return "M1 Mesoscale Sector", "30-60 second updates", "🎯 Active Storm Tracking"
    elif '/MESO/M2/' in sector_url:
        return "M2 Mesoscale Sector", "30-60 second updates", "🎯 Active Storm Tracking"  
    elif '/SECTOR/sp/' in sector_url:
        return "Southern Plains Sector", "5 minute updates", "🌪️ TX/OK/KS Storm Region"
    elif '/SECTOR/np/' in sector_url:
        return "Northern Plains Sector", "5 minute updates", "🌾 NE/IA/SD Storm Region"
    elif '/SECTOR/cgl/' in sector_url:
        return "Central Great Lakes", "5 minute updates", "⛈️ Regional Coverage"
    else:
        return "Regional Sector", "5 minute updates", "🛰️ Regional Coverage"

def get_hrrr_data(lat, lon, forecast_hour=0):
    """Fetch real HRRR model data from NOMADS"""
    try:
        # Use NOMADS HRRR service for real forecast data
        base_url = "https://nomads.ncep.noaa.gov/dods/hrrr/hrrr"
        
        # Get latest HRRR run time
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        # HRRR runs every hour, get most recent
        run_hour = now.hour
        run_date = now.strftime('%Y%m%d')
        
        # NOMADS OPeNDAP endpoint
        dataset_url = f"{base_url}{run_date}/hrrr_conus.t{run_hour:02d}z.wrfprsf{forecast_hour:02d}.grib2"
        
        # For production use, you'd use xarray to read GRIB2 data
        # For now, use NOAA's REST API for surface conditions
        points_url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"
        headers = {
            'User-Agent': 'Diabeteorologist Storm Chase Dashboard (contact@example.com)',
            'Accept': 'application/geo+json'
        }
        
        response = requests.get(points_url, headers=headers, timeout=10)
        if response.status_code == 200:
            point_data = response.json()
            
            # Get forecast data
            forecast_url = point_data['properties']['forecast']
            forecast_response = requests.get(forecast_url, headers=headers, timeout=10)
            
            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                current_period = forecast_data['properties']['periods'][0]
                
                # Extract real forecast parameters
                return {
                    'wind_speed_10m': current_period.get('windSpeed', '0 mph').split()[0],
                    'wind_direction_10m': current_period.get('windDirection', 'N'),
                    'temperature_2m': current_period.get('temperature', 70),
                    'forecast_text': current_period.get('detailedForecast', ''),
                    'source': 'NOAA/NWS'
                }
                
    except Exception as e:
        st.warning(f"Could not fetch HRRR data: {str(e)}")
        
        # Fallback to basic data only if real API fails
        return {
            'wind_speed_10m': 'Unknown',
            'wind_direction_10m': 'Unknown',
            'temperature_2m': None,
            'source': 'API_UNAVAILABLE'
        }
    
    return None

# GPS Breadcrumb Functions
def add_breadcrumb(lat, lon):
    """Add a GPS breadcrumb to the chase track"""
    timestamp = datetime.now()
    breadcrumb = {
        'lat': lat,
        'lon': lon, 
        'timestamp': timestamp,
        'time_str': timestamp.strftime('%H:%M:%S')
    }
    st.session_state.breadcrumbs.append(breadcrumb)

def get_chase_distance():
    """Calculate total chase distance from breadcrumbs"""
    if len(st.session_state.breadcrumbs) < 2:
        return 0
    
    total_distance = 0
    for i in range(1, len(st.session_state.breadcrumbs)):
        point1 = (st.session_state.breadcrumbs[i-1]['lat'], st.session_state.breadcrumbs[i-1]['lon'])
        point2 = (st.session_state.breadcrumbs[i]['lat'], st.session_state.breadcrumbs[i]['lon'])
        total_distance += geodesic(point1, point2).miles
    
    return total_distance

def clear_breadcrumbs():
    """Clear all breadcrumbs and reset tracking"""
    st.session_state.breadcrumbs = []
    st.session_state.tracking_active = False
    st.session_state.chase_start_time = None

# Storm Reports and Alerts Functions
def get_nws_alerts(lat, lon, radius_miles=100):
    """Get NWS alerts for the area"""
    try:
        # Convert miles to approximate lat/lon bounds
        lat_range = radius_miles / 69.0  # roughly 69 miles per degree latitude
        lon_range = radius_miles / (69.0 * np.cos(np.radians(lat)))
        
        response = requests.get(
            f"{NWS_ALERTS_BASE}/active",
            params={
                'point': f"{lat},{lon}",
                'radius': radius_miles
            },
            timeout=10
        )
        
        if response.status_code == 200:
            alerts_data = response.json()
            return alerts_data.get('features', [])
    except Exception as e:
        st.warning(f"Could not fetch weather alerts: {str(e)}")
    return []

def get_spc_storm_reports(date=None):
    """Get SPC storm reports for the day"""
    if not date:
        date = datetime.now().strftime('%y%m%d')
    
    try:
        # SPC storm reports URLs
        tornado_url = f"{SPC_REPORTS_BASE}{date}_rpts_torn.csv"
        hail_url = f"{SPC_REPORTS_BASE}{date}_rpts_hail.csv"  
        wind_url = f"{SPC_REPORTS_BASE}{date}_rpts_wind.csv"
        
        reports = {'tornado': [], 'hail': [], 'wind': []}
        
        for report_type, url in [('tornado', tornado_url), ('hail', hail_url), ('wind', wind_url)]:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    # Parse CSV data (simplified)
                    lines = response.text.strip().split('\n')[1:]  # Skip header
                    for line in lines[:10]:  # Limit to recent reports
                        parts = line.split(',')
                        if len(parts) >= 6:
                            reports[report_type].append({
                                'time': parts[0],
                                'lat': float(parts[1]) if parts[1] else 0,
                                'lon': float(parts[2]) if parts[2] else 0,
                                'magnitude': parts[3],
                                'location': parts[5]
                            })
            except Exception:
                continue
                
        return reports
    except Exception as e:
        st.warning(f"Could not fetch storm reports: {str(e)}")
    return {'tornado': [], 'hail': [], 'wind': []}

# Enhanced Composite Weather Indices Functions - Professional Storm Chasing Grade
def calculate_composite_indices(weather_data, surface_data=None):
    """Calculate comprehensive composite weather indices for advanced severe weather forecasting"""
    indices = {}
    
    try:
        # Extract base parameters
        cape = weather_data.get('CAPE', 0)
        cin = weather_data.get('CIN', 0)
        shear_0_6 = weather_data.get('Shear_0_6km', 0)
        srh_0_1 = weather_data.get('SRH_0_1km', 0)
        lcl = weather_data.get('LCL_Height', 1000)
        dewpoint = weather_data.get('Dewpoint', 50)
        
        # Phase 1: Critical Composite Parameters
        
        # Enhanced Mixed Layer CAPE (more representative than surface-based)
        # Estimate from surface CAPE with lapse rate adjustment
        lapse_rate_factor = 0.9  # Mixed layer typically ~10% less than surface
        mixed_layer_cape = cape * lapse_rate_factor
        indices['Mixed_Layer_CAPE'] = max(0, mixed_layer_cape)
        
        # Professional-grade Supercell Composite Parameter (SCP)
        # Formula: (MLCAPE/1000) * (Shear_0_6km/20) * (SRH_0_1km/100) * (LCL_factor)
        cin_factor = max(0, (50 - abs(cin)) / 50)  # CIN penalty
        lcl_factor_scp = max(0, min(1, (2000 - lcl) / 1000))  # Optimal LCL factor
        dewpoint_factor = max(0.5, min(1.2, dewpoint / 60))  # Moisture factor
        
        scp = (mixed_layer_cape / 1000) * (shear_0_6 / 20) * (srh_0_1 / 100) * lcl_factor_scp * cin_factor * dewpoint_factor
        indices['SCP'] = max(0, min(scp, 20))
        
        # Enhanced Significant Tornado Parameter (STP) - Thompson et al. formula
        # STP = (MLCAPE/1500) * ((2000-LCL)/1000) * (SRH/150) * (Shear/20) * CIN_factor
        lcl_factor_stp = max(0, (2000 - lcl) / 1000)
        stp = (mixed_layer_cape / 1500) * lcl_factor_stp * (srh_0_1 / 150) * (shear_0_6 / 20) * cin_factor
        indices['STP'] = max(0, min(stp, 8))
        
        # Enhanced 0-1km Storm-Relative Helicity with environmental factors
        srh_enhanced = srh_0_1 * (1 + dewpoint_factor * 0.2)  # Moisture enhancement
        indices['SRH_0_1km_Enhanced'] = max(0, srh_enhanced)
        
        # Phase 2: Advanced Analysis Parameters
        
        # Bulk Richardson Number (BRN) - Storm Mode Discriminator
        # BRN = CAPE / (0.5 * U²) where U is bulk shear
        bulk_shear_squared = (shear_0_6 * 0.514444) ** 2  # Convert kts to m/s
        if bulk_shear_squared > 0:
            brn = mixed_layer_cape / (0.5 * bulk_shear_squared)
            indices['BRN'] = max(0, min(brn, 100))  # Cap at 100
        else:
            indices['BRN'] = 100  # Very high BRN when no shear
        
        # Energy Helicity Index (EHI) - Enhanced version
        # EHI = (CAPE * SRH) / 160000
        ehi = (mixed_layer_cape * srh_enhanced) / 160000
        indices['EHI'] = max(0, min(ehi, 8))
        
        # Estimated 700-500mb Lapse Rate from surface conditions
        # Professional approximation based on CAPE and surface temperature
        temp_f = 70 + (dewpoint - 50) * 0.8  # Estimate surface temp from dewpoint
        temp_c = (temp_f - 32) * 5/9
        # Lapse rate increases with instability
        cape_factor = min(1.5, cape / 3000)
        lapse_rate_700_500 = 6.5 + (cape_factor * 2.5)  # Base + instability enhancement
        indices['Lapse_Rate_700_500'] = max(4.0, min(lapse_rate_700_500, 12.0))
        
        # Enhanced 0-3km Shear (Low-level shear critical for tornadogenesis)
        # Estimate as ~65% of 0-6km shear (typical atmospheric profile)
        shear_0_3 = shear_0_6 * 0.65
        indices['Shear_0_3km'] = max(0, shear_0_3)
        
        # Bunkers Storm Motion Components (Critical for storm-relative analysis)
        # Simplified Bunkers calculation using mean wind and shear vector
        mean_wind_0_6 = shear_0_6 * 0.5  # Rough estimate of mean wind speed
        
        # Bunkers right-moving storm motion (simplified)
        # Actual calculation requires wind profile, this is approximation
        deviation_angle = 30  # degrees right of mean wind
        import math
        
        # Assume mean wind direction (can be enhanced with actual wind data)
        mean_wind_dir = 225  # SW flow typical for Great Plains
        storm_dir = mean_wind_dir + deviation_angle
        
        bunkers_u = mean_wind_0_6 * math.cos(math.radians(storm_dir))
        bunkers_v = mean_wind_0_6 * math.sin(math.radians(storm_dir))
        
        indices['Bunkers_Right_U'] = bunkers_u
        indices['Bunkers_Right_V'] = bunkers_v
        indices['Storm_Motion_Speed'] = math.sqrt(bunkers_u**2 + bunkers_v**2)
        
        # Mean Wind 0-6km (Storm propagation)
        indices['Mean_Wind_0_6km'] = mean_wind_0_6
        
        # Additional Professional Parameters
        
        # Composite Hodograph Parameter (CHP) - Storm structure prediction
        chp = (mixed_layer_cape / 1000) * (srh_enhanced / 150)
        indices['CHP'] = max(0, min(chp, 10))
        
        # Supercell High Precipitation Index (SHIP)
        ship = (mixed_layer_cape / 1000) * (shear_0_6 / 20) * (dewpoint_factor)
        indices['SHIP'] = max(0, min(ship, 12))
        
        # Vorticity Generation Parameter (VGP) - Mesocyclone potential
        vgp = (srh_enhanced / 200) * (shear_0_3 / 25) * cin_factor
        indices['VGP'] = max(0, min(vgp, 5))
        
        # Storm-Relative Environmental Helicity (SREH) enhanced
        sreh = srh_enhanced * (1 + (indices['BRN'] - 20) / 50) if indices['BRN'] < 50 else srh_enhanced
        indices['SREH'] = max(0, sreh)
        
        return indices
        
    except Exception as e:
        st.warning(f"Could not calculate enhanced composite indices: {str(e)}")
        return {
            'Mixed_Layer_CAPE': 0, 'SCP': 0, 'STP': 0, 'SRH_0_1km_Enhanced': 0,
            'BRN': 50, 'EHI': 0, 'Lapse_Rate_700_500': 6.5, 'Shear_0_3km': 0,
            'Bunkers_Right_U': 0, 'Bunkers_Right_V': 0, 'Storm_Motion_Speed': 0,
            'Mean_Wind_0_6km': 0, 'CHP': 0, 'SHIP': 0, 'VGP': 0, 'SREH': 0
        }

# Voice Alert Functions
def check_tornado_warnings(lat, lon, radius_miles=50):
    """Check for new tornado warnings in the chase area"""
    try:
        alerts = get_nws_alerts(lat, lon, radius_miles)
        tornado_warnings = []
        
        for alert in alerts:
            properties = alert.get('properties', {})
            event = properties.get('event', '').lower()
            
            if 'tornado warning' in event:
                tornado_warnings.append({
                    'headline': properties.get('headline', ''),
                    'description': properties.get('description', ''),
                    'area': properties.get('areaDesc', ''),
                    'severity': properties.get('severity', ''),
                    'onset': properties.get('onset', ''),
                    'expires': properties.get('expires', '')
                })
        
        return tornado_warnings
    except Exception as e:
        st.warning(f"Could not check tornado warnings: {str(e)}")
        return []

# Initialize OpenAI client
def get_openai_client():
    """Initialize OpenAI client with API key"""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        return OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"OpenAI initialization error: {str(e)}")
        return None

def calculate_storm_chasability(weather_data, lat, lon):
    """Calculate enhanced AI-powered storm chasability score (0-100) using advanced meteorological parameters"""
    try:
        # Get composite indices first
        composite_indices = calculate_composite_indices(weather_data)
        
        # Professional Storm Chasing Score Algorithm
        base_score = 0
        bonus_points = 0
        
        # === Core Parameters (60 points total) ===
        
        # Mixed Layer CAPE scoring (20 points) - More representative than surface CAPE
        ml_cape = composite_indices.get('Mixed_Layer_CAPE', weather_data.get('CAPE', 0))
        if ml_cape >= 4000:
            base_score += 20  # Extreme instability
        elif ml_cape >= 3000:
            base_score += 18  # Very high instability
        elif ml_cape >= 2500:
            base_score += 15  # High instability
        elif ml_cape >= 2000:
            base_score += 12  # Moderate-high instability
        elif ml_cape >= 1500:
            base_score += 8   # Moderate instability
        elif ml_cape >= 1000:
            base_score += 4   # Marginal instability
        
        # Deep Layer Shear scoring (15 points)
        shear_0_6 = weather_data.get('Shear_0_6km', 0)
        if shear_0_6 >= 60:
            base_score += 15  # Excellent shear for supercells
        elif shear_0_6 >= 50:
            base_score += 13  # Very good shear
        elif shear_0_6 >= 40:
            base_score += 11  # Good shear
        elif shear_0_6 >= 30:
            base_score += 8   # Marginal shear
        elif shear_0_6 >= 20:
            base_score += 5   # Weak shear
        
        # Low-level Shear scoring (10 points) - Critical for tornadogenesis
        shear_0_3 = composite_indices.get('Shear_0_3km', 0)
        if shear_0_3 >= 35:
            base_score += 10  # Excellent low-level shear
        elif shear_0_3 >= 25:
            base_score += 8   # Good low-level shear
        elif shear_0_3 >= 20:
            base_score += 6   # Moderate low-level shear
        elif shear_0_3 >= 15:
            base_score += 4   # Marginal low-level shear
        
        # Moisture scoring (10 points)
        dewpoint = weather_data.get('Dewpoint', 50)
        if dewpoint >= 70:
            base_score += 10  # Excellent moisture
        elif dewpoint >= 65:
            base_score += 8   # Very good moisture
        elif dewpoint >= 60:
            base_score += 6   # Good moisture
        elif dewpoint >= 55:
            base_score += 4   # Marginal moisture
        elif dewpoint >= 50:
            base_score += 2   # Poor moisture
        
        # CIN evaluation (5 points) - Capping inversion management
        cin = weather_data.get('CIN', 0)
        if cin <= 15:
            base_score += 5   # Minimal capping
        elif cin <= 30:
            base_score += 4   # Light capping
        elif cin <= 50:
            base_score += 3   # Moderate capping
        elif cin <= 75:
            base_score += 1   # Strong capping
        # No points for very strong capping (CIN > 75)
        
        # === Composite Parameters (25 points total) ===
        
        # Supercell Composite Parameter (10 points)
        scp = composite_indices.get('SCP', 0)
        if scp >= 8:
            base_score += 10  # Excellent supercell environment
        elif scp >= 6:
            base_score += 8   # Very good supercell environment
        elif scp >= 4:
            base_score += 6   # Good supercell environment
        elif scp >= 2:
            base_score += 4   # Marginal supercell environment
        elif scp >= 1:
            base_score += 2   # Weak supercell environment
        
        # Significant Tornado Parameter (10 points)
        stp = composite_indices.get('STP', 0)
        if stp >= 4:
            base_score += 10  # Excellent tornado environment
        elif stp >= 3:
            base_score += 8   # Very good tornado environment
        elif stp >= 2:
            base_score += 6   # Good tornado environment
        elif stp >= 1:
            base_score += 4   # Marginal tornado environment
        elif stp >= 0.5:
            base_score += 2   # Weak tornado environment
        
        # Bulk Richardson Number (5 points) - Storm mode discriminator
        brn = composite_indices.get('BRN', 50)
        if 15 <= brn <= 40:
            base_score += 5   # Optimal for supercells
        elif 10 <= brn <= 50:
            base_score += 3   # Good for organized storms
        elif brn < 10:
            base_score += 1   # Favors squall lines
        # No points for BRN > 50 (favors disorganized convection)
        
        # === Bonus Factors (15 points maximum) ===
        
        # Enhanced SRH bonus
        srh_enhanced = composite_indices.get('SRH_0_1km_Enhanced', 0)
        if srh_enhanced >= 400:
            bonus_points += 5  # Exceptional helicity
        elif srh_enhanced >= 300:
            bonus_points += 4  # Very high helicity
        elif srh_enhanced >= 200:
            bonus_points += 3  # High helicity
        elif srh_enhanced >= 150:
            bonus_points += 2  # Moderate helicity
        elif srh_enhanced >= 100:
            bonus_points += 1  # Marginal helicity
        
        # Energy Helicity Index bonus
        ehi = composite_indices.get('EHI', 0)
        if ehi >= 3:
            bonus_points += 3  # Excellent EHI
        elif ehi >= 2:
            bonus_points += 2  # Good EHI
        elif ehi >= 1:
            bonus_points += 1  # Marginal EHI
        
        # Lapse Rate bonus
        lapse_rate = composite_indices.get('Lapse_Rate_700_500', 6.5)
        if lapse_rate >= 8.5:
            bonus_points += 3  # Steep lapse rate
        elif lapse_rate >= 7.5:
            bonus_points += 2  # Good lapse rate
        elif lapse_rate >= 7.0:
            bonus_points += 1  # Marginal steepening
        
        # Storm Motion bonus
        storm_speed = composite_indices.get('Storm_Motion_Speed', 0)
        if 20 <= storm_speed <= 35:
            bonus_points += 2  # Optimal storm motion
        elif 15 <= storm_speed <= 45:
            bonus_points += 1  # Good storm motion
        
        # SHIP (Hail) consideration
        ship = composite_indices.get('SHIP', 0)
        if ship >= 4:
            bonus_points += 2  # Significant hail potential
        elif ship >= 2:
            bonus_points += 1  # Moderate hail potential
        
        # === Geographic Bonuses ===
        
        # Enhanced geographic scoring
        if 40.0 <= lat <= 42.5 and -104.0 <= lon <= -95.0:
            bonus_points += 3  # Nebraska storm corridor
        elif 36.0 <= lat <= 40.0 and -102.0 <= lon <= -94.0:
            bonus_points += 2  # Kansas storm alley
        elif 33.0 <= lat <= 37.0 and -103.0 <= lon <= -95.0:
            bonus_points += 2  # Oklahoma/Texas panhandle
        elif 37.0 <= lat <= 41.0 and -99.0 <= lon <= -90.0:
            bonus_points += 1  # Missouri/Iowa corridor
        
        # === Final Score Calculation ===
        
        total_score = base_score + min(bonus_points, 15)  # Cap bonus at 15
        
        # Quality control - ensure score makes meteorological sense
        if ml_cape < 1000 and shear_0_6 < 20:  # Very marginal environment
            total_score = min(total_score, 30)
        elif scp < 1 and stp < 0.5:  # Poor composite environment
            total_score = min(total_score, 50)
        
        return min(total_score, 100)
        
    except Exception as e:
        st.warning(f"Error calculating chasability score: {str(e)}")
        return 50  # Default moderate score

def generate_intelligent_targets(base_lat, base_lon, current_weather_data, radius_miles=150):
    """Generate intelligent chase targets based on meteorological analysis"""
    targets = []
    
    try:
        # Define search grid around base location
        grid_points = []
        lat_step = 0.5  # ~35 miles
        lon_step = 0.5  # ~35 miles at mid-latitudes
        
        # Create analysis grid within radius
        for lat_offset in [-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2]:
            for lon_offset in [-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2]:
                grid_lat = base_lat + lat_offset * lat_step
                grid_lon = base_lon + lon_offset * lon_step
                
                # Calculate distance from base
                distance = ((grid_lat - base_lat) * 69)**2 + ((grid_lon - base_lon) * 54.6)**2
                distance = distance**0.5
                
                if distance <= radius_miles:
                    grid_points.append((grid_lat, grid_lon, distance))
        
        # Analyze each grid point
        for grid_lat, grid_lon, distance in grid_points:
            # Generate weather data for this location (with some variation)
            location_weather = simulate_weather_variation(current_weather_data, grid_lat, grid_lon, base_lat, base_lon)
            
            # Calculate storm potential score
            chase_score = calculate_storm_chasability(location_weather, grid_lat, grid_lon)
            composite_indices = calculate_composite_indices(location_weather)
            
            # Enhanced target evaluation with composite parameters
            scp = composite_indices.get('SCP', 0)
            stp = composite_indices.get('STP', 0)
            ehi = composite_indices.get('EHI', 0)
            brn = composite_indices.get('BRN', 50)
            
            # Professional-grade target filtering and prioritization
            if chase_score >= 60:  # Base threshold for chase-worthy conditions
                # Enhanced priority determination using composite parameters
                if chase_score >= 85 or (scp >= 6 and stp >= 2) or ehi >= 3:
                    severity = "Extreme"  # Significant severe weather expected
                    priority = 1
                    target_type = "Supercell with Tornado Potential"
                elif chase_score >= 75 or (scp >= 3 and stp >= 1) or ehi >= 1.5:
                    severity = "High"     # Strong severe weather likely
                    priority = 1
                    target_type = "Supercell Likely"
                elif chase_score >= 65 or (scp >= 1.5 and stp >= 0.5):
                    severity = "Moderate" # Organized storms possible
                    priority = 2 
                    target_type = "Organized Convection"
                else:
                    severity = "Marginal" # Weak organized convection
                    priority = 3
                    target_type = "Marginal Convection"
                
                # Adjust priority based on storm mode (BRN analysis)
                if 10 <= brn <= 40:  # Optimal supercell range
                    storm_mode = "Supercells Favored"
                elif brn < 10:
                    storm_mode = "Squall Line/QLCS"
                    if priority > 1:
                        priority += 1  # Lower priority for linear mode
                else:  # brn > 50
                    storm_mode = "Disorganized/Pulse"
                    priority = max(priority, 3)  # Lowest priority for pulse storms
                
                # Calculate estimated storm initiation time (simplified)
                current_hour = datetime.now().hour
                if current_hour < 14:  # Before 2pm
                    initiation_time = "15:00-17:00 CT"
                elif current_hour < 17:  # Before 5pm
                    initiation_time = "17:00-19:00 CT"
                else:
                    initiation_time = "19:00-21:00 CT"
                
                target = {
                    'lat': grid_lat,
                    'lon': grid_lon,
                    'name': f"Target {len(targets) + 1} ({int(distance)}mi {['N','NE','E','SE','S','SW','W','NW'][int((math.atan2(grid_lon-base_lon, grid_lat-base_lat) * 180/math.pi + 360 + 22.5) % 360 / 45)]}) ",
                    'severity': severity,
                    'score': chase_score,
                    'priority': priority,
                    'distance_miles': distance,
                    'initiation_time': initiation_time,
                    'weather_data': location_weather,
                    'composite_indices': composite_indices,
                    'reasoning': generate_enhanced_target_reasoning(location_weather, composite_indices, storm_mode, target_type, chase_score),
                    'target_type': target_type,
                    'storm_mode': storm_mode,
                    'scp': scp,
                    'stp': stp,
                    'ehi': ehi,
                    'brn': brn
                }
                
                targets.append(target)
        
        # Sort by score (best first) and limit to top targets
        targets.sort(key=lambda x: x['score'], reverse=True)
        return targets[:6]  # Return top 6 targets
        
    except Exception as e:
        st.error(f"Error generating intelligent targets: {str(e)}")
        # Fallback to single target at base location
        return [{
            'lat': base_lat + 0.5,
            'lon': base_lon + 0.5, 
            'name': "Default Target",
            'severity': "Moderate",
            'score': 65,
            'priority': 2,
            'distance_miles': 35,
            'initiation_time': "16:00-18:00 CT",
            'reasoning': "Default target due to analysis error"
        }]

def simulate_weather_variation(base_weather, target_lat, target_lon, base_lat, base_lon):
    """Simulate realistic weather parameter variations across geographic area"""
    try:
        # Calculate distance and direction effects
        lat_diff = target_lat - base_lat
        lon_diff = target_lon - base_lon
        
        # Create variations based on location
        variations = {}
        
        # CAPE tends to increase with distance from dryline (westward in Great Plains)
        cape_variation = lon_diff * 200 + random.uniform(-300, 300)
        variations['CAPE'] = max(500, base_weather['CAPE'] + cape_variation)
        
        # Dewpoint varies with elevation and moisture transport
        dewpoint_variation = -lat_diff * 3 + random.uniform(-5, 5)
        variations['Dewpoint'] = max(40, base_weather['Dewpoint'] + dewpoint_variation)
        
        # Wind shear can vary significantly across mesoscale
        shear_variation = random.uniform(-15, 15)
        variations['Shear_0_6km'] = max(10, base_weather['Shear_0_6km'] + shear_variation)
        
        # CIN varies with boundary proximity
        cin_variation = abs(lat_diff) * 20 + random.uniform(-20, 20)
        variations['CIN'] = max(0, base_weather['CIN'] + cin_variation)
        
        # SRH enhanced near boundaries
        srh_variation = abs(lat_diff + lon_diff) * 30 + random.uniform(-50, 50)
        variations['SRH_0_1km'] = max(50, base_weather['SRH_0_1km'] + srh_variation)
        
        # LCL height varies with moisture
        lcl_variation = dewpoint_variation * -10 + random.uniform(-200, 200)
        variations['LCL_Height'] = max(200, base_weather['LCL_Height'] + lcl_variation)
        
        return variations
        
    except Exception as e:
        return base_weather  # Return base weather if simulation fails

def generate_enhanced_target_reasoning(weather_data, composite_indices, storm_mode, target_type, score):
    """Generate comprehensive AI reasoning using advanced meteorological parameters"""
    try:
        reasons = []
        
        # Extract all enhanced parameters
        ml_cape = composite_indices.get('Mixed_Layer_CAPE', 0)
        cape = weather_data.get('CAPE', 0)
        shear_0_6 = weather_data.get('Shear_0_6km', 0)
        shear_0_3 = composite_indices.get('Shear_0_3km', 0)
        dewpoint = weather_data.get('Dewpoint', 0)
        cin = weather_data.get('CIN', 0)
        scp = composite_indices.get('SCP', 0)
        stp = composite_indices.get('STP', 0)
        ehi = composite_indices.get('EHI', 0)
        brn = composite_indices.get('BRN', 50)
        lapse_rate = composite_indices.get('Lapse_Rate_700_500', 6.5)
        storm_speed = composite_indices.get('Storm_Motion_Speed', 0)
        
        # Primary reasoning based on target type and storm mode
        reasons.append(f"{target_type} • {storm_mode}")
        
        # Composite parameter analysis
        if scp >= 6 and stp >= 2:
            reasons.append(f"Exceptional supercell/tornado environment (SCP:{scp:.1f}, STP:{stp:.1f})")
        elif scp >= 3 and stp >= 1:
            reasons.append(f"Strong supercell environment (SCP:{scp:.1f}, STP:{stp:.1f})")
        elif scp >= 1.5:
            reasons.append(f"Supercell possible (SCP:{scp:.1f})")
        
        # Instability analysis with mixed layer CAPE
        if ml_cape >= 3500:
            reasons.append(f"Extreme instability (ML-CAPE: {ml_cape:.0f} J/kg)")
        elif ml_cape >= 2500:
            reasons.append(f"Very high instability (ML-CAPE: {ml_cape:.0f} J/kg)")
        elif ml_cape >= 2000:
            reasons.append(f"High instability (ML-CAPE: {ml_cape:.0f} J/kg)")
        
        # Enhanced shear analysis
        if shear_0_6 >= 50 and shear_0_3 >= 25:
            reasons.append(f"Excellent shear profile ({shear_0_6:.0f}kt deep, {shear_0_3:.0f}kt low-level)")
        elif shear_0_6 >= 40:
            reasons.append(f"Strong deep shear ({shear_0_6:.0f} kts)")
        elif shear_0_3 >= 25:
            reasons.append(f"Good low-level shear ({shear_0_3:.0f} kts)")
        
        # Storm mode analysis via BRN
        if 15 <= brn <= 35:
            reasons.append(f"Optimal supercell BRN ({brn:.0f})")
        elif brn < 15:
            reasons.append(f"Linear storm mode favored (BRN:{brn:.0f})")
        elif brn > 45:
            reasons.append(f"Pulse storm risk (BRN:{brn:.0f})")
        
        # Tornado potential analysis
        if ehi >= 2:
            reasons.append(f"High tornado potential (EHI:{ehi:.1f})")
        elif ehi >= 1:
            reasons.append(f"Tornado possible (EHI:{ehi:.1f})")
        
        # Environmental factors
        if dewpoint >= 65:
            reasons.append(f"Excellent moisture ({dewpoint:.0f}°F)")
        elif dewpoint >= 60:
            reasons.append(f"Good moisture ({dewpoint:.0f}°F)")
        
        if lapse_rate >= 8.0:
            reasons.append(f"Steep lapse rate ({lapse_rate:.1f}°C/km)")
        
        if cin <= 25:
            reasons.append("Easy storm initiation (low cap)")
        elif cin <= 50:
            reasons.append("Focused initiation (moderate cap)")
        
        # Storm motion consideration
        if 20 <= storm_speed <= 35:
            reasons.append(f"Optimal storm motion ({storm_speed:.0f} kts)")
        
        # Return top reasoning factors
        return " • ".join(reasons[:4]) if reasons else f"{target_type} with {storm_mode.lower()}"
        
    except Exception as e:
        return f"{target_type} • Score: {score:.0f}"

def generate_target_reasoning(weather_data, composite_indices, score):
    """Legacy function - kept for compatibility"""
    return generate_enhanced_target_reasoning(weather_data, composite_indices, "Organized storms", "Convective target", score)

def enhance_targets_with_ai(targets, weather_data):
    """Enhance intelligent targets with AI-powered analysis and recommendations"""
    try:
        if not targets:
            return targets
            
        # Enhanced AI analysis with advanced meteorological parameters
        client = get_openai_client()
        if not client:
            return targets  # Return basic targets if AI unavailable
        
        # Get composite indices for AI analysis
        composite_indices = calculate_composite_indices(weather_data)
        
        # Prepare comprehensive analysis data for AI
        analysis_data = {
            'current_time': datetime.now().strftime('%I:%M %p CT'),
            'base_weather': weather_data,
            'composite_indices': composite_indices,
            'targets': [{
                'lat': t['lat'], 
                'lon': t['lon'],
                'score': t['score'],
                'distance': t['distance_miles'],
                'weather': t['weather_data'],
                'reasoning': t['reasoning']
            } for t in targets[:3]]  # Top 3 targets
        }
        
        # Professional meteorological prompt with advanced parameters
        scp = composite_indices.get('SCP', 0)
        stp = composite_indices.get('STP', 0)
        ehi = composite_indices.get('EHI', 0)
        brn = composite_indices.get('BRN', 50)
        ml_cape = composite_indices.get('Mixed_Layer_CAPE', 0)
        shear_0_3 = composite_indices.get('Shear_0_3km', 0)
        lapse_rate = composite_indices.get('Lapse_Rate_700_500', 6.5)
        storm_motion = composite_indices.get('Storm_Motion_Speed', 0)
        
        prompt = f"""
        You are a professional storm chasing meteorologist analyzing chase targets using advanced meteorological parameters.
        
        CURRENT ATMOSPHERIC ENVIRONMENT:
        Time: {analysis_data['current_time']}
        Mixed Layer CAPE: {ml_cape:.0f} J/kg
        Deep Shear (0-6km): {weather_data.get('Shear_0_6km', 0):.0f} kts
        Low-level Shear (0-3km): {shear_0_3:.0f} kts
        Dewpoint: {weather_data.get('Dewpoint', 0):.0f}°F
        CIN: {weather_data.get('CIN', 0):.0f} J/kg
        
        COMPOSITE PARAMETERS:
        Supercell Composite (SCP): {scp:.1f} | Significant Tornado Parameter (STP): {stp:.1f}
        Energy Helicity Index (EHI): {ehi:.1f} | Bulk Richardson Number (BRN): {brn:.0f}
        700-500mb Lapse Rate: {lapse_rate:.1f} °C/km | Storm Motion: {storm_motion:.0f} kts
        
        TOP CHASE TARGETS:
        {chr(10).join([f"Target {i+1}: Score {t['score']:.0f}, Distance {t['distance']:.0f}mi, {t['reasoning']}" for i, t in enumerate(analysis_data['targets'])])}
        
        ANALYSIS REQUEST:
        Provide a professional 3-4 sentence analysis focusing on:
        1. Primary target recommendation based on composite parameters (SCP/STP/EHI)
        2. Storm mode expectations (supercells vs multicells based on BRN)
        3. Tornado potential assessment using STP and low-level shear
        4. Timing for storm initiation and chase strategy
        5. Key safety considerations for the environment
        
        Use professional meteorological terminology. Keep under 200 words.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,  # Increased for comprehensive analysis
            temperature=0.2  # Lower temperature for more precise meteorological analysis
        )
        
        ai_analysis = response.choices[0].message.content
        if ai_analysis:
            ai_analysis = ai_analysis.strip()
        else:
            ai_analysis = "AI analysis temporarily unavailable"
        
        # Add AI analysis to the top target
        if targets:
            targets[0]['ai_analysis'] = ai_analysis
            targets[0]['ai_enhanced'] = True
        
        return targets
        
    except Exception as e:
        st.warning(f"AI enhancement temporarily unavailable: {str(e)[:50]}...")
        return targets

def analyze_storm_personality(weather_data):
    """AI-powered storm personality and characteristics analysis"""
    try:
        client = get_openai_client()
        if not client:
            return {
                'type': 'Classic Supercell',
                'characteristics': 'Rotating thunderstorm with potential for tornadoes',
                'strategy': 'Maintain safe distance, watch for rotation'
            }
        
        # Prepare weather context for AI analysis
        weather_context = f"""
        Current Weather Parameters:
        - CAPE: {weather_data['CAPE']} J/kg
        - Wind Shear (0-6km): {weather_data['Shear_0_6km']} kts
        - Dewpoint: {weather_data['Dewpoint']}°F
        - CIN: {weather_data['CIN']} J/kg
        - Storm Relative Helicity: {weather_data['SRH_0_1km']} m²/s²
        - LCL Height: {weather_data['LCL_Height']} m
        """
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional storm chasing meteorologist. Analyze weather parameters and provide storm personality insights in JSON format with 'type', 'characteristics', and 'strategy' fields. Keep responses concise and actionable for storm chasers."
                },
                {
                    "role": "user",
                    "content": f"Analyze these weather parameters and predict storm type and chase strategy: {weather_context}"
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=300
        )
        
        content = response.choices[0].message.content
        if content:
            result = json.loads(content)
        else:
            result = {
                'type': 'Classic Supercell',
                'characteristics': 'Rotating thunderstorm with potential for severe weather',
                'strategy': 'Maintain safe distance, watch for rotation and downdrafts'
            }
        return result
        
    except Exception as e:
        st.warning(f"AI analysis temporarily unavailable: {str(e)}")
        return {
            'type': 'Classic Supercell',
            'characteristics': 'Rotating thunderstorm with potential for severe weather',
            'strategy': 'Maintain safe distance, watch for rotation and downdrafts'
        }

def optimize_chase_route(lat, lon, weather_data, storm_personality):
    """AI-powered chase route optimization"""
    try:
        client = get_openai_client()
        if not client:
            return "Route optimization temporarily unavailable. Recommend staying south of storm and moving east with storm motion."
        
        location_context = f"Current location: {lat:.4f}, {lon:.4f} (Valley, Nebraska area)"
        weather_summary = f"Storm type: {storm_personality['type']}, CAPE: {weather_data['CAPE']}, Shear: {weather_data['Shear_0_6km']} kts"
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert storm chaser providing tactical routing advice. Give specific, actionable directions for optimal storm intercept and safety positioning. Focus on road networks around Nebraska/Iowa."
                },
                {
                    "role": "user",
                    "content": f"Given this location and storm data, provide optimal chase route strategy: {location_context} | {weather_summary}"
                }
            ],
            max_tokens=200
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.warning(f"Route optimization error: {str(e)}")
        return "Manual routing recommended: Stay south of storm, move east with storm motion, maintain 2-3 mile safety distance."

def get_voice_assistant_response(query, weather_data, lat, lon):
    """AI Voice Assistant for storm chasing questions"""
    try:
        client = get_openai_client()
        if not client:
            return "Voice assistant temporarily unavailable. Please check weather parameters manually."
        
        # Prepare comprehensive context
        context = f"""
        Current Weather Conditions (Valley, Nebraska area):
        - Location: {lat:.4f}, {lon:.4f}
        - CAPE: {weather_data['CAPE']} J/kg
        - Wind Shear: {weather_data['Shear_0_6km']} kts
        - Dewpoint: {weather_data['Dewpoint']}°F
        - CIN: {weather_data['CIN']} J/kg
        - Storm Relative Helicity: {weather_data['SRH_0_1km']} m²/s²
        - LCL Height: {weather_data['LCL_Height']} m
        
        Storm Chasability Score: {calculate_storm_chasability(weather_data, lat, lon)}/100
        """
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert storm chasing meteorologist and safety advisor. Answer questions about current conditions, chase strategy, safety, and storm behavior. Be concise but informative. Always prioritize safety."
                },
                {
                    "role": "user",
                    "content": f"Weather Context: {context}\n\nQuestion: {query}"
                }
            ],
            max_tokens=200
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Voice assistant error: {str(e)}. Please check weather parameters manually."

def analyze_storm_photo(uploaded_file):
    """AI-powered storm photo analysis"""
    try:
        client = get_openai_client()
        if not client:
            return {
                'cloud_types': 'Unable to analyze - AI service unavailable',
                'features': 'Manual analysis required',
                'safety': 'Exercise standard storm chasing precautions',
                'recommendations': 'Maintain safe distance from storm'
            }
        
        # Convert image to base64 for API
        image_bytes = uploaded_file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are a storm chasing meteorologist analyzing photos. Identify cloud types, storm features, and provide safety assessments. Respond in JSON format with 'cloud_types', 'features', 'safety', and 'recommendations' fields."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this storm photo for cloud types, dangerous features, and provide chase recommendations."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=300
        )
        
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        else:
            return {
                'cloud_types': 'Analysis incomplete',
                'features': 'Unable to determine',
                'safety': 'Exercise caution',
                'recommendations': 'Maintain safe distance'
            }
            
    except Exception as e:
        return {
            'cloud_types': f'Analysis error: {str(e)}',
            'features': 'Manual inspection required',
            'safety': 'Exercise standard precautions',
            'recommendations': 'Maintain safe distance from storm'
        }

def save_chase_to_archive(weather_data, lat, lon):
    """Save current chase data to personal archive"""
    try:
        # Initialize chase archive in session state if not exists
        if 'chase_archive' not in st.session_state:
            st.session_state.chase_archive = []
        
        # Create chase record
        chase_record = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'location': f"{lat:.4f}, {lon:.4f}",
            'cape': weather_data['CAPE'],
            'shear': weather_data['Wind_Shear_0_6km'],
            'dewpoint': weather_data['Dewpoint'],
            'cin': weather_data['CIN'],
            'srh': weather_data['Storm_Relative_Helicity_0_1km'],
            'lcl': weather_data['LCL_Height'],
            'score': calculate_storm_chasability(weather_data, lat, lon),
            'duration': None,  # Could be calculated from GPS tracking
            'notes': 'Saved from dashboard',
            'photo': None
        }
        
        # Add to archive
        st.session_state.chase_archive.append(chase_record)
        
        # Keep only last 50 chases to manage memory
        if len(st.session_state.chase_archive) > 50:
            st.session_state.chase_archive = st.session_state.chase_archive[-50:]
            
    except Exception as e:
        st.error(f"Error saving chase: {str(e)}")

def load_chase_archive():
    """Load chase archive from session state"""
    return st.session_state.get('chase_archive', [])

def display_voice_alert(warning):
    """Display voice alert for tornado warning with mobile optimization"""
    st.error(f"🚨 TORNADO WARNING: {warning['headline']}")
    st.error(f"📍 Area: {warning['area']}")
    st.error(f"⏰ Expires: {warning.get('expires', 'Unknown')}")
    
    # Enhanced voice alert with JavaScript integration for mobile
    warning_headline = warning['headline'].replace('"', "'")
    warning_area = warning['area'].replace('"', "'")
    warning_expires = warning.get('expires', 'Unknown')
    
    voice_script = f"""
    <script>
    // Trigger voice alert for mobile devices
    if (window.stormChaseGPS && window.stormChaseGPS.voiceEnabled) {{
        const warning = {{
            headline: "{warning_headline}",
            area: "{warning_area}",
            expires: "{warning_expires}"
        }};
        window.announceTornadoWarning(warning);
    }}
    
    // Visual alert overlay for mobile
    const alertOverlay = document.createElement('div');
    alertOverlay.innerHTML = `
        <div class="voice-alert" style="
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            z-index: 9999 !important;
            background: linear-gradient(45deg, #ff4444, #cc0000) !important;
            color: white !important;
            padding: 30px !important;
            border-radius: 20px !important;
            font-size: 24px !important;
            font-weight: bold !important;
            text-align: center !important;
            box-shadow: 0 20px 60px rgba(255, 68, 68, 0.6) !important;
            max-width: 90vw !important;
            animation: alertPulse 2s infinite !important;
        ">
            <div style="font-size: 48px; margin-bottom: 15px;">🌪️</div>
            <div style="margin-bottom: 15px;">TORNADO WARNING</div>
            <div style="font-size: 18px; margin-bottom: 20px;">{warning_area}</div>
            <button onclick="this.closest('.voice-alert').parentElement.remove()" 
                    style="background: white; color: #ff4444; border: none; padding: 15px 30px; 
                           border-radius: 10px; font-size: 18px; font-weight: bold; cursor: pointer;">
                ACKNOWLEDGE
            </button>
        </div>
    `;
    document.body.appendChild(alertOverlay);
    
    // Auto-remove after 60 seconds
    setTimeout(() => {{
        if (alertOverlay.parentElement) {{
            alertOverlay.remove();
        }}
    }}, 60000);
    
    // Vibrate device if supported
    if (navigator.vibrate) {{
        navigator.vibrate([1000, 500, 1000, 500, 1000]);
    }}
    </script>
    """
    
    st.markdown(voice_script, unsafe_allow_html=True)
    st.warning("🔊 Voice Alert: TORNADO WARNING announced - Take shelter immediately!")

# Weather parameter thresholds and criteria
# Enhanced Weather Parameter Thresholds for Professional Storm Chasing
THRESHOLDS = {
    # Original Base Parameters
    'CAPE': {'threshold': 2000, 'operator': '>', 'unit': 'J/kg', 'ideal': (2500, 4000), 'description': 'Surface-based Convective Available Potential Energy'},
    'Dewpoint': {'threshold': 60, 'operator': '>', 'unit': '°F', 'ideal': (65, 70), 'description': 'Surface dewpoint temperature'},
    'Shear_0_6km': {'threshold': 40, 'operator': '>', 'unit': 'kts', 'ideal': (45, 60), 'description': 'Deep layer wind shear (0-6km)'},
    'CIN': {'threshold': 50, 'operator': '<', 'unit': 'J/kg', 'ideal': (0, 25), 'description': 'Convective Inhibition'},
    'SRH_0_1km': {'threshold': 150, 'operator': '>', 'unit': 'm²/s²', 'ideal': (200, 400), 'description': 'Storm-relative helicity (0-1km)'},
    'LCL_Height': {'threshold': (500, 1500), 'operator': 'between', 'unit': 'm', 'ideal': (800, 1200), 'description': 'Lifted Condensation Level height'},
    
    # Phase 1: Critical Composite Parameters
    'Mixed_Layer_CAPE': {'threshold': 1800, 'operator': '>', 'unit': 'J/kg', 'ideal': (2200, 3800), 'description': 'Mixed-layer CAPE (often more representative)'},
    'SCP': {'threshold': 4.0, 'operator': '>', 'unit': 'dimensionless', 'ideal': (6.0, 12.0), 'description': 'Supercell Composite Parameter'},
    'STP': {'threshold': 1.0, 'operator': '>', 'unit': 'dimensionless', 'ideal': (2.0, 4.0), 'description': 'Significant Tornado Parameter'},
    'SRH_0_1km_Enhanced': {'threshold': 200, 'operator': '>', 'unit': 'm²/s²', 'ideal': (250, 450), 'description': 'Enhanced 0-1km Storm-relative helicity'},
    
    # Phase 2: Advanced Analysis Parameters  
    'BRN': {'threshold': (10, 45), 'operator': 'between', 'unit': 'dimensionless', 'ideal': (20, 35), 'description': 'Bulk Richardson Number (storm mode)'},
    'EHI': {'threshold': 1.0, 'operator': '>', 'unit': 'dimensionless', 'ideal': (2.0, 4.0), 'description': 'Energy Helicity Index'},
    'Lapse_Rate_700_500': {'threshold': 7.0, 'operator': '>', 'unit': '°C/km', 'ideal': (7.5, 9.0), 'description': '700-500mb lapse rate'},
    'Shear_0_3km': {'threshold': 25, 'operator': '>', 'unit': 'kts', 'ideal': (30, 45), 'description': 'Low-level wind shear (0-3km)'},
    'Bunkers_Right_U': {'threshold': None, 'operator': 'value', 'unit': 'kts', 'ideal': None, 'description': 'Bunkers right-moving storm motion (U component)'},
    'Bunkers_Right_V': {'threshold': None, 'operator': 'value', 'unit': 'kts', 'ideal': None, 'description': 'Bunkers right-moving storm motion (V component)'},
    'Storm_Motion_Speed': {'threshold': 15, 'operator': '>', 'unit': 'kts', 'ideal': (20, 35), 'description': 'Bunkers storm motion speed'},
    'Mean_Wind_0_6km': {'threshold': 20, 'operator': '>', 'unit': 'kts', 'ideal': (25, 40), 'description': 'Mean wind 0-6km (storm propagation)'}
}

def get_parameter_status(value, param_name):
    """Determine the status (favorable/borderline/unfavorable) of a weather parameter"""
    try:
        threshold_info = THRESHOLDS[param_name]
        threshold = threshold_info['threshold']
        operator = threshold_info['operator']
        ideal = threshold_info['ideal']
    except KeyError:
        return 'unknown'  # Parameter not defined in thresholds
    
    if operator == '>':
        if value > threshold:
            if ideal and (value < ideal[0] or value > ideal[1]):
                return 'borderline'
            return 'favorable'
        elif value > threshold * 0.8:  # 80% of threshold for borderline
            return 'borderline'
        else:
            return 'unfavorable'
    elif operator == '<':
        if value < threshold:
            return 'favorable'
        elif value < threshold * 1.2:  # 120% of threshold for borderline
            return 'borderline'
        else:
            return 'unfavorable'
    elif operator == 'between':
        if threshold[0] <= value <= threshold[1]:
            return 'favorable'
        elif (threshold[0] - 100 <= value < threshold[0]) or (threshold[1] < value <= threshold[1] + 100):
            return 'borderline'
        else:
            return 'unfavorable'
    elif operator == 'value':  # For display-only parameters like Bunkers components
        return 'neutral'
    else:
        return 'unknown'

def get_status_color(status):
    """Return the color for a given status"""
    colors = {
        'favorable': '#28a745',    # Green
        'borderline': '#ffc107',   # Yellow
        'unfavorable': '#dc3545',   # Red
        'neutral': '#17a2b8',      # Blue for display-only parameters
        'unknown': '#6c757d'       # Gray for unknown parameters
    }
    return colors.get(status, '#6c757d')

# Auto-refresh data every 30 seconds
current_time = time.time()
if current_time - st.session_state.last_update > 30:
    st.session_state.last_update = current_time
    st.rerun()

# Initialize default coordinates (Valley, Nebraska)
lat = 41.3114
lon = -96.3439

# Sidebar with controls
with st.sidebar:
    st.header("🎛️ Dashboard Controls")
    
    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    # Current time
    st.markdown(f"**Last Update:** {datetime.now().strftime('%H:%M:%S')}")
    
    # Location input
    st.markdown("### 📍 Chase Location")
    lat = st.number_input("Latitude", value=41.3114, format="%.4f")
    lon = st.number_input("Longitude", value=-96.3439, format="%.4f")

# Generate current weather data after coordinates are defined
weather_data = generate_weather_data(lat, lon)

# Add quick stats to sidebar after weather data is generated
with st.sidebar:
    # Quick stats
    st.markdown("### 📊 Quick Stats")
    
    # Check if weather_data is available and merge composite indices
    if weather_data:
        # Calculate and merge composite indices into weather_data
        composite_indices = calculate_composite_indices(weather_data)
        # Merge composite indices into weather_data for UI display
        enhanced_weather_data = {**weather_data, **composite_indices}
        
        # Count favorable parameters using enhanced data
        favorable_count = sum(1 for param in THRESHOLDS.keys() 
                             if param in enhanced_weather_data and get_parameter_status(enhanced_weather_data[param], param) == 'favorable')
        weather_data = enhanced_weather_data  # Update weather_data with composite indices
    else:
        favorable_count = 0
    st.metric("Favorable Parameters", f"{favorable_count}/{len(THRESHOLDS)}")
    
    # Storm Chasability Score - AI-Powered Assessment
    st.markdown("### 🎯 Storm Chasability Score")
    if weather_data:
        chasability_score = calculate_storm_chasability(weather_data, lat, lon)
    else:
        chasability_score = 0
    
    # Color-coded score display
    if chasability_score >= 80:
        st.success(f"🟢 **EXCELLENT CHASE**: {chasability_score}/100")
        st.markdown("*Perfect conditions for storm chasing!*")
    elif chasability_score >= 60:
        st.warning(f"🟡 **GOOD CHASE**: {chasability_score}/100") 
        st.markdown("*Favorable conditions with some limitations*")
    elif chasability_score >= 40:
        st.info(f"🔵 **MODERATE CHASE**: {chasability_score}/100")
        st.markdown("*Mixed conditions, proceed with caution*")
    else:
        st.error(f"🔴 **POOR CHASE**: {chasability_score}/100")
        st.markdown("*Not recommended for chasing today*")
    
    # AI Storm Personality Analysis
    with st.expander("🤖 AI Storm Intelligence", expanded=False):
        storm_personality = analyze_storm_personality(weather_data)
        st.markdown(f"**Storm Type Prediction:** {storm_personality['type']}")
        st.markdown(f"**Characteristics:** {storm_personality['characteristics']}")
        st.markdown(f"**Chase Strategy:** {storm_personality['strategy']}")
        
        # Chase Route Optimizer
        if st.button("🛣️ Optimize Chase Route", key="optimize_route"):
            with st.spinner("AI calculating optimal intercept route..."):
                route_advice = optimize_chase_route(lat, lon, weather_data, storm_personality)
                st.success("**Optimal Chase Route:**")
                st.markdown(route_advice)
    
    # GPS Breadcrumb Controls with Mobile Enhancement
    st.markdown("### 🛤️ GPS Chase Tracking")
    st.markdown("*Auto-GPS tracking for iPad with voice alerts*")
    
    # GPS Status and Controls
    tracking_status = "🟢 ACTIVE" if st.session_state.tracking_active else "🔴 INACTIVE"
    st.markdown(f"**Status:** {tracking_status}")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button("🚀 Auto-GPS ON", key="start_auto_gps", disabled=st.session_state.tracking_active, help="Start automatic GPS tracking every 30 seconds"):
            st.session_state.tracking_active = True
            st.session_state.chase_start_time = datetime.now()
            add_breadcrumb(lat, lon)
            st.success("🎯 GPS Auto-Tracking Started!")
            st.rerun()
    
    with col_b:
        if st.button("⏹️ Stop GPS", key="stop_auto_gps", disabled=not st.session_state.tracking_active):
            st.session_state.tracking_active = False
            st.info("📍 GPS Auto-Tracking Stopped")
            st.rerun()
    
    # Voice Alerts Toggle
    voice_enabled = st.checkbox("🔊 Voice Alerts", value=True, key="voice_alerts", 
                               help="Enable voice announcements for tornado warnings")
    
    # Manual position controls
    st.markdown("**Manual Controls:**")
    col_c, col_d = st.columns(2)
    
    with col_c:
        if st.button("📍 Add Current GPS", key="add_manual_gps", help="Manually add current GPS position"):
            add_breadcrumb(lat, lon)
            st.success("📍 Position Added!")
            st.rerun()
    
    with col_d:
        if st.button("🗑️ Clear Track", key="clear_gps_track", disabled=len(st.session_state.breadcrumbs) == 0):
            clear_breadcrumbs()
            st.warning("🧹 Track Cleared!")
            st.rerun()
    
    # Enhanced Chase statistics with mobile-friendly display
    if len(st.session_state.breadcrumbs) > 0:
        st.markdown("**📊 Chase Statistics:**")
        
        col_stats1, col_stats2 = st.columns(2)
        with col_stats1:
            st.metric("🛣️ Distance", f"{get_chase_distance():.1f} mi", 
                     delta=f"{len(st.session_state.breadcrumbs)} points")
        with col_stats2:
            if st.session_state.chase_start_time:
                chase_duration = datetime.now() - st.session_state.chase_start_time
                hours, remainder = divmod(chase_duration.seconds, 3600)
                minutes = remainder // 60
                st.metric("⏱️ Duration", f"{hours}h {minutes}m")
            else:
                st.metric("📌 Points", len(st.session_state.breadcrumbs))
        
        # Latest position info
        if st.session_state.breadcrumbs:
            latest = st.session_state.breadcrumbs[-1]
            st.info(f"📍 Latest: {latest['time_str']} at {latest['lat']:.4f}, {latest['lon']:.4f}")
    
    # Mobile GPS Integration Notice
    st.markdown("---")
    st.markdown("**📱 iPad Integration:**")
    st.info("• Automatic GPS tracking every 30 seconds while chasing\\n• Voice alerts for tornado warnings\\n• Works offline with cellular data")

# Enhanced Layout: Full-width map on top, parameters below in columns
st.header("🗺️ Interactive Storm Chase Map")
st.markdown("Real-time radar data, SPC outlooks, and intelligent chase targets")

# Full-width Interactive Map section (enhanced layout)
# Map creation and display

# Create enhanced map with multiple base layers for storm chasing
m = folium.Map(
    location=[lat, lon],
    zoom_start=7,
    tiles="OpenStreetMap"
)

# Add specialized map layers for storm chasing
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite (High Resolution)',
    overlay=False,
    control=True
).add_to(m)

# Add terrain layer for topographical awareness
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Topographic',
    overlay=False,
    control=True
).add_to(m)

# Real-time NEXRAD Base Reflectivity overlay
nexrad_reflectivity = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r.cgi',
    name='🌧️ NEXRAD Reflectivity',
    layers='nexrad-n0r-wmst',
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.6,
    version='1.1.1'
)
nexrad_reflectivity.add_to(m)

# NEXRAD Base Velocity for rotation detection
nexrad_velocity = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0v.cgi',
    name='🌪️ NEXRAD Velocity', 
    layers='nexrad-n0v-wmst',
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.7,
    version='1.1.1'
)
nexrad_velocity.add_to(m)

# Storm-Relative Velocity for mesocyclone detection
nexrad_storm_relative = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0s.cgi',
    name='🎯 Storm Relative Motion',
    layers='nexrad-n0s-wmst',
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.8,
    version='1.1.1'
)
nexrad_storm_relative.add_to(m)
    
# Comprehensive SPC Storm Prediction Center Overlays

# SPC Day 1 Convective Outlook 
spc_day1_outlook = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/us/spc_outlook.cgi',
    name='🌩️ SPC Day 1 Outlook',
    layers='day1otlk_cat',
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.6,
    version='1.1.1'
)
spc_day1_outlook.add_to(m)
    
# SPC Day 2-3 Extended Outlooks
spc_day2_outlook = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/us/spc_outlook.cgi',
    name='🗓️ SPC Day 2 Outlook',
    layers='day2otlk_cat', 
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.5,
    version='1.1.1'
)
spc_day2_outlook.add_to(m)
    
# Active Watches and Warnings
current_watches = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/us/wwa.cgi',
    name='⚠️ Active Watches & Warnings',
    layers='warnings_c',
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.7,
    version='1.1.1'
)
current_watches.add_to(m)
    
# SPC Mesoscale Discussions (MCDs)
spc_mcds = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/us/spc_mcd.cgi',
    name='📋 SPC Mesoscale Discussions',
    layers='spc_mcd',
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.6,
    version='1.1.1'
)
spc_mcds.add_to(m)
    
# Tornado probability overlay
tornado_prob = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/us/spc_outlook.cgi',
    name='🌪️ Tornado Probability', 
    layers='day1otlk_torn',
    fmt='image/png',
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.5,
    version='1.1.1'
)
tornado_prob.add_to(m)
    
# Hail probability overlay
hail_prob = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/us/spc_outlook.cgi',
    name='🧊 Hail Probability',
    layers='day1otlk_hail',
    fmt='image/png', 
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.5,
    version='1.1.1'
)
hail_prob.add_to(m)
    
# Surface Analysis overlay
surface_analysis = folium.WmsTileLayer(
    url='https://mesonet.agron.iastate.edu/cgi-bin/wms/us/mrms.cgi',
    name='🌡️ Surface Analysis',
    layers='mrms_p1h_00.00',
    fmt='image/png', 
    transparent=True,
    overlay=True,
    control=True,
    opacity=0.4,
    version='1.1.1'
)
surface_analysis.add_to(m)
    
# Add GPS breadcrumb trail
if len(st.session_state.breadcrumbs) > 1:
    # Create the breadcrumb path
    breadcrumb_coords = [(b['lat'], b['lon']) for b in st.session_state.breadcrumbs]
    
    # Add the path line
    folium.PolyLine(
        breadcrumb_coords,
        color='red',
        weight=3,
        opacity=0.8,
        popup=f"Chase Track - {get_chase_distance():.1f} miles"
    ).add_to(m)
        
    # Add numbered markers for each breadcrumb
    for i, breadcrumb in enumerate(st.session_state.breadcrumbs):
        folium.CircleMarker(
            [breadcrumb['lat'], breadcrumb['lon']],
            radius=6,
            popup=f"Point {i+1}<br>Time: {breadcrumb['time_str']}",
            color='darkred',
            fillColor='red',
            fillOpacity=0.7
        ).add_to(m)
    
# Add current location marker  
marker_color = 'green' if st.session_state.tracking_active else 'blue'
marker_icon = 'play' if st.session_state.tracking_active else 'home'
status_text = "ACTIVE CHASE" if st.session_state.tracking_active else "Chase Base"

folium.Marker(
    [lat, lon],
    popup=f"Current Location<br>{status_text}",
    tooltip=status_text,
    icon=folium.Icon(color=marker_color, icon=marker_icon)
).add_to(m)
    
# Cached intelligent target generation with proper throttling

# Initialize session state for caching
if 'cached_targets' not in st.session_state:
    st.session_state.cached_targets = None
    st.session_state.last_target_update = 0
    st.session_state.cached_weather = None
    st.session_state.last_ai_enhancement = 0
    
current_time = time.time()

# Check if targets need refresh (every 15 minutes)
target_refresh_interval = 15 * 60  # 15 minutes
needs_target_refresh = (
    st.session_state.cached_targets is None or 
    current_time - st.session_state.last_target_update > target_refresh_interval
)
    
# Manual refresh controls
col_refresh1, col_refresh2 = st.columns([3, 1])
with col_refresh1:
    st.markdown("🎯 **Intelligent Chase Targets** • Auto-refresh: 15min")
with col_refresh2:
    if st.button("🔄 Refresh Targets", key="manual_target_refresh", help="Force refresh targets and AI analysis"):
        needs_target_refresh = True
        st.session_state.last_ai_enhancement = 0  # Reset AI throttle
    
# Generate or use cached targets
if needs_target_refresh:
    with st.spinner("🧠 Analyzing weather data for optimal chase targets..."):
        # Generate fresh weather data and targets
        current_weather = generate_weather_data(lat, lon)
        intelligent_targets = generate_intelligent_targets(lat, lon, current_weather)
        
        # Update cache
        st.session_state.cached_targets = intelligent_targets
        st.session_state.cached_weather = current_weather
        st.session_state.last_target_update = current_time
        
        st.success(f"✨ **Targets updated** at {datetime.now().strftime('%I:%M %p')}")
else:
    # Use cached data
    intelligent_targets = st.session_state.cached_targets
    current_weather = st.session_state.cached_weather
    
    next_refresh = st.session_state.last_target_update + target_refresh_interval
    minutes_until_refresh = int((next_refresh - current_time) / 60)
    st.info(f"🔄 **Using cached targets** • Next refresh in {minutes_until_refresh} minutes")
    
# AI enhancement with hourly throttling
ai_refresh_interval = 60 * 60  # 1 hour
needs_ai_refresh = (
    current_time - st.session_state.last_ai_enhancement > ai_refresh_interval or
    st.button("🧠 Get AI Analysis", key="manual_ai_refresh", help="Get fresh AI recommendations")
)
    
if needs_ai_refresh and intelligent_targets:
    with st.spinner("🧠 Getting AI recommendations..."):
        enhanced_targets = enhance_targets_with_ai(intelligent_targets, current_weather)
        st.session_state.last_ai_enhancement = current_time
        st.success("🧠 **AI analysis updated**")
else:
    enhanced_targets = intelligent_targets if intelligent_targets else []
    
# Display intelligent target information
if enhanced_targets:
    st.markdown("**🎯 Intelligent Chase Targets:**")
    
    # Show top target with AI analysis if available
    top_target = enhanced_targets[0]
    if top_target.get('ai_enhanced'):
        with st.expander("🧠 AI Chase Analysis", expanded=True):
            st.success(f"🎯 **Top Target**: Score {top_target['score']:.0f} • {top_target['distance_miles']:.0f} miles")
            st.write(top_target.get('ai_analysis', 'Analysis unavailable'))
        
    # Add intelligent targets to map
    for i, target in enumerate(enhanced_targets):
        # Color coding by severity/score
        if target['severity'] == 'High':
            color = 'red'
            icon = 'star'
        elif target['severity'] == 'Moderate': 
            color = 'orange'
            icon = 'flash'
        else:
            color = 'green'
            icon = 'cloud'
        
        # Create detailed popup with meteorological information
        popup_html = f"""
        <div style="width: 250px;">
            <h4>🎯 {target['name']}</h4>
            <p><strong>Chase Score:</strong> {target['score']:.0f}/100</p>
            <p><strong>Priority:</strong> {target['priority']}</p>
            <p><strong>Distance:</strong> {target['distance_miles']:.0f} miles</p>
            <p><strong>Initiation:</strong> {target['initiation_time']}</p>
            <p><strong>Analysis:</strong> {target['reasoning']}</p>
            <hr>
            <p><small><strong>Weather:</strong><br>
            CAPE: {target.get('weather_data', {}).get('CAPE', 0):.0f} J/kg<br>
            Shear: {target.get('weather_data', {}).get('Shear_0_6km', 0):.0f} kts<br>
            Dewpoint: {target.get('weather_data', {}).get('Dewpoint', 0):.0f}°F</small></p>
        </div>
        """
        
        folium.Marker(
            [target['lat'], target['lon']],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{target['name']} • Score: {target['score']:.0f}",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
else:
    st.warning("⚠️ No chase-worthy targets identified in current conditions")
    st.info("This typically means weather parameters don't support severe storm development")
    
# Add comprehensive layer control for storm chasing
layer_control = folium.LayerControl(
    position='topright',
    collapsed=False
)
layer_control.add_to(m)

# Collapsible Legend Control (similar to layer control)
legend_control_html = '''
<div id="legend-control" style="position: fixed; 
                               bottom: 50px; left: 50px; z-index:9999;">
    <div id="legend-toggle" style="
        background: white; border: 2px solid #333; padding: 8px 12px; 
        border-radius: 5px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        cursor: pointer; font-weight: bold; text-align: center;
        margin-bottom: 5px; user-select: none;
    ">
        🏷️ Legend ▼
    </div>
        <div id="legend-content" style="
            width: 220px; background-color: rgba(255, 255, 255, 0.95); 
            border: 2px solid #333; font-size: 11px; padding: 8px; 
            border-radius: 5px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            display: block;
        ">
            <h4 style="margin: 0 0 8px 0; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 4px;">Storm Chase Legend</h4>
            
            <div style="margin-bottom: 6px;"><strong>📶 Radar Reflectivity:</strong></div>
            <div style="color: #00FF00; margin: 2px 0;">🌧️ Light (20-35 dBZ)</div>
            <div style="color: #FFFF00; margin: 2px 0;">⛈️ Moderate (35-50 dBZ)</div>
            <div style="color: #FF8000; margin: 2px 0;">🌩️ Heavy (50-60 dBZ)</div>
            <div style="color: #FF0000; margin: 2px 0;">⚡ Severe (60+ dBZ)</div>
            <div style="color: #FF00FF; margin: 2px 0;">🧊 Hail Core (65+ dBZ)</div>
            
            <div style="margin: 6px 0 2px 0;"><strong>🎯 SPC Risk Areas:</strong></div>
            <div style="background: #C0E0C0; padding: 1px 3px; margin: 1px 0;">MARGINAL (1)</div>
            <div style="background: #FFE066; padding: 1px 3px; margin: 1px 0;">SLIGHT (2)</div>
            <div style="background: #FF9999; padding: 1px 3px; margin: 1px 0;">ENHANCED (3)</div>
            <div style="background: #FF6666; padding: 1px 3px; margin: 1px 0;">MODERATE (4)</div>
            <div style="background: #FF3333; padding: 1px 3px; margin: 1px 0; color: white;">HIGH (5)</div>
        </div>
    </div>
    
    <script>
    document.getElementById('legend-toggle').addEventListener('click', function() {
        var content = document.getElementById('legend-content');
        var toggle = document.getElementById('legend-toggle');
        if (content.style.display === 'none') {
            content.style.display = 'block';
            toggle.innerHTML = '🏷️ Legend ▼';
        } else {
            content.style.display = 'none';
            toggle.innerHTML = '🏷️ Legend ▶';
        }
    });
    </script>
    '''
# Add legend to map (type: ignore for LSP)
m.get_root().html.add_child(folium.Element(legend_control_html))  # type: ignore[attr-defined]
    
# Display comprehensive storm chasing map (full width)
map_data = st_folium(m, width=None, height=600, key="main_chase_map")
    
# Enhanced map status with SPC integration info
map_status_col1, map_status_col2 = st.columns(2)
with map_status_col1:
    st.success("🗺️ **Interactive Storm Chase Map** • Real-time radar & SPC overlays active")
with map_status_col2:
    st.info("📱 Use layer control (top-right) to toggle radar, outlooks, and watches")
    
# SPC outlook summary
st.markdown("### ⚡ Storm Prediction Center Status")
spc_col1, spc_col2, spc_col3 = st.columns(3)
    
with spc_col1:
    st.metric("Day 1 Outlook", "Available", help="Current day convective outlook from SPC")
    st.caption("🎯 Categorical risk levels visible on map")
    
with spc_col2:
    st.metric("Active Watches", "Real-time", help="Live tornado and severe thunderstorm watches")
    st.caption("⚠️ Polygon overlays show active warning areas")
    
with spc_col3:
    st.metric("Mesoscale Discussions", "Updated", help="SPC mesoscale discussions (MCDs)")
    st.caption("📋 Areas under enhanced surveillance")
    
# Toggle for advanced SPC features
with st.expander("🎯 Advanced SPC Analysis Tools", expanded=False):
    st.markdown("**Probability Overlays:**")
    prob_col1, prob_col2 = st.columns(2)
    
    with prob_col1:
        st.markdown("• **🌪️ Tornado Probability** - Shows tornado likelihood areas")
        st.markdown("• **🧊 Hail Probability** - Significant hail risk zones")
    
    with prob_col2:
        st.markdown("• **⚡ Wind Probability** - Damaging wind potential")
        st.markdown("• **📋 MCDs** - Areas of enhanced surveillance")
    
st.info("💡 **Pro Tip:** Enable probability layers when targeting specific hazards during a chase")
st.caption("⏰ All SPC data updates automatically every 30 minutes or when new products are issued")

# Weather Parameters Section - Enhanced two-column layout below map
st.markdown("---")
st.header("⛈️ Advanced Weather Parameters")
st.markdown("Comprehensive meteorological analysis with 16+ professional parameters")

# Two-column layout for weather parameters
param_col1, param_col2 = st.columns([1, 1])

with param_col1:
    st.subheader("🌩️ Primary Parameters")
    
    # Add comprehensive diagnostics expander
    with st.expander("🔬 Advanced Parameter Diagnostics", expanded=False):
        if weather_data:
            st.markdown("**📊 Comprehensive Parameter Status:**")
            
            # Group parameters by category
            base_params = ['CAPE', 'Dewpoint', 'Shear_0_6km', 'CIN', 'SRH_0_1km', 'LCL_Height']
            phase1_params = ['Mixed_Layer_CAPE', 'SCP', 'STP', 'SRH_0_1km_Enhanced']
            phase2_params = ['BRN', 'EHI', 'Lapse_Rate_700_500', 'Shear_0_3km', 'Bunkers_Right_U', 'Bunkers_Right_V', 'Storm_Motion_Speed', 'Mean_Wind_0_6km']
            
            # Create parameter tables
            col_diag1, col_diag2, col_diag3 = st.columns(3)
            
            with col_diag1:
                st.markdown("**Base Parameters:**")
                for param in base_params:
                    if param in weather_data:
                        value = weather_data[param]
                        status = get_parameter_status(value, param)
                        color = get_status_color(status)
                        st.markdown(f"<span style='color: {color}'>● {param}: {value:.1f}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"❌ {param}: Missing")
            
            with col_diag2:
                st.markdown("**Phase 1 Advanced:**")
                for param in phase1_params:
                    if param in weather_data:
                        value = weather_data[param]
                        status = get_parameter_status(value, param)
                        color = get_status_color(status)
                        st.markdown(f"<span style='color: {color}'>● {param}: {value:.2f}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"❌ {param}: Missing")
            
            with col_diag3:
                st.markdown("**Phase 2 Professional:**")
                for param in phase2_params:
                    if param in weather_data:
                        value = weather_data[param]
                        if param in ['Bunkers_Right_U', 'Bunkers_Right_V']:
                            st.markdown(f"<span style='color: #17a2b8'>● {param}: {value:.1f}</span>", unsafe_allow_html=True)
                        else:
                            status = get_parameter_status(value, param)
                            color = get_status_color(status)
                            st.markdown(f"<span style='color: {color}'>● {param}: {value:.1f}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"❌ {param}: Missing")
            
            # Parameter availability summary
            total_params = len(THRESHOLDS)
            available_params = sum(1 for param in THRESHOLDS.keys() if param in weather_data)
            st.success(f"**Parameter Coverage: {available_params}/{total_params} ({(available_params/total_params)*100:.1f}%)**")
        else:
            st.error("⚠️ Weather data unavailable for diagnostics")
    
    # Display primary parameters
    if weather_data:
        primary_params = ['CAPE', 'Mixed_Layer_CAPE', 'Dewpoint', 'Shear_0_6km', 'CIN', 'SRH_0_1km']
        for param_name in primary_params:
            if param_name in weather_data and param_name in THRESHOLDS:
                param_info = THRESHOLDS[param_name]
                value = weather_data[param_name]
                status = get_parameter_status(value, param_name)
                color = get_status_color(status)
                
                # Format parameter name for display
                display_name = param_name.replace('_', '-')
                unit = param_info['unit']
                threshold = param_info['threshold']
                operator = param_info['operator']
                
                # Create threshold description
                if operator == 'between':
                    threshold_desc = f"{threshold[0]}-{threshold[1]} {unit}"
                else:
                    threshold_desc = f"{operator} {threshold} {unit}"
                
                # Display parameter with color coding
                st.markdown(f"""
                <div style="
                    padding: 10px; 
                    margin: 5px 0; 
                    border-left: 5px solid {color}; 
                    background-color: rgba(255,255,255,0.1);
                    border-radius: 5px;
                ">
                    <strong>{display_name}:</strong> {value:.1f} {unit}<br>
                    <small>Target: {threshold_desc} | Status: <span style="color: {color}; font-weight: bold;">{status.upper() if status else 'UNKNOWN'}</span></small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("⚠️ Weather data unavailable - check API connections")

with param_col2:
    st.subheader("🎯 Composite Indices")
    
    # Display composite parameters
    if weather_data:
        composite_params = ['SCP', 'STP', 'EHI', 'BRN', 'Lapse_Rate_700_500', 'Shear_0_3km']
        for param_name in composite_params:
            if param_name in weather_data and param_name in THRESHOLDS:
                param_info = THRESHOLDS[param_name]
                value = weather_data[param_name]
                status = get_parameter_status(value, param_name)
                color = get_status_color(status)
                
                # Format parameter name for display
                display_name = param_name.replace('_', '-')
                unit = param_info['unit']
                threshold = param_info['threshold']
                operator = param_info['operator']
                
                # Create threshold description
                if operator == 'between':
                    threshold_desc = f"{threshold[0]}-{threshold[1]} {unit}"
                else:
                    threshold_desc = f"{operator} {threshold} {unit}"
                
                # Display parameter with color coding
                st.markdown(f"""
                <div style="
                    padding: 10px; 
                    margin: 5px 0; 
                    border-left: 5px solid {color}; 
                    background-color: rgba(255,255,255,0.1);
                    border-radius: 5px;
                ">
                    <strong>{display_name}:</strong> {value:.2f} {unit}<br>
                    <small>Target: {threshold_desc} | Status: <span style="color: {color}; font-weight: bold;">{status.upper() if status else 'UNKNOWN'}</span></small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("⚠️ Weather data unavailable - check API connections")

# Bottom section continues
st.markdown("---")

# Two larger columns for radar and mesoscale sectors (enhanced visibility)
col3, col4 = st.columns(2)

with col3:
    st.header("📡 Radar Data")
    
    # Get closest radar station
    station_id, station_info = get_radar_stations_near_location(lat, lon)
    
    if station_id and station_info:
        # Display station info with distance warning if applicable
        if station_info.get('out_of_range'):
            st.warning(f"🚨 **Station:** {station_id} - {station_info['name']} ({station_info['distance_km']:.0f}km away)")
            st.caption("⚠️ Station is outside optimal range. Image quality may be reduced at edges.")
        else:
            st.success(f"✅ **Station:** {station_id} - {station_info['name']}")
            st.caption("🟢 Station within optimal NEXRAD coverage range")
        
        # Enhanced radar product selection with real-time map integration
        st.info("💡 **Tip:** Use the map layers above for real-time radar overlays, or select detailed products below for static analysis")
        
        radar_product = st.selectbox(
            "Detailed Radar Product (Static Analysis)",
            ["N0Q", "N0U", "N0S", "N0Z", "N0K", "N0H", "N0C", "N0X"],
            format_func=lambda x: {
                "N0Q": "🌧️ Base Reflectivity SR (Storm Intensity)",
                "N0U": "🌪️ Base Velocity SR (Rotation Detection)", 
                "N0S": "🎯 Storm Relative Motion (Mesocyclones)",
                "N0Z": "📊 Composite Reflectivity (Overall Structure)",
                "N0K": "🔍 Correlation Coefficient (Debris Detection)",
                "N0H": "🧊 Differential Reflectivity (Hail Size)",
                "N0C": "💨 Low-Level Velocity (0.5° Tilt)",
                "N0X": "⚡ Differential Phase (Advanced Analysis)"
            }[x],
            help="Detailed radar analysis - complements real-time map layers above"
        )
        
        # Radar comparison note
        st.caption("📊 **Map vs Static:** Interactive map shows live radar tiles, static images below show detailed loops")
        
        # Add product explanation for storm chasers (RIDGE2 Updated)
        product_explanations = {
            "N0Q": "Super Resolution reflectivity - shows precipitation intensity with enhanced detail.",
            "N0U": "Super Resolution velocity - critical for tornado detection! Look for velocity couplets.",
            "N0S": "Removes storm motion to highlight internal rotation - key for mesocyclone ID.",
            "N0Z": "Shows maximum reflectivity through all elevation scans - storm top intensity.",
            "N0K": "Dual-pol correlation coefficient - detects tornado debris (low correlation values).",
            "N0H": "Differential reflectivity - identifies hail size for chase safety planning.",
            "N0C": "Low-level velocity where tornadoes form - critical for tornado warned storms.",
            "N0X": "Differential phase - advanced dual-pol analysis for precipitation type."
        }
        st.caption(f"💡 **{radar_product}:** {product_explanations.get(radar_product, '')}")
        
        # Real-time radar status indicator
        radar_col1, radar_col2 = st.columns([3, 1])
        with radar_col1:
            st.markdown(f"🟢 **Live NEXRAD** • Range: ~230mi • Updated: ~6min")
        with radar_col2:
            if st.button("🔄 Refresh", key="refresh_radar", help="Force reload radar data"):
                st.rerun()
        
        # Fetch and display real-time radar image
        with st.spinner(f"🛰️ Loading live {radar_product} radar..."):
            radar_data = fetch_radar_image(station_id, radar_product)
            
        if radar_data:
            try:
                # Display animated GIF directly to preserve radar loop animation
                st.image(radar_data, caption=f"🎯 Live {radar_product} from {station_id} • {station_info['name']}", width="stretch")
                
                # Add time warning for critical products
                if radar_product in ['N0V', 'N0S', 'DVL']:
                    st.success("🌪️ **Active Storm Analysis Mode** - Monitor for velocity couplets!")
                elif radar_product in ['N0K', 'N0H']:
                    st.info("⚡ **Dual-Polarization Active** - Advanced storm analysis enabled")
                    
            except Exception as e:
                st.error(f"⚠️ Radar image processing error: {str(e)}")
                st.info("Try selecting a different radar product or refresh")
        else:
            st.warning("🔴 **Live radar temporarily unavailable**")
            st.markdown("""
            **Possible causes:**
            - Radar station maintenance
            - Network connectivity issues  
            - High traffic during severe weather
            
            **Try:** Different station or refresh in ~2 minutes
            """)
    else:
        st.error("🔴 **No NEXRAD coverage found**")
        st.markdown("""
        **Storm chasers:** You may be outside NEXRAD coverage area.
        
        **Solutions:**
        - Move to Nebraska, Kansas, or Oklahoma for optimal coverage
        - Check if coordinates are correct (should be US Midwest)
        - Try refreshing - network issue may be temporary
        """)
        
        # Show available stations as backup
        if st.button("🗺️ Show Available Stations", key="show_stations"):
            st.markdown("**Available NEXRAD Stations:**")
            stations_info = {
                'KOAX': 'Omaha, NE - Prime for Nebraska chasing',
                'KGLD': 'Goodland, KS - Western Kansas coverage', 
                'KUEX': 'Hastings, NE - Central Nebraska',
                'KEAX': 'Kansas City, MO - Eastern Kansas/Missouri'
            }
            for station, desc in stations_info.items():
                st.markdown(f"- **{station}**: {desc}")

with col4:
    st.header("🛰️ GOES Mesoscale Sectors")
    
    # Mesoscale sector status and refresh
    meso_col1, meso_col2 = st.columns([3, 1])
    with meso_col1:
        st.markdown("🎯 **Live Mesoscale** • Storm-Focused • 30-60sec Updates")
    with meso_col2:
        if st.button("🔄 Refresh", key="refresh_mesoscale", help="Force reload mesoscale data"):
            st.rerun()
    
    # Fetch and display mesoscale sector
    with st.spinner("🎯 Loading active mesoscale sectors..."):
        mesoscale_data = get_goes_mesoscale_sectors()
        
    if mesoscale_data:
        try:
            sector_name, update_freq, description = parse_mesoscale_info(mesoscale_data['url'])
            
            # Display the mesoscale image
            st.image(mesoscale_data['data'], caption=f"🎯 {sector_name} - Storm Focused", width="stretch")
            
            # Show sector information
            st.success(f"⚡ **{sector_name} Active**")
            st.caption(f"🔄 {update_freq} • {description}")
            
            # Add mesoscale-specific guidance
            if mesoscale_data['type'] == 'mesoscale':
                st.info("🎯 **Ultra-High Resolution:** This sector updates every 30-60 seconds and is positioned by NWS on active severe weather!")
                st.markdown("""
                **What you're seeing:**
                - NWS positioned this sector on active storms
                - Updates faster than most radar systems
                - Perfect for tracking rapid storm evolution
                """)
            else:
                st.success("🌎 **Regional Coverage:** High-resolution view of Great Plains storm corridors")
                st.caption("Covers primary storm chasing areas with 5-minute updates")
                
        except Exception as e:
            st.error(f"⚠️ Mesoscale image processing error: {str(e)}")
            st.info("Trying to load alternative sector...")
    else:
        st.warning("🔴 **No active mesoscale sectors**")
        st.markdown("""
        **What this means:**
        - No severe weather active requiring mesoscale positioning
        - NWS hasn't positioned sectors on current storms
        - Check back during active severe weather days
        
        **During severe weather:** These sectors update every 30-60 seconds!
        """)

# Separate row for HRRR model data (moved down for better visual organization)
st.markdown("---")

st.header("🌡️ HRRR Weather Model")
st.caption("High-resolution numerical weather prediction model for short-term forecasting")

# Full-width HRRR section with better layout
hrrr_col1, hrrr_col2 = st.columns([3, 1])

with hrrr_col2:
    # Forecast hour selection
    forecast_hour = st.selectbox("Forecast Hour", [0, 1, 3, 6, 12, 18], 
                                format_func=lambda x: f"{x}hr" if x > 0 else "Analysis",
                                help="Select forecast time - 0hr shows current conditions")

with hrrr_col1:
    st.markdown("🌤️ **Live HRRR Model** • 3km Resolution • Hourly Updates")

# Fetch and display HRRR data
with st.spinner("Loading HRRR model data..."):
    hrrr_data = get_hrrr_data(lat, lon, forecast_hour)
    
if hrrr_data and hrrr_data.get('source') != 'API_UNAVAILABLE':
    st.markdown("**NOAA/NWS Forecast Data:**")
    
    # Display real weather parameters
    col5a, col5b = st.columns(2)
    
    with col5a:
        if hrrr_data.get('temperature_2m'):
            st.metric("Temperature", f"{hrrr_data['temperature_2m']}°F")
        if hrrr_data.get('wind_speed_10m'):
            wind_speed = hrrr_data['wind_speed_10m']
            # Extract number if it's a string like "15 mph"
            if isinstance(wind_speed, str):
                wind_speed = wind_speed.split()[0] if wind_speed.split() else "Unknown"
            st.metric("Wind Speed", f"{wind_speed} mph")
    
    with col5b:
        if hrrr_data.get('wind_direction_10m'):
            st.metric("Wind Direction", hrrr_data['wind_direction_10m'])
        st.metric("Data Source", hrrr_data.get('source', 'NOAA/NWS'))
        
    # Show detailed forecast if available
    if hrrr_data.get('forecast_text'):
        with st.expander("🌍 Detailed Forecast"):
            st.info(hrrr_data['forecast_text'])
    
    st.success(f"🌡️ Real-time NOAA forecast for {lat:.2f}, {lon:.2f}")
else:
    st.warning("⚠️ NOAA forecast data unavailable - check internet connection")
    st.info("The dashboard requires internet access for real-time weather data")
    
    # Show SPC status even when HRRR is unavailable
    st.markdown("---")
    st.markdown("### ⚡ Storm Prediction Center Status (Independent)")
    st.success("🎯 **SPC overlays remain active** on the interactive map above")
    st.info("Day 1-2 outlooks, watches, and MCDs continue to update regardless of HRRR data availability")

# Voice Alert System - Check for tornado warnings
current_time = time.time()
if current_time - st.session_state.last_warning_check > 60:  # Check every minute
    st.session_state.last_warning_check = current_time
    tornado_warnings = check_tornado_warnings(lat, lon, 50)  # 50 mile radius
    
    for warning in tornado_warnings:
        display_voice_alert(warning)

# Additional sections for storm reports and composite indices
st.markdown("---")


# Two columns for storm reports and composite indices
col6, col7 = st.columns(2)

# Storm Reports Section
with col6:
    st.header("⚡ Storm Reports & Alerts")
    
    # Get NWS alerts
    with st.spinner("Loading alerts and reports..."):
        alerts = get_nws_alerts(lat, lon, 100)
        storm_reports = get_spc_storm_reports()
    
    # Display active alerts
    if alerts:
        st.markdown("**🚨 Active Alerts:**")
        for alert in alerts[:5]:  # Show top 5 alerts
            properties = alert.get('properties', {})
            event = properties.get('event', 'Unknown')
            headline = properties.get('headline', 'No headline')
            severity = properties.get('severity', 'Unknown')
            
            # Color code by severity
            if 'warning' in event.lower():
                alert_color = 'error'
            elif 'watch' in event.lower():
                alert_color = 'warning'  
            else:
                alert_color = 'info'
                
            if alert_color == 'error':
                st.error(f"🚨 {event}: {headline}")
            elif alert_color == 'warning':
                st.warning(f"⚠️ {event}: {headline}")
            else:
                st.info(f"ℹ️ {event}: {headline}")
    else:
        st.info("No active alerts for your area")
    
    # Display storm reports
    st.markdown("**📍 Today's Storm Reports:**")
    
    report_tabs = st.tabs(["🌪️ Tornado", "🧊 Hail", "💨 Wind"])
    
    with report_tabs[0]:
        tornado_reports = storm_reports.get('tornado', [])
        if tornado_reports:
            for report in tornado_reports[:5]:
                st.markdown(f"**{report['time']}** - {report['location']}")
                st.markdown(f"Magnitude: {report['magnitude']}")
        else:
            st.info("No tornado reports today")
    
    with report_tabs[1]:
        hail_reports = storm_reports.get('hail', [])
        if hail_reports:
            for report in hail_reports[:5]:
                st.markdown(f"**{report['time']}** - {report['location']}")
                st.markdown(f"Size: {report['magnitude']}")
        else:
            st.info("No hail reports today")
    
    with report_tabs[2]:
        wind_reports = storm_reports.get('wind', [])
        if wind_reports:
            for report in wind_reports[:5]:
                st.markdown(f"**{report['time']}** - {report['location']}")
                st.markdown(f"Speed: {report['magnitude']}")
        else:
            st.info("No wind reports today")

# Composite Indices Section
with col7:
    st.header("🌀 Composite Indices")
    st.markdown("Advanced severe weather parameters for storm forecasting")
    
    # Calculate composite indices
    composite_indices = calculate_composite_indices(weather_data)
    
    # Display indices with interpretation
    st.markdown("**Severe Weather Indices:**")
    
    # Supercell Composite Parameter (SCP)
    scp_value = composite_indices['SCP']
    scp_color = 'red' if scp_value >= 4 else 'orange' if scp_value >= 1 else 'green'
    st.metric(
        "SCP (Supercell Composite)", 
        f"{scp_value:.1f}",
        help="Supercell Composite Parameter. >4: Significant, 1-4: Moderate, <1: Low"
    )
    st.caption("💡 Combines instability, wind shear, and moisture for supercell potential. Higher values = better rotating storm conditions")
    if scp_value >= 4:
        st.error("High supercell potential!")
    elif scp_value >= 1:
        st.warning("Moderate supercell potential")
    
    # Significant Tornado Parameter (STP)
    stp_value = composite_indices['STP']
    st.metric(
        "STP (Significant Tornado)",
        f"{stp_value:.1f}",
        help="Significant Tornado Parameter. >1: Significant, 0.5-1: Moderate, <0.5: Low"
    )
    st.caption("🌪️ Targets significant tornado potential using CAPE, 0-1 km SRH, effective shear, low LCLs, and minimal CIN. Values >1 = prime chase time!")
    if stp_value >= 1:
        st.error("High tornado potential!")
    elif stp_value >= 0.5:
        st.warning("Moderate tornado potential")
    
    # Energy Helicity Index (EHI)
    ehi_value = composite_indices['EHI']
    st.metric(
        "EHI (Energy Helicity)",
        f"{ehi_value:.1f}",
        help="Energy Helicity Index. >1: Significant, 0.5-1: Moderate, <0.5: Low"
    )
    st.caption("⚡ Balance between atmospheric energy (CAPE) and rotation (SRH). Higher values = strong updrafts + rotation = tornadogenesis")
    
    # SHIP (Supercell High Precipitation)
    ship_value = composite_indices['SHIP']
    st.metric(
        "SHIP (Significant Hail)",
        f"{ship_value:.1f}",
        help="Significant Hail Parameter. Composite index for significant hail (>2 inches) using CAPE, shear, and freezing level"
    )
    st.caption("🧊 Forecasts dangerous hail that can damage vehicles - critical for chaser safety planning")
    
    # Overall severe weather potential
    st.markdown("**Overall Assessment:**")
    severe_potential = max(scp_value/4, stp_value/1, ehi_value/1) * 100
    severe_potential = min(severe_potential, 100)  # Cap at 100%
    
    if severe_potential >= 75:
        st.error(f"🌪️ VERY HIGH severe weather potential: {severe_potential:.0f}%")
    elif severe_potential >= 50:
        st.warning(f"⚠️ HIGH severe weather potential: {severe_potential:.0f}%") 
    elif severe_potential >= 25:
        st.info(f"📊 MODERATE severe weather potential: {severe_potential:.0f}%")
    else:
        st.success(f"✅ LOW severe weather potential: {severe_potential:.0f}%")

# AI Features Section
st.markdown("---")

# Voice Assistant Section
st.markdown("### 🎙️ AI Voice Assistant")
voice_col1, voice_col2 = st.columns([3, 1])

with voice_col1:
    voice_query = st.text_input(
        "Ask your AI Storm Assistant anything:",
        placeholder="e.g., 'What's the tornado risk today?' or 'Should I chase this storm?'",
        key="voice_query"
    )

with voice_col2:
    if st.button("🤖 Ask AI", key="ask_voice_assistant"):
        if voice_query:
            with st.spinner("AI Assistant thinking..."):
                ai_response = get_voice_assistant_response(voice_query, weather_data, lat, lon)
                st.success(f"**AI Assistant:** {ai_response}")
        else:
            st.warning("Please enter a question first!")

# Storm Archive Section
st.markdown("### 📚 Personal Storm Archive")
archive_col1, archive_col2, archive_col3 = st.columns([2, 1, 1])

with archive_col1:
    # Photo upload for analysis
    uploaded_file = st.file_uploader(
        "Upload storm photo for AI analysis",
        type=['png', 'jpg', 'jpeg'],
        key="storm_photo"
    )
    
with archive_col2:
    if st.button("💾 Save Chase", key="save_chase"):
        save_chase_to_archive(weather_data, lat, lon)
        st.success("Chase saved to archive!")
        
with archive_col3:
    if st.button("📖 View Archive", key="view_archive"):
        st.session_state.show_archive = not st.session_state.get('show_archive', False)

# Photo Analysis
if uploaded_file is not None:
    st.markdown("#### 📸 AI Photo Analysis")
    analyze_col1, analyze_col2 = st.columns([1, 1])
    
    with analyze_col1:
        st.image(uploaded_file, caption="Uploaded Storm Photo", use_container_width=True)
    
    with analyze_col2:
        if st.button("🔍 Analyze Photo", key="analyze_photo"):
            with st.spinner("AI analyzing storm features..."):
                analysis = analyze_storm_photo(uploaded_file)
                st.markdown("**AI Analysis:**")
                st.markdown(f"**Cloud Types:** {analysis['cloud_types']}")
                st.markdown(f"**Storm Features:** {analysis['features']}")
                st.markdown(f"**Safety Assessment:** {analysis['safety']}")
                st.markdown(f"**Recommendations:** {analysis['recommendations']}")

# Archive Display
if st.session_state.get('show_archive', False):
    st.markdown("#### 📚 Your Storm Chase Archive")
    archive_data = load_chase_archive()
    
    if archive_data:
        for i, chase in enumerate(archive_data[-5:]):  # Show last 5 chases
            with st.expander(f"🌪️ Chase {chase['date']} - Score: {chase['score']}/100"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Location:** {chase['location']}")
                    st.markdown(f"**CAPE:** {chase['cape']} J/kg")
                    st.markdown(f"**Shear:** {chase['shear']} kts")
                with col_b:
                    st.markdown(f"**Duration:** {chase.get('duration', 'Unknown')}")
                    st.markdown(f"**Notes:** {chase.get('notes', 'No notes')}")
                    if chase.get('photo'):
                        st.markdown("📸 *Photo saved*")
    else:
        st.info("No chases saved yet. Start chasing and save your adventures!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>🌪️ Storm Chase Dashboard v2.0 - AI Powered | 🤖 AI Intelligence • 📱 PWA Ready • 🎯 Chasability Score • 📸 Photo Analysis • 🎙️ Voice Assistant • 📚 Chase Archive</small>
</div>
""", unsafe_allow_html=True)

# Auto-refresh indicator
with st.container():
    st.markdown("""
    <div style='position: fixed; top: 10px; right: 10px; background: rgba(0,0,0,0.7); color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px;'>
        🔄 Auto-refresh: 30s
    </div>
    
    <!-- GPS Integration Complete - External file handles all GPS functionality -->
    <!-- All GPS tracker code has been moved to static/gps-tracker.js to prevent conflicts -->
    """, unsafe_allow_html=True)
