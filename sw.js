// Service worker: сохраняет приложение на устройстве, чтобы оно работало без интернета.
// При любом изменении файлов приложения увеличивайте номер версии (v1 -> v2 ...).
const CACHE = 'speech-rehab-v64';
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
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS.map(u => new Request(u, { cache: 'reload' })))));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Запрос к сайту с ограничением по времени: при плохой связи страница быстро берётся из сохранённой копии
function fetchFresh(url, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error('timeout')), ms);
    fetch(url, { cache: 'no-cache' }).then(r => { clearTimeout(t); resolve(r); }, err => { clearTimeout(t); reject(err); });
  });
}

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  // Запросы к другим сайтам (онлайн-поиск слов) идут напрямую, без кэша и подмены страницей приложения
  if (url.origin !== self.location.origin) return;
  // Сама страница: при наличии интернета — свежая с сайта (так обновления видны сразу), без интернета — сохранённая копия
  if (e.request.mode === 'navigate' || /\/SpeechRehab\/(index\.html)?$/.test(url.pathname)) {
    e.respondWith(
      fetchFresh('/SpeechRehab/index.html', 4000)
        .then(res => {
          if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put('/SpeechRehab/index.html', copy)); return res; }
          return caches.match('/SpeechRehab/index.html').then(r => r || res);
        })
        .catch(() => caches.match('/SpeechRehab/index.html'))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true })
      .then(r => r || fetch(e.request).then(res => {
        // необязательные частотные списки lex/*.txt сохраняем в кэш, чтобы они работали без интернета
        if (res.ok && /\/SpeechRehab\/lex\/[a-z]+\.txt$/.test(url.pathname)) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => caches.match('/SpeechRehab/index.html')))
  );
});
