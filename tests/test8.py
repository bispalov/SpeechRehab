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

    W = "[...document.querySelectorAll('#trainTiles .letter-tile')].map(b=>Math.round(b.getBoundingClientRect().width))"
    pg.set_viewport_size({'width': 360, 'height': 740})
    ev("goHome(); startMode('listen'); trainReset('ко-ро-ва'); renderListenStep(1)"); pg.wait_for_timeout(400)
    txt = ev("document.getElementById('listenScreen').innerText")
    ok('Шаг 1 из 2' in txt and 'Послушайте и повторите слово' in txt, 'step 1: listen and repeat together')
    ok(ev("document.getElementById('trainMicBtn').textContent") == '🎤 Повторить', 'repeat button label')
    ok(ev("!!document.getElementById('trainNextSay')"), 'next button on step 1')
    ok(ev("__spoken.length") >= 1, 'word plays by itself')
    ev("__spoken=[]; __srQueue.push({alts:['корова']}); trainMic()"); pg.wait_for_timeout(400)
    ok('корова' in ev("document.getElementById('trainSayResult').innerText") and ev("train.passed") is True, 'result shown on the same screen')
    ok(ev("document.getElementById('trainMicBtn').textContent") == '🎤 Ещё раз', 'again label after try')
    # требование верного повтора
    ev("document.getElementById('requireSpeech').checked=true; trainReset('ко-ро-ва'); renderListenStep(1)"); pg.wait_for_timeout(100)
    ok(ev("document.getElementById('trainNextSay').disabled") is True, 'require: next locked before correct')
    ev("__srQueue.push({alts:['корова']}); trainMic()"); pg.wait_for_timeout(400)
    ok(ev("document.getElementById('trainNextSay').disabled") is False, 'require: unlocked after correct')
    ev("document.getElementById('requireSpeech').checked=false")
    # шаг 2: плитки
    ev("document.getElementById('trainNextSay').click()"); pg.wait_for_timeout(200)
    ok('Шаг 2 из 2' in ev("document.getElementById('listenScreen').innerText"), 'step 2 is letters')
    w = ev(W); ok(max(w) < 100 and len(w) == 6, 'tiles compact: ' + str(w))
    tops = ev("new Set([...document.querySelectorAll('#trainTiles .letter-tile')].map(b=>Math.round(b.getBoundingClientRect().top))).size")
    ok(tops <= 2, 'tiles in at most two rows: ' + str(tops))
    # собрать неверно: «корова» → «кровао»
    def put(word): ev("'%s'.split('').forEach(ch=>{const i=train.tiles.findIndex(t=>!t.used&&t.ch===ch); trainPlace(i)})" % word)
    put('коровa'.replace('a','а')[:0] + 'кровао')
    bad = ev("[...document.querySelectorAll('#trainSlots .letter-tile')].map(b=>b.classList.contains('bad'))")
    ok(bad == [False, True, True, True, True, True] or bad.count(True) >= 1, 'wrong letters red: ' + str(bad))
    ok('красные буквы' in ev("document.getElementById('trainBuildMsg').innerText"), 'hint to tap red letters')
    # исправить на месте: убрать 2-ю букву — место остаётся пустым, остальные не сдвигаются
    ev("trainRemove(1)")
    ok(ev("document.querySelectorAll('#trainSlots .letter-slot').length") == 1 and ev("[...document.querySelectorAll('#trainSlots > *')][1].classList.contains('letter-slot')"), 'hole stays in place')
    ok(ev("train.placed[2]") is not None, 'other letters not shifted')
    ev("trainClear()"); put('корова')
    ok(ev("train.builtOk") is True and 'Верно' in ev("document.getElementById('trainBuildMsg').innerText"), 'fixed build ok')
    ok(ev("train.firstBuilt") == 'кровао' and ev("train.firstBuiltOk") is False, 'first attempt kept')
    # «Стереть» убирает последнюю поставленную
    ev("trainRemove(3); trainPlace(train.tiles.findIndex(t=>!t.used)); trainUndo()")
    ok(ev("train.placed[3]") is None and ev("train.placed[5]") is not None, 'undo removes last placed letter')
    ev("trainClear()"); put('корова')
    s0 = ev("JSON.stringify(JSON.parse(localStorage.getItem('app_stats_v1')||'{}'))")
    ev("document.getElementById('trainNextBuild').click()"); pg.wait_for_timeout(200)
    txt = ev("document.getElementById('listenScreen').innerText")
    ok('кровао' in txt and 'Потом исправлено' in txt, 'summary shows first attempt and fix')
    btns = ev("[...document.querySelectorAll('#listenScreen button')].map(b=>b.textContent)")
    ok(btns[0] == '➡ Следующее слово' and '🔁 Ещё раз это слово' in btns and not any('К выбору' in b for b in btns), 'summary buttons: ' + str(btns))
    ok(ev("!!document.querySelector('#listenScreen .train-pic')") == bool(ev("wrPic('ко-ро-ва')")), 'picture shown when available')
    ev("goHome(); startMode('listen'); trainReset('кот'); renderListenStep(3)")
    ok(ev("!!document.querySelector('#listenScreen .train-pic')") == bool(ev("wrPic('кот')")), 'picture for кот: ' + str(ev("wrPic('кот')")))
    # крупный шрифт и узкий экран: плитки не вылезают
    pg.set_viewport_size({'width': 277, 'height': 600})
    ev("trainReset('стра-ни-ца'); renderListenStep(2)")
    ok(ev("document.documentElement.scrollWidth") <= 277, 'no horizontal scroll at 277')
    # ===== v64: голосовой отзыв при сборке и в итоге
    pg.set_viewport_size({'width': 360, 'height': 740})
    ev("localStorage.setItem('sr.verdict','true'); goHome(); startMode('listen'); trainReset('ко-ро-ва'); renderListenStep(1)"); pg.wait_for_timeout(400)
    ev("__srQueue.push({alts:['корова']}); trainMic()"); pg.wait_for_timeout(2200)
    ev("renderListenStep(2); __spoken=[]")
    put('корово'[:5]); ok(ev("__spoken.length") == 0, 'no voice until complete')
    ev("trainClear(); __spoken=[]"); put('кровао')
    ok(ev("__spoken") == ['Не совсем. Замените красные буквы.'], 'wrong build voice: ' + str(ev("__spoken")))
    ev("trainRemove(5); __spoken=[]; trainPlace(train.tiles.findIndex(t=>!t.used))")
    ok(ev("__spoken") == [], 'same wrong word not repeated')
    ev("trainClear(); __spoken=[]"); put('корова')
    sp = ev("__spoken"); ok(len(sp) == 2 and sp[0] == 'Верно!' and 'коров' in sp[1].lower(), 'correct build: "Верно!" + word ' + str(sp))
    ev("__spoken=[]; renderListenStep(3)"); pg.wait_for_timeout(100)
    ok(ev("__spoken") == [], 'no praise when build was not first time')
    # всё с первого раза
    ev("trainReset('кот'); renderListenStep(1)"); pg.wait_for_timeout(400)
    ev("__srQueue.push({alts:['кот']}); trainMic()"); pg.wait_for_timeout(2200)
    ev("renderListenStep(2)"); put('кот')
    ev("__spoken=[]; renderListenStep(3)"); pg.wait_for_timeout(100)
    ok(ev("__spoken") == ['Отлично! Всё с первого раза.'], 'praise when all first time')
    ev("localStorage.setItem('sr.verdict','false'); trainReset('кот'); renderListenStep(2); __spoken=[]"); put('кот')
    ok(ev("__spoken") == [], 'verdict off: silent')
    ev("localStorage.removeItem('sr.verdict')")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
