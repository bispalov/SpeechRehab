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


REC = r"""
window.__gum = 'ok'; window.__tracksStopped = 0; window.__recStarted = 0; window.__played = [];
try {
  if (!navigator.mediaDevices) Object.defineProperty(navigator, 'mediaDevices', { value: {}, configurable: true });
  navigator.mediaDevices.getUserMedia = async () => {
    if (window.__gum === 'deny') { const e = new Error('denied'); e.name = 'NotAllowedError'; throw e; }
    return { getTracks: () => [{ stop() { window.__tracksStopped++; } }] };
  };
} catch (e) {}
window.MediaRecorder = class {
  constructor(s) { this.stream = s; this.state = 'inactive'; this.mimeType = 'audio/webm'; window.__mr = this; }
  start() { this.state = 'recording'; window.__recStarted++; }
  stop() { if (this.state === 'inactive') return; this.state = 'inactive'; if (this.ondataavailable) this.ondataavailable({ data: new Blob([new Uint8Array(4000)]) }); setTimeout(() => this.onstop && this.onstop(), 10); }
};
window.Audio = function (src) { return { src, play() { window.__played.push(src); setTimeout(() => { this.onended && this.onended(); }, 200); return Promise.resolve(); }, pause() {} }; };
"""


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 360, 'height': 740}, permissions=['clipboard-read', 'clipboard-write'])
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    ctx.add_init_script(MOCK); ctx.add_init_script(REC)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(400)
    ev = pg.evaluate
    ev("localStorage.clear(); localStorage.setItem('app_lang','ru'); localStorage.setItem('sr.tour.offer','0')"); pg.reload(); pg.wait_for_timeout(500)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    LOG = "JSON.parse(localStorage.getItem('sr.misslog')||'[]')"
    last = lambda: ev(LOG + ".slice(-1)[0]")
    # ===== 🧩
    ev("startMode('full')"); pg.wait_for_timeout(300)
    ev("targetWordClean='сто'; targetWordSyllables='сто'; __srQueue.push({alts:['Стоп','столб']}); toggleRecording()"); pg.wait_for_timeout(400)
    e = last()
    ok(e and e['m'] == 'full' and e['w'] == 'сто' and e['a'] == ['стоп', 'столб'] and e['n'][0] == 'стоп' and e['err'] == '' and e['fix'] == 0, 'full: rejected answer logged with all alternatives ' + str(e))
    n0 = len(ev(LOG))
    ev("__srQueue.push({alts:['100']}); toggleRecording()"); pg.wait_for_timeout(400)
    ok(len(ev(LOG)) == n0, 'accepted "100" not logged')
    ev("targetWordClean='сто'; __srQueue.push({alts:['стоп']}); toggleRecording()"); pg.wait_for_timeout(400)
    ok(ev("!!document.querySelector('#speechResultBox .full-countok')"), 'full trainer: "I said it correctly" button')
    ev("document.querySelector('#speechResultBox .full-countok').click()"); pg.wait_for_timeout(200)
    ok(last()['fix'] == 1 and ev("speechPassed") and 'correct' in ev("document.getElementById('speechResultBox').className"), 'full: count-ok marks the log entry and passes')
    ok(ev("((loadStats().ru.modes||{}).full||{}).words['сто'].ok") >= 1, 'full: counted as a fix in statistics')
    ev("targetWordClean='сто'; __srQueue.push({error:'no-speech'}); toggleRecording()"); pg.wait_for_timeout(400)
    ok(last()['err'] == 'no-speech' and last()['a'] == [], 'full: recognition error logged')
    # нормализация видна: цифры
    ev("targetWordClean='восемь'; targetWordSyllables='во-семь'; __srQueue.push({alts:['7']}); toggleRecording()"); pg.wait_for_timeout(400)
    ok(last()['a'] == ['7'] and last()['n'] == ['семь'] and last()['syl'] == 'во-семь', 'raw and normalized variants: ' + str(last()))
    # ===== 👂
    ev("goHome(); startMode('listen')"); pg.wait_for_timeout(300)
    w = ev("train.clean")
    ev("__srQueue.push({alts:['абв','где']}); trainMic()"); pg.wait_for_timeout(400)
    ok(last()['m'] == 'listen' and last()['w'] == w and last()['a'] == ['абв', 'где'], 'listen: logged')
    ev("trainCountOk()")
    ok(last()['fix'] == 1, 'listen: count-ok marks entry')
    ev("__srQueue.push({error:'network'}); trainMic()"); pg.wait_for_timeout(400)
    ok(last()['m'] == 'listen' and last()['err'] == 'network', 'listen: error logged')
    # ===== 📝
    ev("goHome(); startMode('quiz')"); pg.wait_for_timeout(300)
    ev("startQuizFromSetup()"); pg.wait_for_timeout(700)
    qw = ev("quiz.cur && quiz.cur.clean")
    ev("__srQueue.push({alts:['абракадабра']}); quizMic()"); pg.wait_for_timeout(500)
    ok(last()['m'] == 'quiz' and last()['w'] == qw, 'quiz: logged')
    ev("quiz.active=false")
    # ===== 📖
    ev("goHome(); startMode('read'); rd.list=[]; rdSave(); rdAdd('корова'); rdStartWord(0)"); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['карова']}); document.querySelector('#readScreen .rd-mic').click()"); pg.wait_for_timeout(400)
    ok(last()['m'] == 'read' and last()['w'] == 'корова' and last()['syl'] == 'ко-ро-ва', 'read: logged with syllables')
    ev("rdCountOk()")
    ok(last()['fix'] == 1, 'read: count-ok marks entry')
    # ===== 🗣
    ev("goHome(); startMode('phr'); phr.list=[{t:'мне нужна вода',n:0,k:0}]; phrSave(); phrRender()"); pg.wait_for_timeout(300)
    ev("phrEnter(0)"); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['мне нужна в ода']}); phrSay()"); pg.wait_for_timeout(500)
    ok(last()['m'] == 'phr' and last()['w'] == 'мне нужна вода', 'phrases: logged')
    btn = ev("(()=>{const b=[...document.querySelectorAll('#phrScreen button')].find(x=>/Я сказал/.test(x.textContent)); if(b){b.click(); return true} return false})()")
    pg.wait_for_timeout(200)
    ok(btn and last()['fix'] == 1, 'phrases: count-ok marks entry')
    # ===== 🔢 по одному слову и весь ряд
    ev("goHome(); startMode('ser'); serStart(serAll()[0].id)"); pg.wait_for_timeout(300)
    ev("ser.step = {i:0, marks:[], tries:[]}; serStepResult(['пятница'], null)"); pg.wait_for_timeout(200)
    first = ev("serTarget()[0]")
    ok(last()['m'] == 'ser' and last()['w'] == first and last()['a'] == ['пятница'], 'sequences word-by-word: logged')
    ev("serStepFix()")
    ok(last()['fix'] == 1, 'sequences: count-ok marks entry')
    ev("serNewTask(); ser.listening=true; ser.buf='понедельник среда'; ser.sess=''; serFinish()"); pg.wait_for_timeout(300)
    ok(last()['m'] == 'ser' and ', ' in last()['w'] and last()['a'] == ['понедельник среда'], 'sequences whole row: logged')
    ok(ev("(()=>{const b=[...document.querySelectorAll('#serScreen button')].find(x=>/Я сказал/.test(x.textContent)); if(b){b.click(); return true} return false})()"), 'sequences row: count-ok button')
    pg.wait_for_timeout(200)
    ok(last()['fix'] == 1, 'sequences row: count-ok marks entry')
    # ===== лимит 20, длина варианта
    ev("for (let i=0;i<30;i++) mlAdd('full','слово'+i,['x'.repeat(200)])")
    L = ev(LOG)
    ok(len(L) == 20 and L[-1]['w'] == 'слово29' and L[0]['w'] == 'слово10', 'only the last 20 kept')
    ok(len(L[-1]['a'][0]) == 80, 'variant cut to 80 chars')
    # ===== резервная копия
    ok('sr.misslog' in ev("Object.keys(localStorage).filter(bkOwnKey)"), 'log is in the backup')
    # ===== статистика
    ev("goHome(); localStorage.removeItem('sr.misslog'); mlAdd('full','сто',['стоп']); mlFix('full','сто'); mlAdd('read','корова',[],{err:'no-speech'}); openStats()"); pg.wait_for_timeout(200)
    ok(ev("!!document.querySelector('#statsPanel .ml-btn')") and not ev("!!document.querySelector('#statsPanel .ml-item')"), 'stats: log collapsed by default')
    ok('Непринятые ответы (2)' in ev("document.querySelector('#statsPanel .ml-btn').textContent"), 'stats: count in header')
    ev("document.querySelector('#statsPanel .ml-btn').click()"); pg.wait_for_timeout(150)
    items = ev("[...document.querySelectorAll('#statsPanel .ml-item')].map(e=>e.textContent)")
    ok(len(items) == 2 and 'корова' in items[0] and 'ошибка распознавания: no-speech' in items[0] and 'стоп' in items[1] and 'Я сказал(а) верно' in items[1], 'stats: entries newest first ' + str(items))
    ok(ev("document.querySelectorAll('#statsPanel .ml-item.fix').length") == 1, 'said-correctly entry highlighted')
    ev("statsTab='full'; renderStatsPanel()")
    ok(ev("!!document.querySelector('#statsPanel .ml-item')"), 'log stays open on other tabs')
    txt = ev("mlText()")
    ok(txt.startswith('SpeechRehab v85') and 'target: сто' in txt and 'heard:  стоп' in txt and 'SAID-CORRECTLY' in txt and 'error: no-speech' in txt, 'developer text: ' + txt[:200])
    ev("document.querySelector('#statsPanel .ml-copy').click()"); pg.wait_for_timeout(300)
    clip = ev("navigator.clipboard.readText()")
    ok(clip == txt and 'Скопировано' in ev("document.getElementById('statsPanel').textContent"), 'copied to clipboard')
    ev("document.querySelector('#statsPanel .ml-clear').click()"); pg.wait_for_timeout(150)
    ok(ev("localStorage.getItem('sr.misslog')") is None and 'Пока нет непринятых' in ev("document.getElementById('statsPanel').textContent"), 'log cleared')
    ok(ev("Object.keys(loadStats().ru.modes||{}).length") > 0, 'clearing the log keeps statistics')
    ev("closeStats()")
    # ===== справка
    ok(ev("['ru','uk','en'].every(l=>helpParse(l).keysOk)"), 'help keys still match')
    ok(ev("['ru','uk','en'].every(l=>/🔍/.test(helpParse(l).items[HELP_KEYS.indexOf('stats')].html) && /📊/.test(helpParse(l).items[HELP_KEYS.indexOf('stats')].title))"), 'stats help mentions the log in all languages')
    ok(not errs, 'no page errors: ' + str(errs))
    ctx.close()
    # ===== вёрстка блока: 360/313/277/240, ru/uk/en
    GEO = r"""(() => {
      const vw = document.documentElement.clientWidth, out = [];
      document.querySelectorAll('#statsPanel .ml-box *').forEach(e => {
        if (!e.offsetParent) return;
        const r = e.getBoundingClientRect();
        if (r.right > vw + 1) out.push('OUT ' + e.className + ' ' + Math.round(r.right));
        if (e.tagName === 'BUTTON' && e.scrollWidth > e.clientWidth + 2) out.push('TEXT ' + e.className);
        if (e.tagName === 'BUTTON' && r.height < 44) out.push('SMALL ' + e.className + ' ' + Math.round(r.height));
      });
      if (document.documentElement.scrollWidth > vw + 1) out.push('HSCROLL');
      return out;
    })()"""
    for lang in ['ru', 'uk', 'en']:
        for z in (1.0, 1.15, 1.3, 1.5):
            W, H = round(360 / z), round(640 / z)
            c2 = b.new_context(viewport={'width': W, 'height': H})
            c2.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
            c2.add_init_script(MOCK)
            p2 = c2.new_page(); p2.goto(URL); p2.wait_for_timeout(300)
            p2.evaluate(f"localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0')"); p2.reload(); p2.wait_for_timeout(400)
            p2.evaluate("mlAdd('ser','понедельник, вторник, среда, четверг, пятница, суббота, воскресенье',['понедельник вторник среда четверг пятница суббота воскресенье понедельник']); mlFix('ser','понедельник, вторник, среда, четверг, пятница, суббота, воскресенье'); mlAdd('full','достопримечательность',['достопримечательности','достопримечательностей','достопримечательность и'],{syl:'дос-топ-ри-ме-ча-тель-ность'}); mlAdd('quiz','сто',[],{err:'no-speech'}); openStats(); mlOpen=true; mlMsg=mlT().copyFail; mlShowText=true; renderStatsPanel()")
            p2.wait_for_timeout(200)
            g = p2.evaluate(GEO)
            ok(not g, f'{lang} {W}x{H}: log layout ' + str(g[:4]))
            c2.close()
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
