// GPS Tracker for Storm Chase Dashboard
class StormChaseGPSTracker {
  constructor() {
    this.watchId = null;
    this.isTracking = false;
    this.lastPosition = null;
    this.trackingInterval = 30000; // 30 seconds
    this.minDistance = 50; // minimum 50 meters between points
    this.voiceEnabled = true;
    this.speechSynthesis = window.speechSynthesis;
    
    // Initialize GPS tracking
    this.init();
  }
  
  init() {
    // Check if geolocation is supported
    if (!navigator.geolocation) {
      console.error('Geolocation not supported');
      this.showError('GPS not supported on this device');
      return;
    }
    
    // Request permission and get initial position
    this.getCurrentPosition();
    
    // Set up voice synthesis
    this.setupVoiceAlerts();
    
    // Listen for Streamlit events
    this.setupStreamlitIntegration();
    
    // Check for existing tracking state
    this.restoreTrackingState();
    
    // Update GPS status indicator
    this.updateGPSStatus();
  }
  
  getCurrentPosition() {
    const options = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 60000
    };
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        this.handlePosition(position, false);
        this.updateStreamlitCoordinates(position.coords);
      },
      (error) => this.handleError(error),
      options
    );
  }
  
  startTracking() {
    if (this.isTracking) return;
    
    console.log('Starting GPS tracking...');
    this.isTracking = true;
    
    const options = {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 30000
    };
    
    // Start watching position
    this.watchId = navigator.geolocation.watchPosition(
      (position) => this.handlePosition(position, true),
      (error) => this.handleError(error),
      options
    );
    
    // Store tracking state
    localStorage.setItem('storm_chase_tracking', 'true');
    localStorage.setItem('storm_chase_start_time', Date.now().toString());
    
    // Update UI
    this.updateGPSStatus();
    this.announceVoice('GPS tracking started');
    
    // Notify Streamlit
    this.notifyStreamlit('tracking_started', { timestamp: Date.now() });
  }
  
  stopTracking() {
    if (!this.isTracking) return;
    
    console.log('Stopping GPS tracking...');
    this.isTracking = false;
    
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
    
    // Clear stored state
    localStorage.removeItem('storm_chase_tracking');
    localStorage.removeItem('storm_chase_start_time');
    
    // Update UI
    this.updateGPSStatus();
    this.announceVoice('GPS tracking stopped');
    
    // Notify Streamlit
    this.notifyStreamlit('tracking_stopped', { timestamp: Date.now() });
  }
  
  handlePosition(position, autoAdd = false) {
    const { latitude, longitude, accuracy, timestamp } = position.coords;
    
    console.log(`GPS Position: ${latitude}, ${longitude} (±${accuracy}m)`);
    
    // Check if we should add this point
    if (autoAdd && this.shouldAddBreadcrumb(latitude, longitude)) {
      this.addBreadcrumb(latitude, longitude, timestamp);
    }
    
    // Update current position in Streamlit
    this.updateStreamlitCoordinates(position.coords);
    
    // Store last position
    this.lastPosition = { latitude, longitude, timestamp };
    
    // Update GPS status
    this.updateGPSStatus();
  }
  
  shouldAddBreadcrumb(lat, lon) {
    if (!this.lastPosition || !this.isTracking) return false;
    
    // Calculate distance from last breadcrumb
    const distance = this.calculateDistance(
      this.lastPosition.latitude, this.lastPosition.longitude,
      lat, lon
    );
    
    // Add if moved more than minimum distance
    return distance >= this.minDistance;
  }
  
  addBreadcrumb(lat, lon, timestamp) {
    console.log(`Adding breadcrumb: ${lat}, ${lon}`);
    
    // Notify Streamlit to add breadcrumb
    this.notifyStreamlit('add_breadcrumb', {
      lat: lat,
      lon: lon,
      timestamp: timestamp,
      accuracy: this.lastPosition ? this.calculateDistance(
        this.lastPosition.latitude, this.lastPosition.longitude,
        lat, lon
      ) : 0
    });
  }
  
  calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = lat1 * Math.PI/180;
    const φ2 = lat2 * Math.PI/180;
    const Δφ = (lat2-lat1) * Math.PI/180;
    const Δλ = (lon2-lon1) * Math.PI/180;
    
    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    
    return R * c; // Distance in meters
  }
  
  updateStreamlitCoordinates(coords) {
    // Update coordinate inputs in Streamlit
    const latInput = document.querySelector('input[aria-label="Latitude"]');
    const lonInput = document.querySelector('input[aria-label="Longitude"]');
    
    if (latInput && lonInput) {
      latInput.value = coords.latitude.toFixed(4);
      lonInput.value = coords.longitude.toFixed(4);
      
      // Trigger change events
      latInput.dispatchEvent(new Event('input', { bubbles: true }));
      lonInput.dispatchEvent(new Event('input', { bubbles: true }));
      latInput.dispatchEvent(new Event('change', { bubbles: true }));
      lonInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }
  
  handleError(error) {
    let message = 'GPS error: ';
    switch(error.code) {
      case error.PERMISSION_DENIED:
        message += 'Location access denied. Please enable location permissions.';
        break;
      case error.POSITION_UNAVAILABLE:
        message += 'Location information unavailable.';
        break;
      case error.TIMEOUT:
        message += 'Location request timed out.';
        break;
      default:
        message += 'An unknown error occurred.';
        break;
    }
    
    console.error(message);
    this.showError(message);
    this.announceVoice('GPS error occurred');
    
    // Notify Streamlit
    this.notifyStreamlit('gps_error', { message: message });
  }
  
  setupVoiceAlerts() {
    // Check if speech synthesis is available
    if (!this.speechSynthesis) {
      console.warn('Speech synthesis not supported');
      this.voiceEnabled = false;
      return;
    }
    
    // Set up voice preferences
    this.voiceEnabled = localStorage.getItem('voice_alerts') !== 'disabled';
  }
  
  announceVoice(message, urgent = false) {
    if (!this.voiceEnabled || !this.speechSynthesis) return;
    
    // Cancel any ongoing speech
    this.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.rate = urgent ? 1.2 : 1.0;
    utterance.pitch = urgent ? 1.2 : 1.0;
    utterance.volume = urgent ? 1.0 : 0.8;
    
    // Use a clear voice if available
    const voices = this.speechSynthesis.getVoices();
    const preferredVoice = voices.find(voice => 
      voice.lang.startsWith('en') && voice.name.includes('Siri')
    ) || voices.find(voice => voice.lang.startsWith('en'));
    
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }
    
    this.speechSynthesis.speak(utterance);
  }
  
  announceTornadoWarning(warning) {
    const message = `Tornado warning issued for ${warning.area}. Take shelter immediately.`;
    this.announceVoice(message, true);
    
    // Show visual alert
    this.showUrgentAlert('🌪️ TORNADO WARNING', warning.headline);
  }
  
  showUrgentAlert(title, message) {
    // Create urgent alert overlay
    const alertDiv = document.createElement('div');
    alertDiv.className = 'voice-alert urgent-alert';
    alertDiv.innerHTML = `
      <div style="font-size: 24px; margin-bottom: 10px;">${title}</div>
      <div style="font-size: 18px;">${message}</div>
      <button onclick="this.parentElement.remove()" 
              style="margin-top: 15px; padding: 10px 20px; font-size: 16px; 
                     background: white; color: #ff4444; border: none; border-radius: 5px; 
                     cursor: pointer;">DISMISS</button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 30 seconds
    setTimeout(() => {
      if (alertDiv.parentElement) {
        alertDiv.remove();
      }
    }, 30000);
    
    // Vibrate if supported
    if (navigator.vibrate) {
      navigator.vibrate([500, 200, 500, 200, 500]);
    }
  }
  
  showError(message) {
    console.error(message);
    // Could show a toast notification here
  }
  
  updateGPSStatus() {
    let statusDiv = document.querySelector('.gps-status');
    
    if (!statusDiv) {
      statusDiv = document.createElement('div');
      statusDiv.className = 'gps-status';
      document.body.appendChild(statusDiv);
    }
    
    if (this.isTracking) {
      statusDiv.className = 'gps-status gps-active';
      statusDiv.innerHTML = '📍 GPS Tracking Active';
    } else {
      statusDiv.className = 'gps-status gps-inactive';
      statusDiv.innerHTML = '📍 GPS Tracking Inactive';
    }
  }
  
  restoreTrackingState() {
    const wasTracking = localStorage.getItem('storm_chase_tracking') === 'true';
    if (wasTracking) {
      console.log('Restoring GPS tracking state...');
      this.startTracking();
    }
  }
  
  setupStreamlitIntegration() {
    // Listen for Streamlit component messages
    window.addEventListener('message', (event) => {
      if (event.data.type === 'streamlit:componentReady') {
        console.log('Streamlit component ready');
      }
    });
  }
  
  notifyStreamlit(action, data) {
    // Send message to Streamlit parent frame
    const message = {
      type: 'storm_chase_gps',
      action: action,
      data: data
    };
    
    window.parent.postMessage(message, '*');
    
    // Also store in localStorage for Streamlit to pick up
    localStorage.setItem('storm_chase_latest_event', JSON.stringify(message));
  }
  
  // Public methods for Streamlit integration
  toggleTracking() {
    if (this.isTracking) {
      this.stopTracking();
    } else {
      this.startTracking();
    }
  }
  
  addCurrentPosition() {
    if (this.lastPosition) {
      this.addBreadcrumb(
        this.lastPosition.latitude, 
        this.lastPosition.longitude, 
        Date.now()
      );
    } else {
      this.getCurrentPosition();
    }
  }
  
  toggleVoiceAlerts() {
    this.voiceEnabled = !this.voiceEnabled;
    localStorage.setItem('voice_alerts', this.voiceEnabled ? 'enabled' : 'disabled');
    this.announceVoice(this.voiceEnabled ? 'Voice alerts enabled' : 'Voice alerts disabled');
  }
}

// Initialize GPS tracker when page loads
document.addEventListener('DOMContentLoaded', () => {
  console.log('Initializing Storm Chase GPS Tracker...');
  window.stormChaseGPS = new StormChaseGPSTracker();
});

// Make functions available globally for Streamlit
window.toggleGPSTracking = () => window.stormChaseGPS?.toggleTracking();
window.addGPSPosition = () => window.stormChaseGPS?.addCurrentPosition();
window.toggleVoiceAlerts = () => window.stormChaseGPS?.toggleVoiceAlerts();
window.announceTornadoWarning = (warning) => window.stormChaseGPS?.announceTornadoWarning(warning);