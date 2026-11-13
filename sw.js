// Service worker: сохраняет приложение на устройстве, чтобы оно работало без интернета.
// При любом изменении файлов приложения увеличивайте номер версии (v1 -> v2 ...).
const CACHE = 'speech-rehab-v71';
// Папка приложения определяется по адресу самого sw.js (на GitHub Pages это /SpeechRehab/),
// поэтому приложение можно разместить в любой папке любого сайта без правки этого файла.
const BASE = new URL('./', self.location).pathname;
const PAGE = BASE + 'index.html';
const ASSETS = ['', 'index.html', 'manifest.json', 'accents.js', 'dict-en.js', 'dict-uk.js', 'dict-ru.js', 'icon-192.png', 'icon-512.png'].map(f => BASE + f);
const isPage = p => p === BASE || p === PAGE;
const isLex = p => p.startsWith(BASE + 'lex/') && /^[a-z]+\.txt$/.test(p.slice(BASE.length + 4));

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
  if (e.request.mode === 'navigate' || isPage(url.pathname)) {
    e.respondWith(
      fetchFresh(PAGE, 4000)
        .then(res => {
          if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(PAGE, copy)); return res; }
          return caches.match(PAGE).then(r => r || res);
        })
        .catch(() => caches.match(PAGE))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true })
      .then(r => r || fetch(e.request).then(res => {
        // необязательные частотные списки lex/*.txt сохраняем в кэш, чтобы они работали без интернета
        if (res.ok && isLex(url.pathname)) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => caches.match(PAGE)))
  );
});
