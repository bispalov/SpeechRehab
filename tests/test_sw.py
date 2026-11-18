"""Настоящий service worker: обновление с первого открытия, офлайн, чужие кэши на том же сайте не трогаются,
копия приложения в другой папке живёт со своим кэшем.

«Старая версия» делается из текущих файлов: номер в sw.js (VER) и index.html (APP_VERSION) уменьшается на 1.
Запуск: python3 tests/test_sw.py   (приложение — папка над tests/ или переменная SR_APP)
"""
import os, re, sys, json, shutil, tempfile, threading, http.server, functools
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sr_site import APP

SKIP = {'tests', '.git', '__pycache__'}
D = tempfile.mkdtemp(prefix='srsw-')
S = os.path.join(D, 'SpeechRehab') + os.sep
R = os.path.join(D, 'rehab') + os.sep

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
    def end_headers(self):
        self.send_header('Cache-Control', 'max-age=0'); super().end_headers()

srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(H, directory=D))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:%d' % srv.server_address[1]

res = []
def ok(c, n): res.append(bool(c)); print(('PASS ' if c else 'FAIL ') + n)

sw_src = open(os.path.join(APP, 'sw.js'), encoding='utf-8').read()
ix_src = open(os.path.join(APP, 'index.html'), encoding='utf-8').read()
N = int(re.search(r"const VER = 'speech-rehab-v(\d+)'", sw_src).group(1))
assert int(re.search(r'const APP_VERSION = (\d+);', ix_src).group(1)) == N, 'VER и APP_VERSION должны совпадать'

def put_app(folder, ver):
    """Все файлы приложения в папку; номер версии — ver."""
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(APP):
        if f in SKIP or f.startswith('.'): continue
        src = os.path.join(APP, f)
        if os.path.isdir(src): shutil.copytree(src, folder + f, dirs_exist_ok=True)
        else: shutil.copy(src, folder + f)
    open(folder + 'sw.js', 'w', encoding='utf-8').write(sw_src.replace("speech-rehab-v%d'" % N, "speech-rehab-v%d'" % ver))
    open(folder + 'index.html', 'w', encoding='utf-8').write(ix_src.replace('const APP_VERSION = %d;' % N, 'const APP_VERSION = %d;' % ver))

ver = lambda pg: pg.evaluate("typeof APP_VERSION!=='undefined' ? APP_VERSION : 0")
keys = lambda pg: sorted(pg.evaluate("caches.keys()"))
OLD, NEW = 'speech-rehab-v%d:/SpeechRehab/' % (N - 1), 'speech-rehab-v%d:/SpeechRehab/' % N
FOREIGN = ['govorim-v70:/Govorim/', 'govorim-v61', 'myvoice-v6:/MyVoice/']

put_app(S, N - 1)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); ctx = b.new_context(); pg = ctx.new_page()
        pg.goto(BASE + '/SpeechRehab/index.html'); pg.wait_for_timeout(2000); pg.reload(); pg.wait_for_timeout(1500)
        ok(ver(pg) == N - 1 and pg.evaluate("!!navigator.serviceWorker.controller"), 'v%d installed and controlled' % (N - 1))
        ok(OLD in keys(pg), 'cache named with the folder: ' + OLD)
        pg.evaluate("Promise.all(%s.map(n => caches.open(n).then(c => c.put('/' + n.replace(/[^a-z0-9]/gi, '') + '/x', new Response('x')))))" % json.dumps(FOREIGN))
        put_app(S, N)
        pg.reload(); pg.wait_for_timeout(3000)
        ok(ver(pg) == N, 'v%d -> v%d on the first open (got %s)' % (N - 1, N, ver(pg)))
        k = keys(pg); print('caches:', k)
        ok(NEW in k and OLD not in k, 'own old cache removed, new one created')
        ok(all(f in k for f in FOREIGN), 'caches of Govorim / MyVoice kept')
        cached = pg.evaluate("caches.open(%s).then(c => c.keys()).then(r => r.map(x => new URL(x.url).pathname))" % json.dumps(NEW))
        need = ['/SpeechRehab/index.html', '/SpeechRehab/manifest.json', '/SpeechRehab/dict-ru.js']
        ok(all(x in cached for x in need), 'app files precached: ' + str(sorted(cached))[:300])
        man = pg.evaluate("fetch('manifest.json').then(r => r.json())")
        ok(man.get('id') == '/SpeechRehab/' and man.get('start_url') == './index.html' and man.get('scope') == './', 'manifest id / start_url / scope')
        ctx.set_offline(True); pg.reload(); pg.wait_for_timeout(2000)
        ok(ver(pg) == N, 'works offline')
        ok(pg.evaluate("typeof SPEECH_DICT_RU !== 'undefined' || typeof dictRu !== 'undefined' || document.querySelectorAll('.mode-card').length > 5"), 'offline: home screen with modes')
        ctx.set_offline(False)
        # копия в другой папке
        put_app(R, N)
        pg2 = ctx.new_page(); pg2.goto(BASE + '/rehab/'); pg2.wait_for_timeout(2000); pg2.reload(); pg2.wait_for_timeout(1500)
        k = keys(pg2); print('caches:', k)
        ok('speech-rehab-v%d:/rehab/' % N in k and NEW in k and all(f in k for f in FOREIGN), 'copy in /rehab/ has its own cache, others kept')
        ctx.set_offline(True); pg2.reload(); pg2.wait_for_timeout(1500)
        ok(ver(pg2) == N, 'copy works offline'); ctx.set_offline(False)
        w = open(R + 'sw.js', encoding='utf-8').read().replace("speech-rehab-v%d'" % N, "speech-rehab-v%d'" % (N + 1))
        open(R + 'sw.js', 'w', encoding='utf-8').write(w)
        pg2.reload(); pg2.wait_for_timeout(3000)
        k = keys(pg2); print('caches:', k)
        ok('speech-rehab-v%d:/rehab/' % (N + 1) in k and 'speech-rehab-v%d:/rehab/' % N not in k and NEW in k, 'update of the copy removes only its own old cache')
        b.close()
finally:
    srv.shutdown(); shutil.rmtree(D, True)
print('%d/%d passed' % (sum(res), len(res)))
