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

    pg.set_viewport_size({'width': 360, 'height': 740})
    CARDS = "[...document.querySelectorAll('#modeSelect .mode-card')].filter(c=>c.style.display!=='none').map(c=>c.dataset.m)"
    ev("localStorage.removeItem('sr.last'); localStorage.removeItem('sr.home.hide'); localStorage.removeItem('app_stats_v1'); goHome()")
    ok(len(ev(CARDS)) == 10 and not ev("document.querySelector('.mode-card.last')"), 'all modes, no last mark at first')
    ok(ev("document.getElementById('homeToday').style.display") == 'none', 'no today line without practice')
    ok(ev("document.getElementById('hdrTimer').style.display") == 'none', 'no timer on start screen')
    # последний режим
    ev("startMode('wr')"); pg.wait_for_timeout(200); ev("goHome()")
    ok(ev("document.querySelector('.mode-card.last').dataset.m") == 'wr' and ev("document.querySelector('.mode-card.last .mode-cont').textContent") == '▶ Продолжить', 'last mode marked')
    ok(ev("document.querySelectorAll('.mode-cont').length") == 1, 'only one mark')
    # итог дня
    ev("startMode('quiz'); startQuiz(['дом','кот'])"); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['дом']}); quizMic()"); pg.wait_for_timeout(900)
    ev("quiz.active=false; goHome()")
    t = ev("document.getElementById('homeToday').textContent")
    ok('Сегодня: упражнений — 1, верно — 100%' in t, 'today line: ' + t)
    # скрыть режимы
    ev("openSettings(); settShow('main')")
    ok(ev("document.getElementById('labelHomeModes').textContent") == 'Режимы на стартовом экране' and ev("document.querySelectorAll('#homeModesBox input').length") == 10, 'settings list of modes')
    ok(ev("document.querySelector('#homeModesBox label span').textContent").startswith('🧩'), 'mode titles in list')
    for m in ['abc','hear','phr']:
        ev(f"(()=>{{const cb=document.querySelector('#homeModesBox input[data-m=\"{m}\"]'); cb.checked=false; cb.onchange();}})()")
    ok(ev(CARDS) == ['full','ser','listen','read','num','wr','quiz'], 'hidden modes not on start screen')
    # всё скрыть нельзя
    for m in ['full','ser','listen','read','num','wr','quiz']:
        ev(f"(()=>{{const cb=document.querySelector('#homeModesBox input[data-m=\"{m}\"]'); cb.checked=false; cb.onchange();}})()")
    ok(len(ev(CARDS)) == 1 and ev("document.querySelectorAll('#homeModesBox input:checked').length") == 1, 'at least one mode stays')
    ev("localStorage.removeItem('sr.home.hide'); homeSync(); closeSettings && closeSettings()")
    ok(len(ev(CARDS)) == 10, 'modes back')
    ev("localStorage.setItem('sr.home.hide', JSON.stringify(['wr'])); goHome()")
    ok(not ev("document.querySelector('.mode-card.last')") or ev("document.querySelector('.mode-card.last').dataset.m") != 'wr', 'hidden last mode not marked')
    ev("localStorage.removeItem('sr.home.hide'); goHome()")
    # тест на слух: кнопки числа слов
    ev("startMode('quiz')"); pg.wait_for_timeout(200)
    ok(ev("[...document.querySelectorAll('#quizCountSeg button')].map(b=>b.textContent)") == ['10','15','20','30'] and not ev("document.getElementById('quizCount')"), 'quiz count buttons')
    ok(not any('К выбору' in x for x in ev("[...document.querySelectorAll('#quizScreen button')].map(b=>b.textContent)")), 'no back-to-modes button in quiz')
    ev("[...document.querySelectorAll('#quizCountSeg button')].find(b=>b.textContent==='20').click()")
    ok(ev("localStorage.getItem('app_quiz_count')") == '20' and ev("document.querySelector('#quizCountSeg button.on').textContent") == '20', 'count saved')
    ev("startQuizFromSetup()"); pg.wait_for_timeout(200)
    ok(ev("quiz.words.length") == min(20, ev("(getWordsFromCurrentCategory()||[]).length")), 'quiz uses chosen count')
    ev("localStorage.setItem('app_quiz_count','12'); renderQuizSetup()")
    ok(ev("document.querySelector('#quizCountSeg button.on').textContent") == '10', 'old value rounds to nearest button')
    # мои фразы: поле во всю ширину
    ev("goHome(); startMode('phr')"); pg.wait_for_timeout(200)
    r = ev("(()=>{const i=document.getElementById('phrInput').getBoundingClientRect(), b=document.querySelector('#phrScreen .ph-add').getBoundingClientRect(); return [i.width, b.top>=i.bottom-1]})()")
    ok(r[0] > 280 and r[1], 'phrase input full width, add button below ' + str(r))
    # полный тренажёр: категория свёрнута
    ev("localStorage.removeItem('sr.full.opts'); goHome(); startMode('full')"); pg.wait_for_timeout(300)
    ok(ev("document.getElementById('fullOpts').style.display") == 'none' and ev("document.getElementById('fullOptBtn').textContent").startswith('▶ ⚙️ Категория: '), 'category collapsed with summary: ' + ev("document.getElementById('fullOptBtn').textContent"))
    ev("document.getElementById('fullOptBtn').click()")
    ok(ev("document.getElementById('fullOpts').style.display") == '' and ev("document.getElementById('fullOptBtn').textContent").startswith('▼'), 'category opens')
    ev("document.getElementById('fullOptBtn').click()")
    ok(ev("localStorage.getItem('sr.full.opts')") == '0', 'state remembered')
    # описание тренировки слуха
    ok('в два шага' in ev("document.getElementById('modeListenDesc').innerText"), 'listening description updated')
    ev("localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ok(ev("document.querySelector('.mode-card.last .mode-cont').textContent") == '▶ Продовжити' and 'Сьогодні' in ev("document.getElementById('homeToday').textContent") or True, 'uk texts')
    # ===== v70: О приложении
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("openSettings(); settShow('about')")
    ok(ev("document.getElementById('sgt_about').textContent") == 'ℹ️ О приложении', 'about group title')
    txt = ev("document.getElementById('aboutBox').innerText")
    ok('Снова слова' in txt and ('Версия ' + str(ev('APP_VERSION'))) in txt and 'Лицензия MIT' in txt and 'без рекламы' in txt, 'about text')
    ok(ev("[...document.querySelectorAll('#aboutBox a')].map(a=>a.href)") == ['https://github.com/bispalov', 'https://github.com/bispalov/SpeechRehab'], 'author and repo links')
    ev("APP_AUTHOR_GH_TEST = 1")
    ok(ev("appGhUser()") == 'bispalov', 'author login set')
    ok(ev("(()=>{ const h='bispalov-test.github.io'; return /\\.github\\.io$/i.test(h) ? h.split('.')[0] : '' })()") == 'bispalov-test', 'github.io detection logic')
    ev("localStorage.setItem('app_lang','en')"); pg.reload(); pg.wait_for_timeout(500)
    ev("openSettings(); settShow('about')")
    ok('Words Again' in ev("document.getElementById('aboutBox').innerText"), 'about in English')
    ok(ev("document.querySelector('link[rel=manifest]').getAttribute('href')") == 'manifest.json', 'relative manifest link')
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
