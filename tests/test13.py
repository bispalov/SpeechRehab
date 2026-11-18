import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright

import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sr_site import make_root, serve, shots_dir
ROOT = make_root()
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
class Q(http.server.ThreadingHTTPServer): pass
H.log_message = lambda *a: None
srv = Q(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = 'http://127.0.0.1:%d/SpeechRehab/index.html' % srv.server_address[1]

MOCK = r"""
try { if (localStorage.getItem("sr.tour.offer") === null) localStorage.setItem("sr.tour.offer", "0"); } catch (e) {}
window.__spoken = []; window.__srQueue = []; window.__srLive = 0;
class FakeSR {
  constructor(){ this.lang=''; this.maxAlternatives=1; }
  start(){ window.__srLive++; this._on=true; const me=this;
    setTimeout(()=>{ me.onstart && me.onstart();
      const job = window.__srQueue.shift();
      if (!job || job==='hold') return;
      setTimeout(()=>{ if(!me._on) return;
        if (job.error) { me.onerror && me.onerror({error: job.error}); }
        else { const r=[...job.alts.map(t=>({transcript:t}))]; r.isFinal=true;
               me.onresult && me.onresult({results:[r], resultIndex:0}); }
        me._end(); }, 20);
    }, 10); }
  _end(){ if(!this._on) return; this._on=false; window.__srLive--; this.onend && this.onend(); }
  stop(){ this._end(); }
  abort(){ if(!this._on) return; this.onerror && this.onerror({error:'aborted'}); this._end(); }
}
window.SpeechRecognition = FakeSR; window.webkitSpeechRecognition = FakeSR;
const _speak = speechSynthesis.speak.bind(speechSynthesis);
speechSynthesis.speak = u => { window.__spoken.push(u.text); setTimeout(()=>{u.onstart&&u.onstart(); u.onend&&u.onend();},5); };
Object.defineProperty(navigator, 'serviceWorker', {get(){return {register:()=>Promise.reject(new Error('blocked')), addEventListener(){}}}});
"""

fails = []; n = 0
def ok(cond, name):
    global n; n += 1
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context()
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    ctx.add_init_script(MOCK)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(500)
    ev = pg.evaluate
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")

    MODES = ['full', 'ser', 'listen', 'wr', 'quiz', 'abc', 'hear', 'phr']
    for lang in ['ru', 'uk', 'en']:
        info = ev(f"(()=>{{const P=helpParse('{lang}'); return [P.items.length, HELP_KEYS.length, P.keysOk, P.items.map(i=>i.key+'|'+i.title.replace(/<[^>]+>/g,''))]}})()")
        ok(info[0] == info[1] and info[2], f'{lang}: items {info[0]} = keys {info[1]}')
        t = dict(x.split('|', 1) for x in info[3])
        exp = {'ru': {'m_full': '🧩 Полный тренажёр', 'm_phr': '🗣 Мои фразы', 'nav': 'Кнопки вверху и «Назад»', 'counters': 'Счётчики', 'pron': 'Проверка произношения', 'stats': '📊 Статистика', 's_idlehint': '💡 Подсказка, если долго нет действия', 's_fb': 'Открыто внутри Facebook или другого приложения', 'dict': '📚 Свой словарь', 'offline': 'Без интернета и установка', 's_abcset': '🔤 Азбука, 🎤 Подсказка по сказанному и 🗣 Мои фразы'},
               'uk': {'m_full': '🧩 Повний тренажер', 'nav': 'Кнопки вгорі та «Назад»', 'counters': 'Лічильники', 'stats': '📊 Статистика', 'offline': 'Без інтернету та встановлення'},
               'en': {'m_full': '🧩 Full trainer', 'nav': 'Header buttons and “Back”', 'counters': 'Counters', 'pron': 'Checking your pronunciation', 'offline': 'Offline use and installing'}}[lang]
        bad = [k for k, v in exp.items() if t.get(k) != v]
        ok(not bad, f'{lang}: keys point to right headings ' + str([(k, t.get(k)) for k in bad]))
        mk = ev("Object.values(HELP_MODE).flat().filter(k=>!HELP_KEYS.includes(k))")
        ok(mk == [], 'mode lists use existing keys')
    ok(ev("helpParse('ru').items.find(i=>i.key==='m_listen').html.startsWith('Одно слово')"), 'item text starts with a capital letter')
    # стартовый экран: оглавление
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("goHome(); openHelp()"); pg.wait_for_timeout(100)
    D = "[...document.querySelectorAll('#helpBody details.hp-item')]"
    ok(ev(D + ".length") == 42 and ev(D + ".every(d=>!d.open)"), 'start screen: all 39 items, collapsed')
    ok(ev("document.getElementById('helpTitle').innerText") == 'Справка' and 'Нажмите на заголовок' in ev("document.getElementById('helpBody').innerText"), 'title and note')
    ok(ev("document.querySelectorAll('#helpBody h3').length") == 3, 'group headings for list sections')
    # раскрытие по заголовку
    ev("document.querySelector('#helpBody details[data-key=\"s_strict\"] summary').click()")
    ok(ev("document.querySelector('#helpBody details[data-key=\"s_strict\"]').open") is True and 'лишними не считаются' in ev("document.querySelector('#helpBody details[data-key=\"s_strict\"]').innerText"), 'item opens on tap')
    sh = ev("document.querySelector('#helpBody details summary').getBoundingClientRect().height")
    ok(sh >= 52, 'summary at least 52px: ' + str(sh))
    ev("document.querySelector('#helpBody .hp-toggle').click()")
    ok(ev(D + ".every(d=>d.open)") and ev("document.querySelector('#helpBody .hp-toggle').textContent") == '▲ Свернуть все пункты', 'expand all')
    ev("document.querySelector('#helpBody .hp-toggle').click()")
    ok(ev(D + ".every(d=>!d.open)") and ev("document.querySelector('#helpBody .hp-toggle').textContent") == '▼ Раскрыть все пункты', 'collapse all')
    tc = ev("document.getElementById('helpBody').textContent")
    ok('стра-нИ-ца' in tc, 'collapsed text available via textContent')
    ev("closeHelp()")
    # справка по режиму
    NAMES = {'full': '🧩 Полный тренажёр', 'ser': '🔢 Перечисления', 'listen': '👂 Тренировка слуха', 'wr': '✍️ Письмо', 'quiz': '📝 Тест на слух', 'abc': '🔤 Азбука', 'hear': '🎤 Подсказка по сказанному', 'phr': '🗣 Мои фразы'}
    for m in MODES:
        ev(f"quiz.active=false; goHome(); startMode('{m}')"); pg.wait_for_timeout(150)
        ev("openHelp()"); pg.wait_for_timeout(80)
        keys = ev(D + ".map(d=>d.dataset.key)")
        ok(ev("document.getElementById('helpTitle').innerText") == '❓ Справка: ' + NAMES[m], f'{m}: mode title')
        ok(keys == ev(f"HELP_MODE['{m}']") and ev(D + ".every(d=>d.open)"), f'{m}: own items, open {keys}')
        ok(keys[0] == 'm_' + m, f'{m}: mode item first')
        # окно настроек не влияет
        ev("closeHelp(); openSettings(); openHelp()")
        ok(ev("document.getElementById('helpTitle').innerText") == '❓ Справка: ' + NAMES[m], f'{m}: help over settings still about mode')
        ev("closeHelp(); closeSettings()")
    ev("openHelp(); document.querySelector('#helpBody .hp-all').click()")
    ok(ev(D + ".length") == 42 and ev("document.getElementById('helpTitle').innerText") == 'Справка', '«Вся справка» opens contents')
    ev("closeHelp()")
    # «Назад» закрывает справку
    ev("quiz.active=false; goHome(); startMode('abc')"); pg.mouse.click(5, 5); pg.wait_for_timeout(100)
    ev("openHelp()"); pg.wait_for_timeout(100)
    pg.go_back(); pg.wait_for_timeout(300)
    ok(ev("overlayOpen('helpOverlay')") is False and ev("screenName") == 'abc', 'Back closes help, stays in mode')
    # смена языка при открытой справке режима
    ev("openHelp(); toggleLanguage()"); pg.wait_for_timeout(100)
    ok(ev("document.getElementById('helpTitle').innerText").startswith('❓ Help: ') or ev("document.getElementById('helpTitle').innerText").startswith('❓ Довідка: '), 'language change keeps mode view: ' + ev("document.getElementById('helpTitle').innerText"))
    ev("closeHelp()")
    # вёрстка
    for w in [277, 360]:
        for lang in ['ru', 'uk', 'en']:
            pg.set_viewport_size({'width': w, 'height': 640})
            ev(f"localStorage.setItem('app_lang','{lang}')"); pg.reload(); pg.wait_for_timeout(500)
            ev("openHelp(); document.querySelector('#helpBody .hp-toggle').click()"); pg.wait_for_timeout(100)
            ov = ev("[...document.querySelectorAll('#helpOverlay *')].filter(e=>e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).length")
            ok(ov == 0 and ev("document.documentElement.scrollWidth") <= w, f'layout {w} {lang} contents')
            ev("closeHelp(); startMode('full'); openHelp()"); pg.wait_for_timeout(100)
            ov = ev("[...document.querySelectorAll('#helpOverlay *')].filter(e=>e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).length")
            ok(ov == 0, f'layout {w} {lang} mode help')
            ev("closeHelp()")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
