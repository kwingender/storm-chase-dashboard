// Storm Chase Dashboard Service Worker
const CACHE_NAME = 'storm-chase-v1';
const STATIC_CACHE_URLS = [
  '/',
  '/static/manifest.json',
  '/static/mobile-styles.css',
  '/static/gps-tracker.js',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.js'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_CACHE_URLS.filter(url => !url.startsWith('https:')));
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== CACHE_NAME) {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
  // Skip non-HTTP requests
  if (!event.request.url.startsWith('http')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached version or fetch from network
        if (response) {
          return response;
        }

        // Clone the request for fetching
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then(response => {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone response for caching
          const responseToCache = response.clone();

          // Cache successful responses
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });

          return response;
        }).catch(() => {
          // Return offline page for navigation requests
          if (event.request.mode === 'navigate') {
            return caches.match('/');
          }
          return new Response('Offline - Storm Chase Dashboard', {
            status: 503,
            statusText: 'Service Unavailable'
          });
        });
      })
  );
});

// Background sync for GPS data when online
self.addEventListener('sync', event => {
  if (event.tag === 'sync-gps-data') {
    event.waitUntil(syncGPSData());
  }
});

// Push notifications for severe weather alerts
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/icon-192x192.png',
      badge: '/static/icon-192x192.png',
      vibrate: [200, 100, 200],
      tag: 'weather-alert',
      actions: [
        {action: 'view', title: 'View Dashboard'},
        {action: 'dismiss', title: 'Dismiss'}
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'view' || !event.action) {
    event.waitUntil(
      self.clients.openWindow('/')
    );
  }
});

// Sync GPS data function
async function syncGPSData() {
  try {
    // Get stored GPS data from IndexedDB
    const gpsData = await getStoredGPSData();
    if (gpsData.length > 0) {
      // Send to server when online
      await fetch('/api/sync-gps', {
        method: 'POST',
        body: JSON.stringify(gpsData),
        headers: {'Content-Type': 'application/json'}
      });
      
      // Clear stored data after successful sync
      await clearStoredGPSData();
    }
  } catch (error) {
    console.error('GPS sync failed:', error);
  }
}

// IndexedDB helpers for offline GPS storage
async function getStoredGPSData() {
  // Implementation would go here for IndexedDB operations
  return [];
}

async function clearStoredGPSData() {
  // Implementation would go here for IndexedDB operations
}