# Проверка браузера при первом открытии, справка «🌐 Браузеры», строка в «О приложении» (v93)
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

BASE = r"""
try { if (localStorage.getItem("sr.tour.offer") === null) localStorage.setItem("sr.tour.offer", "0"); } catch (e) {}
Object.defineProperty(navigator, 'serviceWorker', {get(){return {register:()=>Promise.reject(new Error('blocked')), addEventListener(){}}}});
speechSynthesis.speak = u => { setTimeout(()=>{u.onstart&&u.onstart(); u.onend&&u.onend();},5); };
"""
WITH_SR = "class FakeSR { start(){} stop(){} abort(){} } window.SpeechRecognition = FakeSR; window.webkitSpeechRecognition = FakeSR;"
NO_SR = "try { delete window.SpeechRecognition; } catch(e) {} try { delete window.webkitSpeechRecognition; } catch(e) {} window.SpeechRecognition = undefined; window.webkitSpeechRecognition = undefined;"
NO_TTS = "try { delete Window.prototype.speechSynthesis; delete window.speechSynthesis; } catch(e) {} try { delete window.SpeechSynthesisUtterance; } catch(e) {}"
NO_REC = "window.MediaRecorder = undefined;"
def VOICES(langs):
    return "speechSynthesis.getVoices = () => %s.map(l => ({lang: l, name: 'v-' + l}));" % json.dumps(langs)
ANDROID_FF = 'Mozilla/5.0 (Android 14; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0'
SAMSUNG = 'Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/27.0 Chrome/125.0.0.0 Mobile Safari/537.36'
CHROME_A = 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
FB = CHROME_A.replace('Mobile Safari/537.36', 'Mobile Safari/537.36 [FBAN/EMA;FBLC/ru_RU;FBAV/450.0.0.0;]')

