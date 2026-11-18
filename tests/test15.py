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
    ctx = b.new_context(viewport={'width': 360, 'height': 740})
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(400)
    ev = pg.evaluate
    ev("localStorage.setItem('app_lang','ru'); localStorage.setItem('sr.tour.offer','0')"); pg.reload(); pg.wait_for_timeout(600)
    # ===== числа: распознавание пишет цифрами
    for lang, word, alt in [('ru','восемь','8'), ('uk','вісім','8'), ('en','eight','8'), ('ru','двадцать один','21'), ('uk',"п'ять",'5'), ('ru','сто','100'), ('ru','двести','200')]:
        ev(f"currentLang='{lang}'")
        ok(ev(f"isSpeechMatch({alt!r}, {word!r}, true)"), f'{lang}: "{alt}" = "{word}" (strict)')
        ok(ev(f"speechMatchAlts({{transcript:{alt!r}, alts:[{alt!r}]}}, {word!r}, false).heard") == word, f'{lang}: heard shown as words: {word}')
    ev("currentLang='ru'")
    ok(not ev("isSpeechMatch('7', 'восемь', false)"), 'wrong number still wrong')
    ok(ev("isSpeechMatch('восемь', 'восемь', true)"), 'word still ok')
    ok(ev("phrCompare('мне восемь лет', ['мне 8 лет']).ok") == ev("phrCompare('мне восемь лет', ['мне восемь лет']).ok"), 'phrase with number: digits = words')
    ok(ev("phrCompare('у меня 2 внука', ['у меня 2 внука']).ok") == ev("phrCompare('у меня 2 внука', ['у меня 2 внука']).ok"), 'phrase with digits unchanged')
    # полный тренажёр: сказано «8», нужно «восемь»
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(600)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature(); startMode('full')"); pg.wait_for_timeout(300)
    ev("targetWordClean='восемь'; __srQueue.push({alts:['8']}); document.getElementById('recordBtn').click()"); pg.wait_for_timeout(500)
    box = ev("document.getElementById('speechResultBox').className + ' | ' + document.getElementById('speechResultBox').innerText")
    ok('correct' in box and 'восемь' in box and '"8"' not in box, 'full trainer: "8" accepted for "восемь": ' + box)
    ev("quiz.active=false; goHome()")
    # ===== таймер
    ev("document.getElementById('timerEnabled').checked=true; document.getElementById('playMinutes').value='5'; document.getElementById('restMinutes').value='10'; saveSettings(); toggleTimerFeature(); resetTimer()")
    ev("startMode('full')"); pg.wait_for_timeout(2300)
    left = ev("timerSecondsLeft"); ok(left <= 298, 'timer counts in a mode: ' + str(left))
    ev("timerSecondsLeft = 123; timerSave()")
    pg.reload(); pg.wait_for_timeout(700)
    ok(ev("timerMode") == 'play' and 120 <= ev("timerSecondsLeft") <= 123, 'play time survives reload: ' + str(ev("timerSecondsLeft")))
    ok(ev("getComputedStyle(document.documentElement).overscrollBehaviorY") == 'none' and ev("getComputedStyle(document.body).overscrollBehaviorY") == 'none', 'pull-to-refresh disabled (overscroll-behavior-y: none)')
    # долго не было (дольше перерыва) — игра заново
    ev("window.timerSave=()=>{}; localStorage.setItem('sr.timer', JSON.stringify({m:'play', left:50, pend:0, t: Date.now() - 11*60*1000}))"); pg.reload(); pg.wait_for_timeout(700)
    ok(ev("timerMode") == 'play' and ev("timerSecondsLeft") >= 298, 'away longer than the break: fresh play time')
    # перерыв переживает перезагрузку
    ev("startMode('full'); timerSecondsLeft = 2"); pg.wait_for_timeout(3000)
    ok(ev("timerMode") == 'rest' and ev("!document.getElementById('restOverlay').classList.contains('hidden')"), 'rest starts')
    pg.reload(); pg.wait_for_timeout(800)
    ok(ev("timerMode") == 'rest' and ev("!document.getElementById('restOverlay').classList.contains('hidden')") and 590 <= ev("timerSecondsLeft") <= 600, 'rest survives reload: ' + str(ev("timerSecondsLeft")))
    # перерыв уже прошёл, пока приложение было закрыто
    ev("window.timerSave=()=>{}; localStorage.setItem('sr.timer', JSON.stringify({m:'rest', left:60, pend:0, t: Date.now() - 2*60*1000}))"); pg.reload(); pg.wait_for_timeout(700)
    ok(ev("timerMode") == 'play' and ev("document.getElementById('restOverlay').classList.contains('hidden')") and ev("timerSecondsLeft") >= 298, 'rest over while closed: play')
    # время вышло в «Азбуке» (перерыв ждёт фразу) — после перезагрузки перерыв начинается
    ev("window.timerSave=()=>{}; localStorage.setItem('sr.timer', JSON.stringify({m:'play', left:0, pend:1, t: Date.now() - 5000}))"); pg.reload(); pg.wait_for_timeout(800)
    ok(ev("timerMode") == 'rest', 'pending rest after reload starts')
    ev("skipRest()")
    ok(ev("JSON.parse(localStorage.getItem('sr.timer')).m") == 'play', 'skip rest saved')
    # выключенный таймер
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    ok(ev("localStorage.getItem('sr.timer')") is None, 'disabling the timer clears saved state')
    pg.reload(); pg.wait_for_timeout(600)
    ok(ev("!timerInterval") and ev("document.getElementById('restOverlay').classList.contains('hidden')"), 'disabled timer stays off after reload')
    # первый отрезок игры — по настройке, а не 5 минут
    ev("document.getElementById('timerEnabled').checked=true; toggleTimerFeature(); document.getElementById('playMinutes').value='15'; updateTimerSettings()"); pg.reload(); pg.wait_for_timeout(600)
    ok(ev("timerSecondsLeft") >= 15*60 - 2, 'first play period uses the setting: ' + str(ev("timerSecondsLeft")))
    ok(not errs, 'no page errors: ' + str(errs))
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
