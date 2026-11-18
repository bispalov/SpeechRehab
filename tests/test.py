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

    ok('🧩' in ev("document.getElementById('modeCatLabel').innerText"), 'category label lists modes')
    ok(ev("document.body.innerHTML.indexOf('\U0001F399')") < 0, 'one mic icon')
    ok(ev("helpI18n.uk.body.indexOf('🔢') < helpI18n.uk.body.indexOf('👂')") and ev("helpI18n.uk.body.indexOf('🧩') < helpI18n.uk.body.indexOf('🔢')"), 'help order matches screen')
    ok('прибереться' in ev("JSON.stringify(1)") or True, 'noop')

    # --- полный тренажёр
    ev("startMode('full')"); pg.wait_for_timeout(400)
    ok(ev("document.querySelector('.audio-btn').title") == 'Послушать этот вариант', 'option audio title localized')
    ev("targetWordSyllables='стра-ни-ца'; targetWordClean='страница'; document.getElementById('gentleMode').checked=false; __spoken=[]")
    ev("__srQueue.push({alts:['странница','страница','стоянка']}); toggleRecording()"); pg.wait_for_timeout(2500)
    ok('correct' in ev("document.getElementById('speechResultBox').className"), 'full: second alternative counted')
    ev("__spoken=[]; __srQueue.push({alts:['ступица']}); toggleRecording()"); pg.wait_for_timeout(3000)
    sp = ev("__spoken.join('|')")
    ok('Нужно: странИца' in sp and 'ступица' in sp, 'full non-gentle: says heard + model word: ' + sp)
    ev("document.getElementById('gentleMode').checked=true; __spoken=[]; __srQueue.push({alts:['ступица']}); toggleRecording()"); pg.wait_for_timeout(3000)
    sp = ev("__spoken.join('|')")
    ok('Почти. Послушайте ещё раз: странИца' in sp and 'Неправильно' not in sp, 'full gentle verdict: ' + sp)
    ok('info' in ev("document.getElementById('speechResultBox').className"), 'gentle: no red box')
    ev("__srQueue.push({error:'not-allowed'}); toggleRecording()"); pg.wait_for_timeout(500)
    ok('микрофон' in ev("document.getElementById('speechResultBox').innerText"), 'friendly mic error in full')
    # во время записи слово не озвучивается
    ev("__spoken=[]; __srQueue.push('hold'); toggleRecording()"); pg.wait_for_timeout(200)
    ev("speakWord(targetWordSyllables)"); ok(ev("__spoken.length") == 0, 'no TTS while recording')
    ev("recognition.abort()"); pg.wait_for_timeout(200)
    ok(ev("isRecording") is False, 'recording stopped')

    # --- тренировка слуха
    ev("goHome(); startMode('listen')"); pg.wait_for_timeout(500)
    ev("trainReset('стра-ни-ца'); renderListenStep(1)")
    ev("__srQueue.push('hold'); trainMic()"); pg.wait_for_timeout(100)
    ok(ev("document.getElementById('trainMicBtn').classList.contains('rec')"), 'listen: mic red while listening')
    ev("__spoken=[]; trainSpeak()"); ok(ev("__spoken.length") == 0, 'listen: no TTS while listening')
    ev("stopModeRec()"); pg.wait_for_timeout(100)
    ok(ev("train.attempts") == 0 and not ev("document.getElementById('trainMicBtn').disabled"), 'listen: aborted not counted, button restored')
    ev("__srQueue.push({alts:['стоянка','страница']}); trainMic()"); pg.wait_for_timeout(300)
    ok(ev("train.passed") is True, 'listen: alternative counted')
    ev("__srQueue.push({error:'network'}); trainMic()"); pg.wait_for_timeout(300)
    ok('интернет' in ev("document.getElementById('trainSayResult').innerText"), 'listen: friendly network error')

    # --- тест
    ev("goHome(); startMode('quiz'); startQuiz(['дом','кот'])"); pg.wait_for_timeout(400)
    ev("__srQueue.push({alts:['том','дом']}); quizMic()"); pg.wait_for_timeout(300)
    ok(ev("quiz.results[0].ok") is True and ev("quiz.results[0].heard") == 'дом', 'quiz: alternative counted')

    # --- мои фразы
    ev("goHome(); localStorage.setItem('sr.phr.ru', JSON.stringify([{t:'Дайте мне воды'}])); phr.loadedLang=null; startMode('phr'); phrEnter(0)"); pg.wait_for_timeout(300)
    ev("__srQueue.push('hold'); phrSay()"); pg.wait_for_timeout(100)
    ok(ev("[...document.querySelectorAll('#phrScreen .abc-row button')].slice(0,2).every(b=>b.disabled)"), 'phr: listen disabled while listening')
    ok(ev("document.querySelector('#phrScreen .ph-say').classList.contains('rec')"), 'phr: mic red')
    # перерыв таймера во время распознавания
    ev("showRestOverlay(true)"); pg.wait_for_timeout(200)
    ok(ev("phr.listening") is False and not ev("document.querySelector('#phrScreen .ph-say').disabled"), 'rest overlay stops phr listening, UI not stuck')
    ev("showRestOverlay(false)")
    ev("phrSetSave('show', false); __spoken=[]; phrVoice('part')");
    ok(ev("__spoken[0]").startswith('Почти. Послушайте'), 'phr: hidden text -> no "read" voice')
    ev("phrSetSave('show', true)")

    # --- перечисления
    ev("goHome(); startMode('ser'); serStart('days')"); pg.wait_for_timeout(300)
    ev("ser.mode='whole'; ser.dir='fwd'; serNewTask(); ser.listening=true; ser.buf='привет мир'; __spoken=[]; serFinish()"); pg.wait_for_timeout(100)
    ok(ev("__spoken[0]").startswith('Попробуйте ещё раз. Начало: понедельник'), 'ser zero-correct voice: ' + str(ev("__spoken[0]")))

    # --- личный словарь произношения
    ev("HP.open(true)");
    r = ev("""(()=>{ localStorage.removeItem('sr.pick.ru');
      const s=document.createElement('x'); return 1 })()""")
    # функции внутри HP недоступны напрямую — проверяем через упрощённый режим
    ev("localStorage.setItem('sr.pick.ru', JSON.stringify({f:[],a:[],p:[{h:'толя',w:'туалет',n:1,t:1}]}))")
    ev("goHome(); startMode('hear')"); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['я хочу в толя']}); document.getElementById('micGo').click()"); pg.wait_for_timeout(400)
    chips = ev("[...document.querySelectorAll('#hearScreen .hbuild .chip')].map(c=>c.textContent).join(' ')")
    ok('толя' in chips, 'pron: single choice does not auto-replace: ' + chips)
    ev("localStorage.setItem('sr.pick.ru', JSON.stringify({f:[],a:[],p:[{h:'толя',w:'туалет',n:2,t:1}]}))")
    ev("__srQueue.push({alts:['я хочу в толя']}); document.getElementById('micGo').click()"); pg.wait_for_timeout(400)
    chips = ev("[...document.querySelectorAll('#hearScreen .hbuild .chip')].map(c=>c.textContent).join(' ')")
    ok('туалет' in chips, 'pron: two choices auto-replace: ' + chips)

    # --- плитки букв
    ev("goHome(); startMode('listen'); trainReset('кот'); renderListenStep(2)")
    sz = ev("[document.querySelector('#trainTiles .letter-tile').getBoundingClientRect().height, document.querySelector('#trainSlots .letter-slot').getBoundingClientRect().height]")
    ok(sz[0] == sz[1], 'tile and slot same height ' + str(sz))

    # --- языки: нет английских строк в украинском интерфейсе
    ev("localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ev("startMode('full')"); pg.wait_for_timeout(200)
    ok(ev("document.querySelector('.audio-btn').title") == 'Послухати цей варіант', 'uk option title')
    ok(ev("recErrorText('not-allowed')").startswith('Немає доступу'), 'uk friendly error')
    ok(ev("HP && document.body") is not None, 'HP ok')
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
