// Service worker: кэширует всё приложение, чтобы оно работало без интернета.
// При любом изменении файлов приложения увеличивайте номер версии (v1 -> v2 ...).
const CACHE = 'speech-rehab-v29';
const ASSETS = [
  '/SpeechRehab/',
  '/SpeechRehab/index.html',
  '/SpeechRehab/manifest.json',
  '/SpeechRehab/accents.js',
  '/SpeechRehab/dict-en.js',
  '/SpeechRehab/dict-uk.js',
  '/SpeechRehab/dict-ru.js',
  '/SpeechRehab/icon-192.png',
  '/SpeechRehab/icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  // Запросы к другим сайтам (онлайн-поиск слов) идут напрямую, без кэша и подмены страницей приложения
  if (new URL(e.request.url).origin !== self.location.origin) return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true })
      .then(r => r || fetch(e.request).catch(() => caches.match('/SpeechRehab/index.html')))
  );
});
