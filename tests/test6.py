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

import json as _j, os
fails = []; n = 0
def ok(cond, name):
    global n; n += 1
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond: fails.append(name)
FB_AND = 'Mozilla/5.0 (Linux; Android 13; Pixel 6 Build/TQ3A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/440.0.0.0;]'
FB_IOS = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/440.0]'
TMP = shots_dir() + os.sep
with sync_playwright() as p:
    b = p.chromium.launch()
    def mk(ua=None, w=360, h=740):
        kw = {'viewport': {'width': w, 'height': h}, 'accept_downloads': True}
        if ua: kw['user_agent'] = ua
        ctx = b.new_context(**kw)
        ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
        ctx.add_init_script(MOCK)
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(500)
        return ctx, pg, errs
    # ===== 1. резервная копия
    ctx, pg, errs = mk(); ev = pg.evaluate
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("""localStorage.setItem('sr.phr.ru', JSON.stringify([{t:'Дайте мне воды'}]));
          localStorage.setItem('sr.wr.given','3'); localStorage.setItem('app_stats_v1','{"ru":{"words":{}}}');
          localStorage.setItem('aac.settings','{"x":1}'); localStorage.setItem('app_lex_ru','BIG'); localStorage.setItem('sr.secret.k','zzz');""")
    ev("openSettings(); settShow('data')"); pg.wait_for_timeout(200)
    ok(ev("document.getElementById('sgt_data').textContent").startswith('💾 Данные'), 'data group title ru')
    ok(ev("document.getElementById('bkSaveBtn').textContent") == '💾 Сохранить копию данных', 'save label')
    ok(ev("document.getElementById('bkSaveBtn').getBoundingClientRect().height") >= 44, 'save button tall enough')
    with pg.expect_download() as dl: ev("document.getElementById('bkSaveBtn').click()")
    d = dl.value; fn = d.suggested_filename; path = TMP + fn; d.save_as(path)
    ok(fn.startswith('znovu-slova-backup-') and fn.endswith('.json'), 'file name ' + fn)
    obj = _j.load(open(path, encoding='utf-8'))
    ok(obj['app'] == 'SpeechRehab' and obj['version'] == 85 and 'date' in obj, 'header fields')
    ks = obj['data']
    ok('sr.phr.ru' in ks and ks['sr.wr.given'] == '3' and 'app_lang' in ks and 'app_stats_v1' in ks, 'own keys saved')
    ok('aac.settings' not in ks and 'app_lex_ru' not in ks and 'sr.secret.k' not in ks, 'foreign/lex/secret skipped')
    ok('Загрузки' in ev("document.getElementById('bkStatus').textContent"), 'saved status')
    # чужой файл
    gov = TMP + 'gov.json'; _j.dump({'app': 'Govorim', 'data': {'aac.x': '1'}}, open(gov, 'w'))
    dialogs = []; pg.on('dialog', lambda dg: (dialogs.append(dg.message), dg.accept()))
    pg.set_input_files('#bkFile', gov); pg.wait_for_timeout(300)
    ok(not dialogs and 'не является' in ev("document.getElementById('bkStatus').textContent"), 'Govorim file rejected')
    bad = TMP + 'bad.json'; open(bad, 'w').write('{oops')
    pg.set_input_files('#bkFile', bad); pg.wait_for_timeout(300)
    ok(not dialogs and 'не является' in ev("document.getElementById('bkStatus').textContent"), 'broken file rejected')
    # очистить и загрузить
    ev("""Object.keys(localStorage).filter(k=>k.startsWith('sr.')||k.startsWith('app_')).forEach(k=>localStorage.removeItem(k));
          localStorage.setItem('app_lang','ru'); localStorage.setItem('sr.junk','1')""")
    ok(ev("localStorage.getItem('sr.phr.ru')") is None, 'cleared')
    with pg.expect_navigation(timeout=5000):
        pg.set_input_files('#bkFile', path)
    pg.wait_for_timeout(600)
    ok(len(dialogs) == 1 and 'Заменить' in dialogs[0], 'confirm asked')
    ok(ev("localStorage.getItem('sr.phr.ru')") is not None and ev("localStorage.getItem('sr.wr.given')") == '3', 'data restored')
    ok(ev("localStorage.getItem('sr.junk')") is None, 'old own keys replaced')
    ok(ev("localStorage.getItem('aac.settings')") == '{"x":1}', 'Govorim keys untouched')
    ok(ev("wrGivenN()") == 3, 'restored setting active')
    # отказ в подтверждении ничего не меняет
    pg.remove_listener('dialog', pg.listeners('dialog')[0]) if hasattr(pg, 'listeners') else None
    ctx2 = ctx
    ok(ev("document.getElementById('iabBar')") is None, 'no banner in normal browser')
    ok(not errs, 'no page errors (backup): ' + '; '.join(errs))
    ctx.close()
    # отказ
    ctx, pg, errs = mk(); ev = pg.evaluate
    ev("localStorage.setItem('app_lang','uk'); localStorage.setItem('sr.wr.given','0')"); pg.reload(); pg.wait_for_timeout(500)
    pg.on('dialog', lambda dg: dg.dismiss())
    ev("openSettings(); settShow('data')")
    pg.set_input_files('#bkFile', path); pg.wait_for_timeout(800)
    ok(ev("localStorage.getItem('sr.wr.given')") == '0', 'dismiss keeps data')
    ok(ev("document.getElementById('bkLoadBtn').textContent") == '📂 Завантажити копію даних', 'uk label')
    ctx.close()
    # ===== 2. плашка
    for (w, h) in [(360, 740), (313, 643), (277, 569)]:
        for lang in ['ru', 'uk', 'en']:
            ctx, pg, errs = mk(FB_AND, w, h); ev = pg.evaluate
            ev(f"localStorage.setItem('app_lang','{lang}')"); pg.reload(); pg.wait_for_timeout(500)
            tag = f'{lang} {w}'
            ok(ev("document.body.firstElementChild && document.body.firstElementChild.id") == 'iabBar', 'banner first in body ' + tag)
            r = ev("""(()=>{const b=document.getElementById('iabBar'), hd=document.querySelector('.app-header');
              const bb=b.getBoundingClientRect(), hb=hd.getBoundingClientRect();
              const over=[...b.querySelectorAll('*')].filter(e=>e.scrollWidth>e.clientWidth+1||e.getBoundingClientRect().right>innerWidth+1).length;
              const btns=[...b.querySelectorAll('button')].map(x=>x.getBoundingClientRect().height);
              return {bh:bb.height, ov:over, hdTop:hb.top, bBot:bb.bottom, docW:document.documentElement.scrollWidth, minB:Math.min(...btns), n:btns.length}})()""")
            ok(r['ov'] == 0 and r['docW'] <= w and r['minB'] >= 44 and r['n'] == 3, f'banner fits {tag}: {r}')
            ok(r['hdTop'] >= r['bBot'] - 1 and r['bh'] < h * 0.4, f'header below, room left {tag}')
            if w == 360 and lang == 'ru':
                ev("toggleLanguage()"); pg.wait_for_timeout(200)  # ru -> en
                ok('Opened inside' in ev("document.getElementById('iabBar').innerText"), 'banner rerenders on language change')
                ok('intent://' not in ev("location.href"), 'not navigated')
                ev("document.querySelector('.iab-x').click()"); pg.wait_for_timeout(100)
                ok(ev("document.getElementById('iabBar')") is None, 'close hides')
                pg.reload(); pg.wait_for_timeout(500)
                ok(ev("document.getElementById('iabBar')") is None, 'hidden for the session')
            ok(not errs, 'no errors ' + tag)
            ctx.close()
    ctx, pg, errs = mk(FB_IOS); ev = pg.evaluate
    ev("localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ok(ev("!document.querySelector('.iab-chrome') && !!document.querySelector('.iab-copy')"), 'iOS: no Chrome button')
    ok('Відкрити в браузері' in ev("document.querySelector('.iab-hint').textContent"), 'iOS hint')
    ctx.close()
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
