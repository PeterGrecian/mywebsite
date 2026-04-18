// Service Worker for petergrecian.co.uk
const CACHE_NAME = 'petergrecian-v2';

// Only these paths belong to the PWA — everything else passes through to Lambda
const PWA_PATHS = new Set(['/', '/index.html', '/manifest.json', '/sw.js',
  '/icon-192.png', '/icon-192-maskable.png', '/icon-512.png', '/icon-512-maskable.png']);

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(['/', '/index.html', '/manifest.json']);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Only intercept PWA assets — let everything else go straight to network
  if (!PWA_PATHS.has(url.pathname)) {
    return;
  }

  // Cache-first for PWA assets
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
