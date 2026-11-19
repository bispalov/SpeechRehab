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


    ST = "JSON.parse(localStorage.getItem('app_stats_v1')||'{}').ru"
    # старые данные без режимов
    ev("localStorage.setItem('app_stats_v1', JSON.stringify({ru:{words:{'кот':{ok:1,bad:2}},conf:{'кот>код':2}}}))")
    ev("openStats()")
    ok(ev("document.querySelectorAll('#statsPanel .stats-tabs button').length") == 7, '7 tabs')
    ok('кот' in ev("document.getElementById('statsPanel').innerText"), 'old data visible in All')
    ev("statsTab='full'; renderStatsPanel()")
    ok('версии 53' in ev("document.getElementById('statsPanel').innerText"), 'mode tab without data explains')
    ev("closeStats(); localStorage.removeItem('app_stats_v1'); ['ru','uk','en'].forEach(l=>localStorage.removeItem('sr.ser.st.'+l))")
    # полный тренажёр: выбор
    ev("startMode('full'); targetWordSyllables='дом'; targetWordClean='дом'; document.getElementById('gentleMode').checked=false; isAnswered=false")
    ev("checkAnswer('ком', document.querySelector('.option-btn'))")
    st = ev(ST)
    ok(st['modes']['full']['words']['дом']['bad'] == 1 and st['modes']['full']['conf'].get('дом>ком') == 1, 'full: choice error recorded in mode')
    ok(list(st['modes']['full']['days'].values())[0] == {'n': 1, 'k': 0}, 'full: day counted')
    # тренировка слуха: ошибка, затем «Я сказал(а) верно»
    ev("goHome(); startMode('listen'); trainReset('кот'); renderListenStep(1); __srQueue.push({alts:['код']}); trainMic()"); pg.wait_for_timeout(300)
    ev("trainCountOk()")
    st = ev(ST); B = st['modes']['listen']
    ok(B['words']['кот'] == {'ok': 1, 'bad': 0} and list(B['days'].values())[0] == {'n': 1, 'k': 1}, 'listen: self-confirm fixes, no extra try')
    # сборка из букв учитывается на итоговом шаге
    ev("renderListenStep(2); 'кто'.split('').forEach(ch=>{const i=train.tiles.findIndex(t=>!t.used&&t.ch===ch); trainPlace(i)}); renderListenStep(3); renderListenStep(3)")
    st = ev(ST); B = st['modes']['listen']
    ok(B['conf'].get('кот>кто') == 1 and list(B['days'].values())[0]['n'] == 2, 'listen: letter building recorded once')
    # тест на слух — только во «Все»
    ev("goHome(); startMode('quiz'); startQuiz(['дом']); __srQueue.push({alts:['дом']}); quizMic()"); pg.wait_for_timeout(300)
    st = ev(ST)
    ok('quiz' in st['modes'] and st['modes']['quiz']['words']['дом']['ok'] == 1, 'quiz recorded (All tab)')
    # письмо
    ev("quiz.active=false; goHome(); startMode('wr'); wrSetLevel(2); wr.word='ко-ро-ва'; wrNew(true); wr.typed='карова'; wrCheck()")
    st = ev(ST)
    ok(st['modes']['wr']['conf'].get('корова>карова') == 1, 'writing confusion recorded')
    # перечисления
    ev("goHome(); startMode('ser'); serStart('days'); ser.mode='whole'; ser.dir='fwd'; serNewTask(); ser.listening=true; ser.buf='понедельник среда'; serFinish()")
    ev("[...document.querySelectorAll('#serScreen button')].find(b=>b.textContent.includes('верно')).click()")
    sst = ev("JSON.parse(localStorage.getItem('sr.ser.st.ru'))")
    ok(sst['days:fwd'] == {'n': 1, 'k': 1, 'l': sst['days:fwd']['l']}, 'ser: self-confirm no extra try')
    st = ev(ST)
    ok(list(st['modes']['ser']['days'].values())[0] == {'n': 1, 'k': 1}, 'ser: day recorded')
    ev("goHome(); openStats(); statsTab='ser'; renderStatsPanel()")
    txt = ev("document.getElementById('statsPanel').innerText")
    ok('Дни недели' in txt and 'Вперёд' in txt and 'Сегодня' in txt, 'ser tab shows series and today')
    ev("statsTab='wr'; renderStatsPanel()")
    txt = ev("document.getElementById('statsPanel').innerText")
    ok('корова → карова' in txt and 'Сегодня: 1' in txt, 'writing tab: today and confusions')
    ev("statsTab='all'; renderStatsPanel()")
    txt = ev("document.getElementById('statsPanel').innerText")
    ok('Сегодня: 6' in txt or 'Сегодня: 7' in txt, 'All sums days: ' + txt.split('\n')[6][:60])
    # сброс только одного режима
    pg.on('dialog', lambda d: d.accept())
    ev("statsTab='wr'; renderStatsPanel()")
    ev("[...document.querySelectorAll('#statsPanel button')].find(b=>b.textContent.includes('Сбросить')).click()")
    st = ev(ST)
    ok('wr' not in st['modes'] and 'full' in st['modes'], 'reset one mode only')
    ev("statsTab='all'; renderStatsPanel(); resetStats()")
    ok(ev("localStorage.getItem('app_stats_v1')") is None and ev("localStorage.getItem('sr.ser.st.ru')") is None, 'reset all clears series too')
    ev("closeStats()")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
