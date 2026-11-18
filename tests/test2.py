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


    # --- группы настроек
    ok(ev("document.querySelectorAll('#settingsPanel .sg').length") == 8, '8 settings groups')
    ok(ev("!document.getElementById('setPhrVoice') && !document.getElementById('setSerVoice') && !document.getElementById('setPhrAuto')"), 'old split settings removed')
    ev("openSettings()")
    ok(ev("document.querySelector('.sg.open').dataset.g") == 'main', 'main group open on start screen')
    ok(ev("getComputedStyle(document.getElementById('optionsCountSelect')).display") != 'none' and not ev("document.getElementById('optionsCountSelect').offsetParent"), 'other groups collapsed')
    ev("settToggle('ser')"); ok(ev("document.querySelectorAll('.sg.open').length") == 1 and ev("document.querySelector('.sg.open').dataset.g") == 'ser', 'one group at a time')
    ok(ev("document.getElementById('sgt_abc').textContent").startswith('🔤 Азбука'), 'group titles localized')
    # --- системная «Назад»: закрывает окно настроек, выход не происходит
    ok(ev("history.state && history.state.sr") == 1, 'guard state pushed when overlay open')
    ev("history.back()"); pg.wait_for_timeout(300)
    ok(ev("document.getElementById('settingsOverlay').classList.contains('hidden')"), 'back closes settings')
    ev("startMode('ser')"); pg.wait_for_timeout(200); ev("openSettings()")
    ok(ev("document.querySelector('.sg.open').dataset.g") == 'ser', 'settings open group of current mode')
    ev("closeSettings(); serStart('days')"); pg.wait_for_timeout(200)
    ev("history.back()"); pg.wait_for_timeout(300)
    ok(ev("screenName") == 'ser' and ev("ser.view") == 'list', 'back: series task -> list')
    ev("history.back()"); pg.wait_for_timeout(300)
    ok(ev("screenName") == 'select', 'back: list -> mode selection')
    pg.wait_for_timeout(300)
    ok(not (ev("history.state && history.state.sr") or False), 'no guard on start screen (next back exits)')
    # --- общая голосовая оценка
    ev("localStorage.setItem('sr.verdict','false'); __spoken=[]; startMode('phr'); phr.list=[{t:'Доброе утро',n:0,k:0,l:0}]; phrEnter(0); __spoken=[]; phrVoice('ok'); serVoice('x')")
    ok(ev("__spoken.length") == 0, 'verdict off silences phrases and series')
    ev("goHome(); startMode('full'); targetWordSyllables='дом'; targetWordClean='дом'; __spoken=[]; __srQueue.push({alts:['ком']}); toggleRecording()"); pg.wait_for_timeout(2600)
    ok(not any('Почти' in x or 'Неправ' in x for x in ev("__spoken")), 'verdict off silences full trainer')
    ev("localStorage.setItem('sr.verdict','true')")
    # --- автоозвучивание фразы следует общей настройке
    ev("document.getElementById('autoSpeak').checked=false; goHome(); startMode('phr'); phr.list=[{t:'Доброе утро',n:0,k:0,l:0}]; __spoken=[]; phrEnter(0)"); pg.wait_for_timeout(100)
    ok(ev("__spoken.length") == 0, 'phrase not auto-spoken when autoSpeak off')
    ev("document.getElementById('autoSpeak').checked=true; __spoken=[]; phrEnter(0)"); pg.wait_for_timeout(100)
    ok(ev("__spoken.length") == 1, 'phrase auto-spoken when autoSpeak on')
    # --- таймер в шапке
    ev("goHome(); document.getElementById('timerEnabled').checked=true; toggleTimerFeature()")
    ok(ev("document.getElementById('hdrTimer').style.display") == 'none', 'v68: header timer hidden on start screen')
    ev("startMode('full')"); ok(ev("document.getElementById('hdrTimer').style.display") == '' and ':' in ev("document.getElementById('hdrTimer').textContent"), 'v68: header timer shown in full trainer')
    ok(ev("getComputedStyle(document.querySelector('#fullTrainer .timer-status-row')).display") == 'none', 'v68: in-mode timer row hidden')
    ev("goHome(); startMode('listen'); document.getElementById('hdrTimer').click()")
    ok(ev("isTimerPaused") is True and '⏸' in ev("document.getElementById('hdrTimer').textContent"), 'header timer pause')
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    ok(ev("document.getElementById('hdrTimer').style.display") == 'none', 'header timer hidden when timer off')
    # --- тест: один повтор
    ev("localStorage.setItem('sr.quiz.replay','true'); startMode('quiz'); startQuiz(['дом','кот'])"); pg.wait_for_timeout(400)
    ok(ev("!!document.getElementById('quizReplayBtn')"), 'quiz replay button')
    ev("__spoken=[]; quizReplay(); quizReplay()")
    ok(ev("__spoken.length") == 1 and not ev("!!document.getElementById('quizReplayBtn')"), 'quiz replay only once')
    ev("__srQueue.push({alts:['дом']}); quizMic()"); pg.wait_for_timeout(200); ev("quizAdvance()")
    ok(ev("!!document.getElementById('quizReplayBtn')"), 'quiz replay available for next word')
    ev("localStorage.setItem('sr.quiz.replay','false'); quiz.active=false; goHome(); startMode('quiz'); startQuiz(['дом'])"); pg.wait_for_timeout(300)
    ok(not ev("!!document.getElementById('quizReplayBtn')"), 'no replay when off')
    # --- тренировка слуха: «Я сказал(а) верно»
    ev("quiz.active=false; goHome(); startMode('listen'); trainReset('кот'); renderListenStep(1); __srQueue.push({alts:['код']}); trainMic()"); pg.wait_for_timeout(300)
    ok(ev("[...document.querySelectorAll('#trainSayResult button')].some(b=>b.textContent.includes('верно'))"), 'listen: self-confirm button')
    ev("trainCountOk()")
    ok(ev("train.passed") and 'Записано' in ev("document.getElementById('trainSayResult').innerText"), 'listen: self-confirm counted')
    # --- Азбука
    ev("goHome(); startMode('abc')"); pg.wait_for_timeout(200)
    ok(ev("document.querySelectorAll('#abcScreen .abc-kbh .abc-kbt').length") == 3, 'abc: keyboard header has 3 buttons')
    ok(ev("document.querySelector('#abcScreen .abc-fnarr').textContent") == '▶' and ev("document.querySelectorAll('#abcScreen .abc-fnw').length") == 0, 'abc: block collapsed with ▶')
    ev("document.querySelector('#abcScreen .abc-fnbtn').click()")
    ok(ev("document.querySelector('#abcScreen .abc-fnarr').textContent") == '▼' and ev("document.querySelectorAll('#abcScreen .abc-fnw').length") > 20, 'abc: block expanded with ▼')
    ok(ev("(()=>{const b=document.querySelector('#abcScreen .abc-fnbtn'), h=document.querySelector('#abcScreen .abc-sec'); return !!(b.compareDocumentPosition(h) & Node.DOCUMENT_POSITION_FOLLOWING)})()"), 'abc: block above typing line')
    ev("[...document.querySelectorAll('#abcScreen .abc-fnw')].find(b=>b.textContent==='я').click()")
    ev("abcState.fn=false")
    ok(ev("abcState.line.join(' ')") == 'я', 'abc: add "я"')
    ev("abcState.prefix='д'; abcRender(); [...document.querySelectorAll('#abcScreen .abc-word')].find(b=>b.textContent.includes('дом')).click()")
    ok(ev("abcState.line.join(' ')") == 'я дом', 'abc: word after short word')
    ev("abcState.prefix='д'; abcRender()")
    ok(ev("abcState.keys.includes('для')"), 'abc: short words searchable by letters')
    ev("[...document.querySelectorAll('#abcScreen .abc-line .ph-chip')][0].click()")
    ok(ev("abcState.line.join(' ')") == 'дом', 'abc: tap removes word')
    ev("abcState.line=['я','хочу','дом']; abcRender(); [...document.querySelectorAll('#abcScreen button')].find(b=>b.textContent.includes('Тренировать')).click()"); pg.wait_for_timeout(200)
    ok(ev("screenName") == 'phr' and ev("phr.tmp.t") == 'Я хочу дом', 'abc: train phrase')
    ok('Азбуке' in ev("document.querySelector('#phrScreen .ph-back').textContent"), 'abc: back label')
    ev("history.back()"); pg.wait_for_timeout(300)
    ok(ev("screenName") == 'abc' and ev("abcState.line.length") == 3, 'back from training keeps abc phrase')
    ev("localStorage.setItem('sr.hear.tap','true'); abcState.prefix='к'; abcRender(); __spoken=[]; [...document.querySelectorAll('#abcScreen .abc-word')].find(b=>b.textContent.includes('кот')).click()")
    ok(ev("abcState.line.length") == 3 and ev("__spoken.length") == 1, 'abc tap mode: tap only speaks')
    ev("localStorage.setItem('sr.hear.tap','false')")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