fails = []; n = 0
def ok(cond, name):
    global n; n += 1
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    def page(scripts, ua=None, lang='ru', w=360, h=740, theme=None, clear=True):
        kw = {'viewport': {'width': w, 'height': h}}
        if ua: kw['user_agent'] = ua
        c = b.new_context(**kw)
        c.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
        c.add_init_script(BASE)
        for s_ in scripts: c.add_init_script(s_)
        pg = c.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(200)
        pg.evaluate(f"localStorage.clear(); localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0')" + (f"; localStorage.setItem('app_theme','{theme}')" if theme else ''))
        pg.reload(); pg.wait_for_timeout(1900)
        return c, pg, errs
    shown = lambda pg: pg.evaluate("overlayOpen('brwOverlay')")
    items = lambda pg: pg.evaluate("[...document.querySelectorAll('#brwList li')].map(l=>l.textContent)")

    # ===== всё есть (Chrome) — окна нет
    c, pg, errs = page([WITH_SR, VOICES(['ru-RU', 'uk-UA', 'en-US'])], ua=CHROME_A)
    ok(not shown(pg), 'Chrome with everything: no window')
    ok(pg.evaluate("brwSummary()") == 'Этот браузер: распознавание речи ✔, озвучка ✔, запись ✔.', 'summary: ' + pg.evaluate("brwSummary()"))
    pg.evaluate("openSettings(); settShow('about')"); pg.wait_for_timeout(150)
    ok('распознавание речи ✔' in pg.evaluate("document.getElementById('aboutBrw').textContent"), 'about shows this browser')
    facts = pg.evaluate("document.getElementById('aboutBox').textContent")
    ok('нигде не сохраняется' in facts and 'входит в копию данных' in facts, 'about: recordings of phrases are mentioned correctly')
    ok(not errs, 'no errors (chrome)'); c.close()

    # ===== нет распознавания (Firefox Android)
    c, pg, errs = page([NO_SR, VOICES(['ru-RU', 'uk-UA'])], ua=ANDROID_FF)
    ok(shown(pg), 'no recognition: window shown at first opening')
    it = items(pg)
    ok(len(it) == 1 and it[0].startswith('🎤 Распознавание речи не работает'), 'one item about recognition: ' + str(it))
    ok(pg.evaluate("document.getElementById('brwTitle').textContent") == 'В этом браузере часть функций не работает', 'title')
    ok('Chrome' in pg.evaluate("document.getElementById('brwNote').textContent") and 'копию данных' in pg.evaluate("document.getElementById('brwNote').textContent"), 'note: Chrome and data backup')
    ok(pg.evaluate("getComputedStyle(document.getElementById('brwChrome')).display") != 'none', 'Android: «Open in Chrome» button')
    r = pg.evaluate("(()=>{const a=document.getElementById('brwOk').getBoundingClientRect(); return [a.top>=0, a.bottom<=innerHeight, a.height]})()")
    ok(r[0] and r[1] and r[2] >= 48, 'OK button visible and big: ' + str(r))
    pg.click('#brwOk'); pg.wait_for_timeout(200)
    ok(not shown(pg) and pg.evaluate("localStorage.getItem('sr.brw.seen')") == 'sr', 'closed and remembered')
    pg.reload(); pg.wait_for_timeout(1900)
    ok(not shown(pg), 'second opening: not shown again')
    ok(pg.evaluate("brwSummary()").startswith('Этот браузер: распознавание речи ✖'), 'summary shows no recognition')
    # системное «Назад» закрывает окно
    pg.evaluate("localStorage.removeItem('sr.brw.seen'); brwShow(false)"); pg.wait_for_timeout(100)
    ok(shown(pg), 'shown again after reset')
    pg.evaluate("appBack()"); pg.wait_for_timeout(100)
    ok(not shown(pg) and pg.evaluate("localStorage.getItem('sr.brw.seen')") == 'sr', 'Back closes the window and remembers')
    ok(not errs, 'no errors (firefox): ' + str(errs)); c.close()

    # ===== Samsung Internet — с ограничениями
    c, pg, errs = page([WITH_SR, VOICES(['ru-RU', 'uk-UA'])], ua=SAMSUNG)
    it = items(pg)
    ok(shown(pg) and len(it) == 1 and 'с ограничениями' in it[0], 'Samsung: recognition limited: ' + str(it))
    ok(pg.evaluate("getComputedStyle(document.getElementById('brwChrome')).display") != 'none', 'Samsung: «Open in Chrome» offered')
    c.close()

    # ===== нет голоса для языка (в Chrome) — только пункт про голос, без кнопки Chrome
    c, pg, errs = page([WITH_SR, VOICES(['en-US', 'de-DE'])], ua=CHROME_A, lang='uk')
    it = items(pg)
    ok(shown(pg) and len(it) == 1 and 'українська' in it[0], 'no voice for Ukrainian: ' + str(it))
    ok(pg.evaluate("getComputedStyle(document.getElementById('brwChrome')).display") == 'none', 'voice only: no «Open in Chrome»')
    ok(pg.evaluate("document.getElementById('brwOk').textContent") == 'Зрозуміло', 'uk button')
    pg.click('#brwOk'); pg.wait_for_timeout(100)
    # смена языка на тот, для которого голос есть — ничего нового
    ok(pg.evaluate("localStorage.getItem('sr.brw.seen')") == 'voice-uk', 'signature per language')
    c.close()

    # ===== список голосов пуст (ещё не загружен) — про голос не говорим
    c, pg, errs = page([WITH_SR, VOICES([])], ua=CHROME_A)
    ok(not shown(pg), 'empty voice list: unknown, nothing shown')
    c.close()

    # ===== нет озвучки и записи
    c, pg, errs = page([NO_SR, NO_TTS, NO_REC], ua=ANDROID_FF)
    it = items(pg)
    ok(shown(pg) and len(it) == 3 and it[1].startswith('🔊 Озвучка не работает') and it[2].startswith('⏺ Запись'), 'three items: ' + str([x[:20] for x in it]))
    ok(not errs, 'no errors without speech synthesis: ' + str(errs))
    # набор изменился (другой браузер / обновление) — показать снова
    pg.click('#brwOk'); pg.wait_for_timeout(100)
    ok(pg.evaluate("localStorage.getItem('sr.brw.seen')") == 'rec,sr,tts', 'signature of all issues')
    pg.evaluate("localStorage.setItem('sr.brw.seen','sr')"); pg.reload(); pg.wait_for_timeout(1900)
    ok(shown(pg), 'different set of issues: shown again')
    c.close()

    # ===== встроенный браузер Facebook — своя жёлтая плашка, окна нет
    c, pg, errs = page([NO_SR], ua=FB)
    ok(not shown(pg) and pg.evaluate("!!document.getElementById('iabBar')"), 'in-app browser: yellow bar instead of the window')
    c.close()

    # ===== окно не мешает: обучение ждёт, подсказка не тикает
    c, pg, errs = page([NO_SR], ua=ANDROID_FF)
    pg.evaluate("localStorage.setItem('sr.tour.offer','1')")
    pg.evaluate("startMode('listen')"); pg.wait_for_timeout(800)
    ok(shown(pg) and not pg.evaluate("TOUR.offer"), 'tutorial offer does not cover the window')
    pg.click('#brwOk'); pg.wait_for_timeout(200)
    c.close()

    # ===== справка
    c, pg, errs = page([WITH_SR, VOICES(['ru-RU', 'uk-UA', 'en-US'])], ua=CHROME_A)
    for L, title in (('ru', 'Браузеры'), ('uk', 'Браузери'), ('en', 'Browsers')):
        hp = pg.evaluate(f"(()=>{{ const h = helpParse('{L}'); const i = HELP_KEYS.indexOf('browser'); return [h.items.length, HELP_KEYS.length, h.items[i] ? h.items[i].title : '', h.items[i] ? h.items[i].html : ''] }})()")
        ok(hp[0] == hp[1] == 48, f'{L}: 48 help items')
        ok(title in hp[2] and 'Chrome' in hp[3] and 'Samsung' in hp[3] and 'Firefox' in hp[3], f'{L}: browser item: ' + hp[2])
    pg.evaluate("openHelp()"); pg.wait_for_timeout(200)
    ok('Браузеры' in pg.evaluate("document.getElementById('helpOverlay').textContent"), 'item in the help contents')
    c.close()

    # ===== вёрстка окна: 360/313/277/240, ru/uk/en, тёмная тема
    for L in ('ru', 'uk', 'en'):
        for W, Hh in ((360, 640), (313, 557), (277, 492), (240, 427)):
            c, pg, errs = page([NO_SR, NO_REC], ua=ANDROID_FF, lang=L, w=W, h=Hh, theme='dark')
            g = pg.evaluate("""(()=>{ const vw=document.documentElement.clientWidth, out=[];
                document.querySelectorAll('#brwOverlay *').forEach(e=>{ if(!e.offsetParent) return; const r=e.getBoundingClientRect(); if(r.right>vw+1||r.left<-1) out.push('OUT '+(e.id||e.className));
                  if(e.tagName==='BUTTON' && e.scrollWidth>e.clientWidth+2) out.push('TEXT '+e.id); });
                const okb=document.getElementById('brwOk'); okb.scrollIntoView({block:'nearest'}); const r=okb.getBoundingClientRect(); if(r.bottom>innerHeight+1) out.push('OK not reachable');
                const p=document.querySelector('.brw-panel'); const bg=getComputedStyle(p).backgroundColor.match(/[\\d.]+/g).map(Number);
                if ((0.2126*bg[0]+0.7152*bg[1]+0.0722*bg[2]) > 90) out.push('light panel in dark theme '+bg);
                return out; })()""")
            ok(shown(pg) and not g, f'{L} {W}x{Hh}: window layout ' + str(g))
            c.close()
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
sys.exit(1 if fails else 0)
