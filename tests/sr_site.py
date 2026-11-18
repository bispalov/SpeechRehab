"""Общий запуск сайта для тестов SpeechRehab.

Тесты не зависят от папки конкретного компьютера: приложение берётся из корня репозитория
(папка над tests/) или из переменной окружения SR_APP. Сайт собирается во временной папке
как /SpeechRehab/ и раздаётся на свободном порту.

По умолчанию вместо больших словарей подставляются маленькие заглушки из tests/fixtures
(тесты рассчитаны на них: «корова» = «ко-ро-ва», картинка 🐮 и т. п.), а lex/ и extra-dict.json
не подключаются. SR_REAL_DICTS=1 — подключить настоящие словари.
"""
import os, shutil, tempfile, atexit, threading, http.server, functools

TESTS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.environ.get('SR_APP') or os.path.dirname(TESTS))
FIX = os.path.join(TESTS, 'fixtures')
APP_FILES = ('index.html', 'sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png')
STUBS = ('dict-ru.js', 'dict-uk.js', 'dict-en.js', 'accents.js')


def make_root(real_dicts=None):
    """Временная папка с подпапкой SpeechRehab/ — корень для http-сервера."""
    real = (os.environ.get('SR_REAL_DICTS') == '1') if real_dicts is None else real_dicts
    root = tempfile.mkdtemp(prefix='srtest-')
    site = os.path.join(root, 'SpeechRehab')
    os.makedirs(site)
    if real:
        for f in os.listdir(APP):
            if f in ('tests', '.git'):
                continue
            os.symlink(os.path.join(APP, f), os.path.join(site, f))
    else:
        for f in APP_FILES:
            src = os.path.join(APP, f)
            if os.path.exists(src):
                os.symlink(src, os.path.join(site, f))
        for f in STUBS:
            shutil.copy(os.path.join(FIX, f), site)
    atexit.register(shutil.rmtree, root, True)
    return root


def serve(root, port=0):
    """Поднять http-сервер (порт 0 — любой свободный). Вернуть (сервер, адрес index.html)."""
    H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    H.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, 'http://127.0.0.1:%d/SpeechRehab/index.html' % srv.server_address[1]


def shots_dir():
    d = os.environ.get('SR_SHOTS') or os.path.join(tempfile.gettempdir(), 'sr-shots')
    os.makedirs(d, exist_ok=True)
    return d
