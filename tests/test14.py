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
    pg.set_viewport_size({'width': 360, 'height': 740})
    BOX = "(()=>{const b=document.getElementById('tourBox'); return b && b.classList.contains('on') ? b.querySelector('.tour-text').textContent : ''})()"
    BTNS = "[...document.querySelectorAll('#tourBox button')].map(b=>b.textContent)"
    HOLE = "(()=>{const h=document.querySelector('.tour-hole'); return h && getComputedStyle(h).display!=='none' && document.getElementById('tourDim').classList.contains('on')})()"
    def click_box(label): ev(f"[...document.querySelectorAll('#tourBox button')].find(b=>b.textContent==={label!r}).click()"); pg.wait_for_timeout(250)
    def tap(sel):
        ev(f"document.querySelector({sel!r}).scrollIntoView({{block:'center'}})"); pg.wait_for_timeout(50)
        r = ev(f"(()=>{{const r=document.querySelector({sel!r}).getBoundingClientRect(); return [r.x+r.width/2, r.y+r.height/2]}})()")
        pg.mouse.click(r[0], r[1]); pg.wait_for_timeout(450)
    ev("localStorage.removeItem('sr.tour.seen'); localStorage.removeItem('sr.tour.offer'); document.getElementById('timerEnabled').checked=false; toggleTimerFeature(); document.getElementById('autoSpeak').checked=false")
    # предложение при первом входе
    ev("startMode('full')"); pg.wait_for_timeout(800)
    ok(ev(BOX) == 'Показать, как здесь заниматься?' and ev(BTNS) == ['▶ Да, показать', 'Не сейчас'], 'offer on first entry')
    ok(any('Показать, как здесь' in x for x in ev("__spoken")), 'offer spoken')
    ok(ev("timerCounts()") is False and ev("ihBlocked()") is True, 'timer and idle hint wait')
    # нажатие мимо не срабатывает
    ok(ev("isAnswered") is False, 'not answered')
    tap('#optionsContainer .option-btn')
    ok(ev("isAnswered") is False, 'tap outside the tutorial box is blocked')
    click_box('▶ Да, показать')
    ok(ev(BOX) == 'Нажмите 🔊, чтобы послушать слово.' and ev(HOLE), 'step 1: listen button highlighted')
    ok(ev(BTNS) == ['Дальше ➔', '✕ Закончить'], 'step buttons')
    # шаг с ожиданием: человек сам нажимает подсвеченную кнопку
    ev("__spoken=[]"); tap('#speakMainBtn')
    ok(ev(BOX) == 'Выберите слово, которое услышали.', 'tap on highlighted button advances')
    tap('#optionsContainer .option-btn')
    ok(ev(BOX) == 'Здесь можно сказать слово вслух — приложение проверит.', 'choosing advances to the microphone step: ' + ev(BOX))
    for _ in range(6):
        if ev(BOX).startswith('Готово!'): break
        btns = ev(BTNS); click_box(btns[0])
    ok(ev(BOX).startswith('Готово! Обучение можно повторить'), 'final message')
    click_box('Готово ✔')
    ok(ev(BOX) == '' and not ev(HOLE), 'tutorial closed')
    ok(ev("JSON.parse(localStorage.getItem('sr.tour.seen')).full") == 1, 'mode marked as seen')
    # второй вход — без предложения
    ev("goHome(); startMode('full')"); pg.wait_for_timeout(800)
    ok(ev(BOX) == '', 'no offer on second entry')
    # «Не сейчас» тоже запоминается
    ev("goHome(); startMode('wr')"); pg.wait_for_timeout(800)
    ok(ev(BOX) == 'Показать, как здесь заниматься?', 'offer in writing')
    click_box('Не сейчас')
    ok(ev(BOX) == '' and ev("JSON.parse(localStorage.getItem('sr.tour.seen')).wr") == 1, 'not now remembered')
    # повтор из справки режима
    ev("openHelp()"); pg.wait_for_timeout(100)
    ok(ev("document.querySelector('#helpBody .hp-tour').textContent") == '🎓 Обучение', 'tutorial button in mode help')
    ev("document.querySelector('#helpBody .hp-tour').click()"); pg.wait_for_timeout(250)
    ok(not ev("overlayOpen('helpOverlay')") and ev(BOX) == 'Посмотрите на картинку или послушайте 🔊 слово.', 'tutorial from help, help closed')
    # «Назад» завершает обучение и остаётся в режиме
    pg.go_back(); pg.wait_for_timeout(300)
    ok(ev(BOX) == '' and ev("screenName") == 'wr', 'Back ends tutorial, stays in mode')
    # смена экрана завершает
    ev("openHelp(); document.querySelector('#helpBody .hp-tour').click()"); pg.wait_for_timeout(200)
    ev("goHome()"); pg.wait_for_timeout(100)
    ok(ev(BOX) == '' and not ev("TOUR.active"), 'leaving mode ends tutorial')
    # все режимы: есть шаги, каждый видимый
    for m in ['full', 'listen', 'wr', 'ser', 'quiz', 'abc', 'hear', 'phr']:
        ev(f"quiz.active=false; goHome(); startMode('{m}')"); pg.wait_for_timeout(700)
        if ev(BOX): click_box(ev(BTNS)[1])   # «Не сейчас»
        ev(f"tourStart('{m}')"); pg.wait_for_timeout(200)
        cnt = 0; texts = []
        while ev("TOUR.active") and cnt < 8:
            texts.append(ev(BOX)); ok(ev(HOLE), f"{m}: step {cnt+1} highlighted")
            click_box(ev(BTNS)[0]); cnt += 1
        ok(cnt >= 1 and ev(BOX).startswith("Готово!"), f"{m}: {cnt} steps {texts}")
        click_box('Готово ✔')
    # «Перечисления»: выбор ряда — шаг с ожиданием
    ev("quiz.active=false; goHome(); startMode('ser'); serOpen(); tourStart('ser')"); pg.wait_for_timeout(200)
    ok(ev(BOX) == 'Выберите ряд, например дни недели.', 'ser step 1')
    tap('#serScreen .ser-item')
    ok(ev("ser.view") == 'do' and ev(BOX) == 'Здесь можно выбрать направление и задание.', 'ser: choosing a series advances')
    click_box('✕ Закончить'); ok(ev(BOX) == '', 'finish button ends')
    # настройки
    ev("goHome(); openSettings(); settShow('main')")
    ok(ev("document.getElementById('labelTourOffer').textContent") == 'Предлагать обучение при первом входе в режим' and ev("document.getElementById('tourOfferCb').checked") is True, 'setting on by default')
    ev("document.getElementById('tourResetBtn').click()")
    ok(ev("localStorage.getItem('sr.tour.seen')") is None and 'снова будет предложено' in ev("document.getElementById('tourResetNote').textContent"), 'reset tutorials')
    ev("document.getElementById('tourOfferCb').click()"); ev("closeSettings()")
    ev("startMode('abc')"); pg.wait_for_timeout(800)
    ok(ev(BOX) == '', 'offer off: nothing')
    ev("localStorage.setItem('sr.tour.offer','1'); goHome()")
    # вёрстка 277 на трёх языках
    for lang in ['ru', 'uk', 'en']:
        pg.set_viewport_size({'width': 277, 'height': 600})
        ev(f"localStorage.setItem('app_lang','{lang}')"); pg.reload(); pg.wait_for_timeout(500)
        ev("startMode('full'); setTimeout(()=>{},0)"); pg.wait_for_timeout(800)
        if ev(BOX): click_box(ev(BTNS)[0])
        else: ev("tourStart('full')"); pg.wait_for_timeout(200)
        r = ev("(()=>{const b=document.getElementById('tourBox').getBoundingClientRect(); return [b.left, b.right, b.top, b.bottom, innerHeight]})()")
        ok(r[0] >= 0 and r[1] <= 277 and r[2] >= 0 and r[3] <= r[4], f'{lang}: tutorial box inside the screen {r}')
        hs = ev("Math.min(...[...document.querySelectorAll('#tourBox button')].map(b=>b.getBoundingClientRect().height))")
        ok(hs >= 52, f'{lang}: big buttons {hs}')
        ev("tourEnd()")
    # ===== v80: окно обучения не закрывает элемент; значки не читаются вслух
    GEOM = """(()=>{const e=TOUR.el, b=document.getElementById('tourBox'); if(!e) return null; const r=e.getBoundingClientRect(), q=b.getBoundingClientRect(), h=document.querySelector('.app-header').getBoundingClientRect().bottom;
      return {et:r.top, eb:r.bottom, bt:q.top, bb:q.bottom, H:innerHeight, hdr:h}})()"""
    for (w, hgt) in [(360, 740), (360, 560), (277, 480)]:
        for lang in ['ru', 'uk']:
            pg.set_viewport_size({'width': w, 'height': hgt})
            ev(f"localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0')"); pg.reload(); pg.wait_for_timeout(500)
            ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
            for m in ['full', 'listen', 'wr', 'ser', 'quiz', 'abc', 'hear', 'phr']:
                pre = "serOpen(); " if m == 'ser' else ""
                ev(f"quiz.active=false; goHome(); startMode('{m}'); {pre}tourStart('{m}')"); pg.wait_for_timeout(250)
                k = 0
                while ev("TOUR.active") and k < 8:
                    g = ev(GEOM); k += 1
                    tag = f'{w}x{hgt} {lang} {m} step {k}'
                    if g:
                        fits = (g['eb'] - g['et']) + (g['bb'] - g['bt']) + 40 <= g['H'] - g['hdr']
                        overlap = not (g['bt'] >= g['eb'] + 2 or g['bb'] <= g['et'] - 2)
                        if fits: ok(not overlap and g['et'] >= g['hdr'] - 8 and g['bb'] <= g['H'] + 1, tag + ': box beside element ' + str(g))
                        else: ok(g['et'] >= g['hdr'] - 8 and (g['bt'] >= g['et'] + 40 or g['bb'] <= g['et']), tag + ': tall element, its top stays visible ' + str(g))
                    if m == 'ser' and k == 1:
                        ev("document.querySelector('#serScreen .ser-item').click()"); pg.wait_for_timeout(450)
                    else:
                        ev("[...document.querySelectorAll('#tourBox button')][0].click()"); pg.wait_for_timeout(250)
                ev("tourEnd()")
    # ===== v81: реальный путь — 🔊 и выбор слова нажатием; приложение само не уводит кнопку за экран
    GV = """(()=>{const b=document.getElementById('tourBox'); if(!TOUR.el) return null; const r=tourRect(), q=b.getBoundingClientRect(), h=document.querySelector('.app-header').getBoundingClientRect().bottom;
      return {i:TOUR.i+1, et:r.top, eb:r.bottom, bt:q.top, bb:q.bottom, H:innerHeight, hdr:h}})()"""
    def geo_ok(g, tag):
        ok(g and g['et'] >= g['hdr'] - 8 and g['eb'] <= g['H'] + 1 and (g['bt'] >= g['eb'] + 2 or g['bb'] <= g['et'] - 2), tag + ' ' + str(g))
    for (w, hgt) in [(360, 740), (360, 560), (800, 1280)]:
        for lang in ['ru', 'uk']:
            pg.set_viewport_size({'width': w, 'height': hgt})
            ev(f"localStorage.setItem('app_lang','{lang}'); localStorage.removeItem('sr.tour.seen'); localStorage.setItem('sr.tour.offer','1')"); pg.reload(); pg.wait_for_timeout(600)
            tag = f'real {w}x{hgt} {lang}'
            pg.click('.mode-card[data-m="full"]'); pg.wait_for_timeout(900)
            pg.click('#tourBox .primary-btn'); pg.wait_for_timeout(500)
            pg.click('#speakMainBtn'); pg.wait_for_timeout(700)
            ok(ev("TOUR.i") == 1, tag + ': step 2 after 🔊')
            h = pg.evaluate_handle("""(()=>{const t=cleanWord(targetWordSyllables).toLowerCase(); return [...document.querySelectorAll('#optionsContainer button')].find(x=>cleanWord(x.textContent).toLowerCase()===t) || document.querySelector('#optionsContainer button')})()""")
            h.as_element().click()
            pg.wait_for_timeout(2200)   # автопрокрутка приложения срабатывает через 350 и 900 мс
            g = ev(GV); ok(g and g['i'] == 3, tag + ': step 3 (🎤)'); geo_ok(g, tag + ': 🎤 visible, box beside it')
            pg.click('#tourBox .primary-btn'); pg.wait_for_timeout(900)
            g = ev(GV)
            if g and g['i'] == 4:
                geo_ok(g, tag + ': letters + slots visible, box beside them')
                ok(ev("TOUR.el.id") == 'lettersTarget' and ev("TOUR.el2 && TOUR.el2.id") == 'lettersPool', tag + ': slots and letters highlighted together')
                pg.click('#lettersPool .letter-tile'); pg.wait_for_timeout(500)
                ok(ev("document.getElementById('tourBox').classList.contains('mini')"), tag + ': box shrinks after tapping a letter')
                ok(ev("document.querySelectorAll('#lettersTarget .letter-tile').length") >= 1 or ev("spell.placed.filter(Boolean).length") >= 1, tag + ': letter placed during tutorial')
                g = ev(GV); geo_ok(g, tag + ': after tap still beside')
            ev("tourEnd(); quiz.active=false; goHome()")
    # чужая прокрутка во время шага возвращается обучением
    pg.set_viewport_size({'width': 360, 'height': 560})
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("startMode('full'); tourStart('full')"); pg.wait_for_timeout(400)
    ev("tourStep(1); tourStep(1)"); pg.wait_for_timeout(300)
    ev("window.scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(300)
    g = ev(GV); geo_ok(g, 'element scrolled away by app comes back')
    ev("tourEnd()")
    # голос без значков
    pg.set_viewport_size({'width': 360, 'height': 740})
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("startMode('full'); __spoken=[]; tourStart('full')"); pg.wait_for_timeout(500)
    sp = ev("__spoken")
    ok('Нажмите, чтобы послушать слово.' in sp and not any('🔊' in x for x in sp), 'tutorial speech without emoji: ' + str(sp))
    ok(ev("speakableText('Нажмите «Далее ➔», чтобы перейти к новому слову.')") == 'Нажмите «Далее», чтобы перейти к новому слову.', 'arrow removed from speech')
    ok(ev("speakableText('Нажмите 🎤 и повторите слово.')") == 'Нажмите и повторите слово.', 'mic emoji removed')
    ev("tourEnd()")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
