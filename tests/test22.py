# «👆 Управление и нажатия»: вибрация, звук нажатия, не гасить экран (v92)
import threading, http.server, functools, json, sys
from playwright.sync_api import sync_playwright

import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sr_site import make_root
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
speechSynthesis.speak = u => { window.__spoken.push(u.text); setTimeout(()=>{u.onstart&&u.onstart(); u.onend&&u.onend();},5); };
window.__vib = []; navigator.vibrate = p => { window.__vib.push(p); return true; };
window.__wl = { req: 0, rel: 0, active: 0 };
Object.defineProperty(navigator, "wakeLock", {get(){ return { request: () => { __wl.req++; __wl.active++; const l = { _h: [], addEventListener(e, f){ this._h.push(f); }, release(){ __wl.rel++; __wl.active--; this._h.forEach(f=>f()); return Promise.resolve(); } }; return Promise.resolve(l); } }; }});
window.__osc = []; const _AC = window.AudioContext;
window.AudioContext = class extends _AC { createOscillator(){ const o = super.createOscillator(); window.__osc.push(o); return o; } };
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
    ev("localStorage.clear(); localStorage.setItem('app_lang','ru'); localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('app_timer_enabled','false')")
    pg.reload(); pg.wait_for_timeout(500)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    # ===== группа настроек
    groups = ev("[...document.querySelectorAll('#settingsPanel .sg')].map(g=>g.dataset.g)")
    ok(groups[:2] == ['main', 'touch'], 'group right after «Основные»: ' + str(groups[:3]))
    ev("openSettings(); settShow('touch')"); pg.wait_for_timeout(150)
    ok(ev("document.getElementById('sgt_touch').textContent") == '👆 Управление и нажатия', 'group title')
    ok(ev("document.getElementById('labelTapVib').textContent") == 'Вибрация при нажатии' and ev("document.getElementById('labelKeepAwake').textContent") == 'Не гасить экран, пока приложение открыто', 'labels like in Govorim')
    ok(ev("[...document.getElementById('tapSound').options].map(o=>o.textContent)") == ['выключен', 'тихий', 'громкий'], 'sound levels')
    ok(ev("tapSet()") == {'vib': False, 'sound': 0, 'awake': False}, 'all off by default')
    # по умолчанию — ни вибрации, ни звука
    ev("closeSettings(); __vib.length=0; __osc.length=0; startMode('full')"); pg.wait_for_timeout(300)
    pg.click('#modeHomeBtn') if ev("!!document.getElementById('modeHomeBtn')") else ev("goHome()")
    pg.wait_for_timeout(200)
    pg.click('.mode-card[data-m="num"]'); pg.wait_for_timeout(300)
    ok(ev("__vib.length") == 0 and ev("__osc.length") == 0, 'off: no vibration, no sound on taps')
    ev("goHome()")
    # ===== вибрация
    ev("openSettings(); settShow('touch')"); pg.wait_for_timeout(100)
    pg.click('#tapVib'); pg.wait_for_timeout(100)
    ok(ev("localStorage.getItem('sr.tap.vib')") == '1', 'vibration saved')
    ev("closeSettings(); __vib.length=0"); pg.wait_for_timeout(100)
    pg.click('.mode-card[data-m="num"]'); pg.wait_for_timeout(300)
    ok(ev("__vib") == [20], 'tap on a mode card vibrates 20 ms: ' + str(ev("__vib")))
    ev("__vib.length=0"); pg.click('#numScreen .nm-listen'); pg.wait_for_timeout(150)
    ok(ev("__vib") == [20], 'tap on a button vibrates')
    ev("__vib.length=0"); pg.mouse.click(5, 400); pg.wait_for_timeout(150)
    ok(ev("__vib") == [], 'tap on empty space: nothing')
    ev("goHome()")
    # ===== звук
    ev("openSettings(); settShow('touch'); __osc.length=0"); pg.wait_for_timeout(100)
    pg.select_option('#tapSound', '2'); pg.wait_for_timeout(200)
    ok(ev("localStorage.getItem('sr.tap.sound')") == '2' and ev("__osc.length") == 1, 'loud saved, sample click played on choosing')
    ev("closeSettings(); __osc.length=0"); pg.wait_for_timeout(100)
    pg.click('.mode-card[data-m="num"]'); pg.wait_for_timeout(300)
    ok(ev("__osc.length") == 1, 'click sound on tap')
    ok(ev("__osc[0].frequency.value") <= 700, 'low click (≤ 700 Hz) for reduced hearing')
    # во время записи щелчка нет
    ev("__srQueue.push('hold'); nmMic()"); pg.wait_for_timeout(200)
    ok(ev("micBusy()") is True, 'microphone on')
    ev("__osc.length=0; __vib.length=0"); pg.click('#numScreen .nm-listen', force=True); pg.wait_for_timeout(150)
    ok(ev("__osc.length") == 0 and ev("__vib") == [20], 'microphone on: vibration yes, no click')
    ev("stopModeRec()"); pg.wait_for_timeout(200)
    ev("__osc.length=0"); pg.click('#numScreen .nm-listen'); pg.wait_for_timeout(150)
    ok(ev("__osc.length") == 1, 'microphone off: click again')
    # полный тренажёр: во время записи щелчка нет
    ev("goHome(); startMode('full')"); pg.wait_for_timeout(300)
    ev("__srQueue.push('hold'); toggleRecording()"); pg.wait_for_timeout(200)
    ev("__osc.length=0"); pg.click('#recordBtn', force=True); pg.wait_for_timeout(150)
    ok(ev("__osc.length") == 0, 'full trainer: no click while recording')
    ev("try{recognition.abort()}catch(e){}"); pg.wait_for_timeout(100)
    # тихий
    ev("tapSetChange('sound','1'); __osc.length=0"); pg.click('#fullOptBtn') if ev("!!document.getElementById('fullOptBtn')") else None
    pg.wait_for_timeout(150)
    ok(ev("__osc.length") >= 1, 'quiet level plays too')
    ev("tapSetChange('sound','0'); tapSetChange('vib','0'); __osc.length=0; __vib.length=0")
    pg.click('#fullOptBtn'); pg.wait_for_timeout(150)
    ok(ev("__osc.length") == 0 and ev("__vib.length") == 0, 'switched off again: nothing')
    # ===== не гасить экран
    ev("goHome()"); pg.wait_for_timeout(200)
    ok(ev("__wl.active") == 0, 'wake lock not held by default on the start screen')
    ev("openSettings(); settShow('touch')"); pg.wait_for_timeout(100)
    pg.click('#keepAwake'); pg.wait_for_timeout(200)
    ok(ev("localStorage.getItem('sr.awake')") == '1' and ev("__wl.active") == 1, 'keep awake: wake lock held at once')
    ev("closeSettings()"); ev("startMode('abc')"); pg.wait_for_timeout(200)
    ok(ev("__wl.active") == 1, 'held in a mode without hints (ABC)')
    ev("goHome()"); pg.wait_for_timeout(200)
    ok(ev("__wl.active") == 1, 'held on the start screen')
    ev("Object.defineProperty(document,'hidden',{value:true,configurable:true}); document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(200)
    ok(ev("__wl.active") == 0, 'released when minimised')
    ev("Object.defineProperty(document,'hidden',{value:false,configurable:true}); document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(200)
    ok(ev("__wl.active") == 1, 'taken again when back')
    pg.reload(); pg.wait_for_timeout(500)
    ok(ev("__wl.active") == 1 and ev("document.getElementById('keepAwake').checked") is True, 'after reload: still on')
    ev("openSettings(); settShow('touch')"); pg.wait_for_timeout(100)
    pg.click('#keepAwake'); pg.wait_for_timeout(200)
    ok(ev("__wl.active") == 0, 'switched off: released')
    # подсказка при бездействии по-прежнему держит экран в своих режимах
    ev("localStorage.setItem('sr.hint.sec','20'); closeSettings(); startMode('num')"); pg.wait_for_timeout(300)
    ok(ev("__wl.active") == 1, 'idle hint still keeps the screen on in its modes')
    ev("goHome()"); pg.wait_for_timeout(200)
    ok(ev("__wl.active") == 0, 'and releases on the start screen')
    ev("localStorage.removeItem('sr.hint.sec')")
    # ===== копия данных включает настройки
    ev("tapSetChange('vib','1'); tapSetChange('sound','2'); tapSetChange('awake','1')")
    ok(all(ev(f"bkKeys().includes('{k}')") for k in ('sr.tap.vib', 'sr.tap.sound', 'sr.awake')), 'settings are in the data backup')
    ev("tapSetChange('vib','0'); tapSetChange('sound','0'); tapSetChange('awake','0')")
    # ===== справка, языки, вёрстка
    ok(ev("HELP_KEYS.indexOf('s_touch')") == ev("HELP_KEYS.indexOf('s_idlehint')") + 1, 'help key placed')
    for L, title in (('ru', 'Управление и нажатия'), ('uk', 'Керування й натискання'), ('en', 'Control and taps')):
        ev(f"localStorage.setItem('app_lang','{L}')"); pg.reload(); pg.wait_for_timeout(400)
        ok(ev("helpParse(currentLang).items.length") == 48, f'{L}: 48 help items')
        ok(title in ev("document.getElementById('sgt_touch').textContent"), f'{L}: group title')
        t = ev("(()=>{ const h = helpParse(currentLang); const i = HELP_KEYS.indexOf('s_touch'); return JSON.stringify(h.items[i]); })()")
        ok(title.split(' ')[0] in t or title in t, f'{L}: help item for the group: ' + t[:80])
    for W in (360, 313, 277, 240):
        pg.set_viewport_size({'width': W, 'height': 600})
        for L in ('ru', 'uk', 'en'):
            ev(f"localStorage.setItem('app_lang','{L}')"); pg.reload(); pg.wait_for_timeout(300)
            ev("openSettings(); settShow('touch')"); pg.wait_for_timeout(150)
            g = ev("""(()=>{ const vw=document.documentElement.clientWidth, out=[];
                 document.querySelectorAll('[data-g="touch"] *').forEach(e=>{ if(!e.offsetParent) return; const r=e.getBoundingClientRect(); if(r.right>vw+1||r.left<-1) out.push(e.id||e.className); });
                 if (document.documentElement.scrollWidth > vw+1) out.push('HSCROLL');
                 const s=document.getElementById('tapSound').getBoundingClientRect(); if (s.height<40) out.push('select small');
                 return out; })()""")
            ok(not g, f'{L} {W}: group layout ' + str(g))
    ok(not errs, 'no page errors: ' + str(errs))
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
sys.exit(1 if fails else 0)
