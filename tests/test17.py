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
    for (W, H, zoom) in [(360, 640, 1), (277, 492, 1.3)]:
        ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1)
        ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
        ctx.add_init_script(MOCK)
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(400)
        ev = pg.evaluate
        ev("localStorage.setItem('app_lang','ru'); localStorage.setItem('sr.tour.offer','0')"); pg.reload(); pg.wait_for_timeout(600)
        tag = f'{W}x{H}'
        def realclick(sel):
            ev(f"document.querySelector({sel!r}).scrollIntoView({{block:'center'}})"); pg.wait_for_timeout(100)
            bb = pg.locator(sel).first.bounding_box()
            if not bb: print("NO BOX", sel); return
            ev("window.__clk=[]; document.addEventListener('click', e=>window.__clk.push(e.target), {capture:true, once:true})")
            pg.mouse.click(bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2); pg.wait_for_timeout(250)
        def typein(sel, txt):
            ev(f"document.querySelector({sel!r}).scrollIntoView({{block:'center'}})")
            pg.focus(sel); pg.keyboard.press('Control+A'); pg.keyboard.type(txt)
        # таймер: поле → соседние элементы
        ev("openSettings(); if (document.querySelector('.sg[data-g=\"main\"] .sg-h').getAttribute('aria-expanded')!=='true') settToggle('main')"); pg.wait_for_timeout(300)
        for nxt, check in [('#restMinutes', "document.activeElement && document.activeElement.id==='restMinutes'"),
                           ('label[for="resumeOnStart"]', "document.getElementById('resumeOnStart').checked"),
                           ('#settingsClose', "document.getElementById('settingsOverlay').classList.contains('hidden') || getComputedStyle(document.getElementById('settingsOverlay')).display==='none'")]:
            ev("document.getElementById('resumeOnStart').checked=false")
            if not ev("!document.getElementById('settingsOverlay').classList.contains('hidden')"): ev("openSettings(); if (document.querySelector('.sg[data-g=\"main\"] .sg-h').getAttribute('aria-expanded')!=='true') settToggle('main')"); pg.wait_for_timeout(300)
            typein('#playMinutes', '7')
            realclick(nxt)
            ok(ev(check), f'{tag}: after editing play minutes, first tap on {nxt} works')
        ev("if (!document.getElementById('settingsOverlay').classList.contains('hidden')) closeSettings()")
        ev("openSettings(); if (document.querySelector('.sg[data-g=\"main\"] .sg-h').getAttribute('aria-expanded')!=='true') settToggle('main')"); pg.wait_for_timeout(300)
        typein('#restMinutes', '9'); realclick('.sg[data-g="train"] .sg-h')
        ok(ev("document.querySelector('.sg[data-g=\"train\"] .sg-h').getAttribute('aria-expanded')") == 'true', f'{tag}: after editing rest minutes, group header opens on first tap')
        ev("closeSettings()")
        # мои фразы: поле → «Добавить»
        ev("goHome(); startMode('phr')"); pg.wait_for_timeout(300)
        n0 = ev("phr.list.length"); typein('#phrInput', 'проверка касания'); realclick('.ph-add')
        ok(ev("phr.list.length") == n0 + 1, f'{tag}: phrase added on first tap')
        # перечисления: своё — поле → «Сохранить»
        ev("goHome(); startMode('ser'); ser.form=true; serRender()"); pg.wait_for_timeout(300)
        typein('#serName', 'Тест'); typein('#serItems', 'раз, два, три'); realclick('#serScreen .abc-row .abc-say')
        ok(ev("ser.my.some(s=>s.name==='Тест')"), f'{tag}: own series saved on first tap')
        # словарь: поле → «Сохранить»
        ev("goHome(); openDict()"); pg.wait_for_timeout(300)
        typein('#dictWordInput', 'кошечка')
        sv = ev("(()=>{const b=[...document.querySelectorAll('#dictOverlay button, #dictPanel button')].find(x=>/Сохранить|Добавить/.test(x.textContent)&&x.offsetParent); if(b){b.id=b.id||'__dsave'; return '#'+b.id} return null})()")
        if sv:
            n1 = ev("JSON.stringify(localStorage).length"); realclick(sv)
            ok(ev("window.__clk.length") >= 1, f'{tag}: dictionary save button got the first tap')
        ok(not errs, f'{tag}: no page errors ' + str(errs))
        ctx.close()
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
