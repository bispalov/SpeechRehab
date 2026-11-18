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
    def restart():
        pg.reload(); pg.wait_for_timeout(700)
    ev("localStorage.setItem('app_lang','ru'); localStorage.removeItem('sr.resume'); localStorage.removeItem('sr.home.hide')"); restart()
    # по умолчанию выключено
    ev("startMode('ser')"); pg.wait_for_timeout(200)
    ok(ev("localStorage.getItem('sr.lastScr')") == 'ser', 'last screen remembered')
    restart(); ok(ev("screenName") == 'select', 'off: start screen after restart')
    # включено
    ev("openSettings(); settShow('main')")
    ok(ev("document.getElementById('labelResume').textContent") == 'При запуске открывать режим, в котором закончили' and ev("document.getElementById('resumeOnStart').checked") is False, 'setting shown, off by default')
    ev("document.getElementById('resumeOnStart').click()"); ok(ev("localStorage.getItem('sr.resume')") == '1', 'setting saved')
    ev("closeSettings()")
    for m in ['full', 'ser', 'listen', 'wr', 'quiz', 'abc', 'hear', 'phr']:
        ev(f"goHome(); startMode('{m}')"); pg.wait_for_timeout(250)
        ev("openSettings()")   # окно не запоминается
        restart()
        ok(ev("screenName") == m, f'on: restart opens {m}')
        ok(ev("__srLive") == 0, f'{m}: microphone not started')
        ok(ev("__spoken.length") == 0, f'{m}: nothing spoken without a touch: ' + str(ev("__spoken")))
    # «Тренировка слуха» — начальный шаг; «Перечисления» — список рядов
    ev("goHome(); startMode('listen'); renderListenStep(2)"); restart()
    ok(ev("train.step") == 1, 'listen opens on its first step')
    ev("goHome(); startMode('ser'); serStart('days')"); restart()
    ok(ev("ser.view") != 'do', 'sequences open on the list, not mid-task')
    # после касания озвучка работает
    pg.mouse.click(5, 300); pg.wait_for_timeout(100)
    ev("__spoken=[]; serSpeak('понедельник', 1)"); pg.wait_for_timeout(100)
    ok(ev("__spoken.length") == 1, 'speech works after first touch')
    # вернулись на стартовый экран
    ev("goHome()"); restart(); ok(ev("screenName") == 'select', 'finished on start screen -> start screen')
    # скрытый режим
    ev("startMode('wr'); localStorage.setItem('sr.home.hide', JSON.stringify(['wr']))"); restart()
    ok(ev("screenName") == 'select', 'hidden mode -> start screen')
    ev("localStorage.removeItem('sr.home.hide')")
    # испорченное значение
    ev("localStorage.setItem('sr.lastScr', 'qwerty')"); restart(); ok(ev("screenName") == 'select', 'bad value -> start screen')
    ev("localStorage.setItem('sr.lastScr', '')"); restart(); ok(ev("screenName") == 'select', 'empty value -> start screen')
    # «Назад» с восстановленного режима — свежий запуск (новая вкладка, без касаний и без старой истории)
    ev("localStorage.setItem('sr.lastScr','abc'); localStorage.setItem('sr.resume','1')")
    p2 = ctx.new_page(); p2.on('pageerror', lambda e: errs.append(str(e)))
    p2.goto(URL); p2.wait_for_timeout(800)
    e2 = p2.evaluate
    ok(e2("screenName") == 'abc' and not e2("history.state && history.state.sr"), 'restored: history entry waits for a touch')
    p2.mouse.click(5, 120); p2.wait_for_timeout(150)
    ok(e2("!!(history.state && history.state.sr)"), 'history entry added on first touch')
    p2.go_back(); p2.wait_for_timeout(300)
    ok(e2("screenName") == 'select', 'Back from restored mode -> start screen')
    # обычный вход по-прежнему создаёт запись сразу
    e2("startMode('phr')"); p2.wait_for_timeout(100)
    ok(e2("!!(history.state && history.state.sr)"), 'manual entry: history entry at once')
    p2.close()
    # вёрстка группы main при 277 px
    for lang in ['ru', 'uk', 'en']:
        pg.set_viewport_size({'width': 277, 'height': 600})
        ev(f"localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.resume','0')"); restart()
        ev("openSettings(); settShow('main')"); pg.wait_for_timeout(100)
        over = ev("[...document.querySelectorAll('#settingsPanel *')].filter(e=>e.offsetParent && e.getBoundingClientRect().right > innerWidth + 1).length")
        ok(over == 0 and ev("document.documentElement.scrollWidth") <= 277, f'main group fits 277 px [{lang}]')
        ok(len(ev("document.getElementById('labelResume').textContent")) > 10, f'label text [{lang}]')
        ev("closeSettings()")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
