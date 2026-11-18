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

    ev("goHome(); startMode('abc')"); pg.wait_for_timeout(400)
    ev("abcState.fn=true; abcRender(true)"); pg.wait_for_timeout(100)
    ok(ev("!!document.querySelector('.abc-fnw')"), 'abc: short words open')
    ev("document.querySelector('.abc-fnw').click()"); pg.wait_for_timeout(200)
    ok(ev("abcState.line.length")==1 and ev("abcState.fn") is False and not ev("!!document.querySelector('.abc-fnw')"), 'abc: collapsed after pick')
    ok(ev("document.querySelector('.abc-fnarr').textContent")=='▶', 'abc: arrow ▶')
    ev("goHome(); startMode('hear')"); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['хочу пить']}); document.getElementById('micGo').click()"); pg.wait_for_timeout(500)
    ev("document.querySelector('button.fn').click()"); pg.wait_for_timeout(200)
    n0 = ev('hearBuild.length') if False else None
    fnchips = ev("document.querySelector('button.fn').getAttribute('aria-expanded')")
    ok(fnchips=='true', 'hear: fn open')
    # кнопка короткого слова: первая .chip в строке после кнопки fn, не в .hbuild
    clicked = ev("""(()=>{const b=[...document.querySelector('button.fn').parentElement.nextElementSibling.querySelectorAll('.chip')].find(c=>c.textContent==='я'); if(!b) return false; b.click(); return true})()""")
    pg.wait_for_timeout(300)
    ok(clicked, 'hear: found я')
    ok(ev("document.querySelector('button.fn').getAttribute('aria-expanded')")=='false', 'hear: collapsed after pick')
    bt = ev("[...document.querySelectorAll('.hbuild .chip')].map(c=>c.textContent).join(' ')"); ok('я' in bt.split(' ') or 'я?' in bt, 'hear: word added: '+bt)
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
