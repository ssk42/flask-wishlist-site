const CACHE_NAME = 'wishlist-v1';
const OFFLINE_URL = '/static/offline.html';

const ASSETS_TO_CACHE = [
    OFFLINE_URL,
    '/static/images/icons/icon-192x192.png',
    '/static/images/icons/icon-512x512.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => {
                return caches.match(OFFLINE_URL);
            })
        );
    }
});
