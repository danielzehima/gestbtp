// GESTBTP — Service Worker (PWA)
// Stratégie : network-first pour les pages (toujours à jour), cache-first
// pour les assets statiques (rapide), page hors-ligne en secours.

const CACHE = 'gestbtp-v2';
const OFFLINE_URL = '/offline';

// Assets pré-mis en cache à l'installation
const PRECACHE = [
  OFFLINE_URL,
  '/static/css/main.css',
  '/static/js/app.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/img/logo.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // On ne gère que le GET ; le reste (POST...) passe directement au réseau
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Ne pas intercepter les autres domaines (CDN, Supabase, Open-Meteo...)
  if (url.origin !== self.location.origin) return;

  // CSS/JS -> network-first (toujours la dernière version ; repli cache hors-ligne)
  if (url.pathname.startsWith('/static/') &&
      (url.pathname.endsWith('.js') || url.pathname.endsWith('.css'))) {
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // Autres assets statiques (images, icônes, manifest) -> cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) =>
        cached || fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        }).catch(() => cached)
      )
    );
    return;
  }

  // Pages / navigation -> network-first, repli sur cache puis page offline
  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() =>
        caches.match(req).then((cached) => cached || caches.match(OFFLINE_URL))
      )
  );
});
