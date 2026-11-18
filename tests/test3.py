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


    # --- название
    ok(ev("document.getElementById('appTitle').innerText") == 'Снова слова' and 'Знову слова' in ev("document.title"), 'new name')
    # --- таймер: на стартовом экране не идёт
    ev("document.getElementById('playMinutes').value='1'; document.getElementById('timerEnabled').checked=true; toggleTimerFeature(); resetTimer()")
    t0 = ev("timerSecondsLeft"); pg.wait_for_timeout(2300)
    ok(ev("timerSecondsLeft") == t0 and ev("document.getElementById('hdrTimer').style.display") == 'none', 'timer idle and hidden on start screen')
    ev("startMode('listen')"); pg.wait_for_timeout(2300)
    ok(ev("timerSecondsLeft") <= t0 - 2, 'timer runs in training mode')
    t1 = ev("timerSecondsLeft"); ev("openSettings()"); pg.wait_for_timeout(2300)
    ok(ev("timerSecondsLeft") == t1, 'timer stops while settings open')
    ev("closeSettings()")
    # перерыв в обычном режиме — сразу
    ev("timerSecondsLeft=1"); pg.wait_for_timeout(1500)
    ok(not ev("document.getElementById('restOverlay').classList.contains('hidden')"), 'rest starts in training mode')
    ev("skipRest(); goHome()")
    # Азбука: перерыв откладывается до озвучки фразы
    ev("startMode('abc'); abcState.line=['я','дом']; abcRender(); timerSecondsLeft=1"); pg.wait_for_timeout(1600)
    ok(ev("restPending") is True and ev("document.getElementById('restOverlay').classList.contains('hidden')") and ev("document.getElementById('hdrTimer').textContent") == '☕', 'abc: rest deferred')
    ev("[...document.querySelectorAll('#abcScreen button')].find(b=>b.textContent.includes('Сказать так')).click()"); pg.wait_for_timeout(2200)
    ok(not ev("document.getElementById('restOverlay').classList.contains('hidden')") and not ev("restPending"), 'abc: rest after phrase spoken')
    ev("skipRest(); goHome(); startMode('hear'); timerSecondsLeft=1"); pg.wait_for_timeout(1600)
    ok(ev("restPending") is True, 'hear: rest deferred')
    ev("goHome()"); pg.wait_for_timeout(200)
    ok(not ev("document.getElementById('restOverlay').classList.contains('hidden')"), 'hear: rest on leaving mode')
    ev("skipRest(); document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    # --- Письмо
    ok(ev("!!document.getElementById('modeWrTitle').innerText.includes('Письмо')"), 'writing mode card')
    ev("localStorage.removeItem('sr.wr.level'); startMode('wr')"); pg.wait_for_timeout(500)
    ok(ev("wr.level") == 1 and ev("!!wrPic(wr.word)") and ev("wr.typed") == ev("wrNorm(wr.target)[0]"), 'level1: picture word, first letter given')
    ok(ev("__spoken.length") > 0, 'word spoken on new task')
    ok(ev("document.querySelectorAll('#wrScreen .abc-letter').length") >= 30, 'keyboard shown')
    T = ev("wrNorm(wr.target)")
    bad = T[0] + ('ы' if T[1:2] != 'ы' else 'а') + T[2:]
    ev("wr.typed=%r; wrCheck()" % bad)
    ok(ev("wr.solved") is False and ev("document.querySelectorAll('#wrScreen .wr-typed mark.diff-bad').length") >= 1, 'wrong letter highlighted')
    ok('Нажмите правильную букву' in ev("document.querySelector('#wrScreen .ph-score').innerText"), 'score with fix hint')
    ev("wrHint()"); ok(ev("wr.typed") == T[:2], 'hint keeps correct start and adds next letter')
    ev("wr.typed=%r; wrRender(true); wrCheck()" % T.upper())
    ok(ev("wr.solved") is True and ev("!!document.querySelector('#wrScreen .ph-great')"), 'correct (case ignored)')
    st = ev("JSON.parse(localStorage.getItem('app_stats_v1')).ru.words[%r]" % T)
    ok(st and st['bad'] == 1 and st['ok'] == 0, 'first check recorded in stats once: ' + str(st))
    ev("wrSetLevel(2)"); pg.wait_for_timeout(400)
    ok(ev("wr.typed") == ev("wrNorm(wr.target)[0]") and not ev("!!document.querySelector('#wrScreen .wr-kpic')"), 'dictation: no picture, first letter hinted')
    ev("wrShow()"); ok(ev("!!document.querySelector('#wrScreen .wr-word')"), 'show word')
    ev("wrKey('а')"); ok(not ev("!!document.querySelector('#wrScreen .wr-word')"), 'shown word hides after typing')
    ev("localStorage.setItem('sr.phr.ru', JSON.stringify([{t:'Доброе утро, мама!'}])); phr.loadedLang=null; wrSetLevel(3)"); pg.wait_for_timeout(400)
    ok(ev("wr.word") == 'Доброе утро, мама!', 'phrase dictation uses my phrases')
    ok(ev("[...document.querySelectorAll('#wrScreen .abc-kbt')].some(b=>b.textContent.includes('Пробел'))"), 'space key for phrases')
    ev("wr.typed='доброе утро мама'; wrCheck()")
    ok(ev("wr.solved") is True, 'phrase: punctuation ignored')

    # --- Письмо: сворачивание панели букв
    ev("goHome(); localStorage.setItem('app_lang','ru'); startMode('wr'); wrSetLevel(2)"); pg.wait_for_timeout(300)
    ok(ev("[...document.querySelectorAll('#wrScreen .abc-kbt')].some(b=>b.textContent.includes('▾'))"), 'wr: hide-letters button')
    ev("[...document.querySelectorAll('#wrScreen .abc-kbt')].find(b=>b.textContent.includes('▾')).click()")
    ok(ev("document.querySelectorAll('#wrScreen .abc-letter').length") == 0 and ev("!!document.querySelector('#wrScreen .wr-typed')") and ev("!!document.querySelector('#wrScreen .wr-check')"), 'wr: letters hidden, typed and check stay')
    ev("[...document.querySelectorAll('#wrScreen .abc-kbt')].find(b=>b.textContent.includes('▴')).click()")
    ok(ev("document.querySelectorAll('#wrScreen .abc-letter').length") > 30, 'wr: letters shown again')
    ok(ev("!!document.getElementById('setWrAutoHide') && document.getElementById('setWrAutoHide').closest('.sg').dataset.g") == 'train', 'wr autohide setting in Words group')
    ev("document.getElementById('setWrAutoHide').checked=true; extraSettingChanged('wrAutoHide'); document.querySelectorAll('#wrScreen .abc-letter')[0].click()")
    ok(ev("document.querySelectorAll('#wrScreen .abc-letter').length") == 0, 'wr: auto-collapse after letter')
    ev("wrBack()"); ok(ev("document.querySelectorAll('#wrScreen .abc-letter').length") > 30, 'wr: erase shows letters again')
    ev("localStorage.removeItem('sr.wr.autohide')")

    ev("wrSetLevel(1)"); pg.wait_for_timeout(300)
    ok(ev("document.querySelector('#wrScreen .wr-given').textContent") == ev("wr.typed") and ev("!!document.querySelector('#wrScreen .wr-gnote')"), 'given first letter marked as hint')
    ev("wrKey('а')"); ok(ev("document.querySelector('#wrScreen .wr-given').textContent.length") == 1, 'typed letter not marked as hint')
    ev("wrClear()"); ok(not ev("!!document.querySelector('#wrScreen .wr-given')"), 'clear removes hint marking')
    ev("wrHint(); wrHint()"); ok(ev("document.querySelector('#wrScreen .wr-given').textContent.length") == 2, 'hint letters marked')

    # --- исправление по месту
    def fixcase(typed, keys, expect, name):
        ev("wrSetLevel(2); wr.word='ко-ро-ва'; wrNew(true)"); pg.wait_for_timeout(100)
        ev("wr.typed=%r; wrRender(true); wrCheck()" % typed)
        for k in keys:
            ev("wrBack()" if k == 'BS' else "wrKey(%r)" % k)
        ok(ev("wr.typed") == expect, name + ': ' + ev("wr.typed"))
    fixcase('кырова', ['о'], 'корова', 'fix: substitution replaced in place')
    ok('Проверить' in ev("document.querySelector('#wrScreen .ph-score').innerText"), 'fix: all fixed -> press Check')
    ev("wrCheck()"); ok(ev("wr.solved") is True, 'fix: solved after check')
    fixcase('кырава', ['о'], 'корава', 'fix: first of two fixed first')
    ok(ev("document.querySelectorAll('#wrScreen mark.wr-curfix').length") == 1 and ev("document.querySelector('#wrScreen mark.wr-curfix').textContent") == 'а', 'fix: frame moves to next error')
    ev("wrKey('о')"); ok(ev("wr.typed") == 'корова', 'fix: second fixed')
    fixcase('крова', ['о'], 'корова', 'fix: missing letter inserted in its place')
    fixcase('коррова', ['BS'], 'корова', 'fix: backspace removes extra letter')
    fixcase('кырова', ['о', 'к'], 'коровак', 'fix: after all fixed, letters append at end')
    ev("wr.typed='кырова'; wr.res=null; wrRender(true); wrCheck(); wrHint()")
    ok(ev("wr.res") is None and ev("wr.typed") == 'ко', 'fix: hint leaves correction mode')
    # --- настройка числа подсказанных букв
    for gn, exp in [('0', ''), ('3', 'кор'), ('1', 'к')]:
        ev("document.getElementById('setWrGiven').value=%r; extraSettingChanged('wrGiven'); wrSetLevel(1); wr.word='ко-ро-ва'; wrNew(true)" % gn)
        ok(ev("wr.typed") == exp and ev("wr.given") == len(exp), 'given letters = ' + gn)
    ok(ev("document.getElementById('optWrG2').textContent") == '2 буквы' and ev("document.getElementById('setWrGiven').closest('.sg').dataset.g") == 'train', 'given setting localized, in Words group')
    ev("wr.word='кот'; localStorage.setItem('sr.wr.given','3'); wrNew(true)")
    ok(ev("wr.typed") == 'ко', 'given never reveals whole word')
    ev("localStorage.setItem('sr.wr.given','1')")

    # --- картинка и 🔊 рядом с полем ввода, касание поля разворачивает буквы
    ev("wrSetLevel(1)"); pg.wait_for_timeout(300)
    ok(ev("!!document.querySelector('#wrScreen .wr-kb .wr-kpic')") and ev("document.querySelector('#wrScreen .wr-kb .wr-kpic').textContent") == ev("wrPic(wr.word)"), 'picture next to input field')
    ev("__spoken=[]; document.querySelector('#wrScreen .wr-ksay').click()"); ok(ev("__spoken.length") == 1, 'speaker next to field speaks word')
    ev("wr.kbOff=true; wrRender(true); document.querySelector('#wrScreen .wr-typed').click()")
    ok(ev("wr.kbOff") is False and ev("document.querySelectorAll('#wrScreen .abc-letter').length") > 30, 'tap on field opens letters')
    ev("document.querySelector('#wrScreen .wr-typed').click()"); ok(ev("wr.kbOff") is False, 'tap on field does not hide letters')
    ev("wrSetLevel(2)"); pg.wait_for_timeout(200)
    ok(not ev("!!document.querySelector('#wrScreen .wr-kpic')") and ev("!!document.querySelector('#wrScreen .wr-ksay')"), 'dictation: no picture, speaker present')

    # --- размер кнопок с буквами
    ev("localStorage.removeItem('sr.kb.small'); wrSetLevel(1)"); pg.wait_for_timeout(200)
    h0 = ev("document.querySelector('#wrScreen .abc-letter').getBoundingClientRect().height")
    ev("document.querySelector('#wrScreen .kb-size').click()")
    h1 = ev("document.querySelector('#wrScreen .abc-letter').getBoundingClientRect().height")
    ok(h1 < h0 and ev("document.querySelector('#wrScreen .kb-size').textContent").startswith('🔠'), 'smaller letters in writing (%s -> %s)' % (h0, h1))
    ev("goHome(); startMode('abc')"); pg.wait_for_timeout(200)
    ok(ev("document.querySelector('#abcScreen .abc-kb').classList.contains('kb-small')"), 'size shared with ABC')
    ev("document.querySelector('#abcScreen .kb-size').click()")
    ok(not ev("document.querySelector('#abcScreen .abc-kb').classList.contains('kb-small')") and ev("document.querySelector('#abcScreen .kb-size').textContent").startswith('🔡'), 'back to normal in ABC')
    ev("goHome(); startMode('wr')"); pg.wait_for_timeout(200)

    # --- подсказка первых букв на всех уровнях
    ev("localStorage.setItem('sr.wr.given','2'); wrSetLevel(2); wr.word='ко-ро-ва'; wrNew(true)")
    ok(ev("wr.typed") == 'ко' and ev("document.querySelector('#wrScreen .wr-given').textContent") == 'ко', 'dictation: 2 hint letters')
    ev("localStorage.setItem('sr.phr.ru', JSON.stringify([{t:'Доброе утро'}])); phr.loadedLang=null; wrSetLevel(3)")
    ok(ev("wr.typed") == 'до', 'phrase: 2 hint letters')
    ev("document.getElementById('setWrGiven').value='0'; extraSettingChanged('wrGiven')")
    ok(ev("wr.typed") == '' and ev("wr.word") == 'Доброе утро', 'setting 0 applies immediately to current phrase')
    ev("localStorage.setItem('sr.wr.given','1')")
    ev("openSettings()"); ok(ev("document.querySelector('.sg.open').dataset.g") == 'train', 'settings group for writing'); ev("closeSettings()")
    ev("history.back()"); pg.wait_for_timeout(300)
    ok(ev("screenName") == 'select', 'back from writing')
    ev("localStorage.setItem('app_lang','en')"); pg.reload(); pg.wait_for_timeout(500)
    ok(ev("document.getElementById('appTitle').innerText") == 'Words Again' and ev("document.getElementById('modeWrTitle').innerText") == '✍️ Writing', 'en names')
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
