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

    ROW = "[...document.querySelectorAll('#serScreen .ser-row .ph-chip')].map(c=>c.textContent)"
    def seg(lbl): ev(f"[...document.querySelectorAll('#serScreen .ser-seg button')].find(b=>b.textContent==='{lbl}').click()"); pg.wait_for_timeout(100)
    # ===== v62: параметры задания свёрнуты по умолчанию
    ev("localStorage.removeItem('sr.ser.opts'); localStorage.setItem('sr.ser.names','always'); localStorage.removeItem('sr.ser.check')")
    ev("goHome(); startMode('ser'); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender(true)"); pg.wait_for_timeout(200)
    OPT = "document.querySelector('#serScreen .ser-optbtn')"
    ok(ev("document.querySelectorAll('#serScreen .ser-seg').length") == 0, 'options collapsed by default')
    ok(ev(OPT + ".textContent") == '▶ ⚙️ → Вперёд · Весь ряд · Названия: Видны', 'collapsed summary: ' + ev(OPT + ".textContent"))
    ev(OPT + ".click()"); pg.wait_for_timeout(100)
    ok(ev("document.querySelectorAll('#serScreen .ser-seg').length") == 3 and ev(OPT + ".textContent") == '▼ ⚙️ Параметры задания' and ev(OPT + ".getAttribute('aria-expanded')") == 'true', 'options open')
    ev("[...document.querySelectorAll('#serScreen .ser-seg button')].find(b=>b.textContent==='⇄ Туда и обратно').click()"); pg.wait_for_timeout(100)
    ok(ev("document.querySelectorAll('#serScreen .ser-seg').length") == 3, 'stays open after a choice')
    ev(OPT + ".click()"); pg.wait_for_timeout(100)
    ok(ev(OPT + ".textContent").startswith('▶ ⚙️ ⇄ Туда и обратно') and ev("localStorage.getItem('sr.ser.opts')") == '0', 'closed shows new choice, remembered')
    ev("serOpen(); serStart('months')"); pg.wait_for_timeout(100)
    ok(ev("document.querySelectorAll('#serScreen .ser-seg').length") == 0, 'closed state kept for another series')
    ev("localStorage.setItem('sr.ser.opts','1')")
    ev("localStorage.setItem('sr.ser.names','always'); localStorage.removeItem('sr.ser.check')")
    ev("goHome(); startMode('ser'); serStart('days')"); pg.wait_for_timeout(300)
    ev("ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender(true)")
    ok(len(ev(ROW)) == 7, 'always: row before recognition')
    ev("__srQueue.push({alts:['понедельник вторник пятница']}); serListen()"); pg.wait_for_timeout(600); ev("serFinish()"); pg.wait_for_timeout(200)
    ok(ev("!!ser.res && !ser.res.allOk"), 'result with errors')
    ok(len(ev(ROW)) == 7, 'always: row stays after recognition (bug fix)')
    seg('После ошибок'); ok(len(ev(ROW)) == 0 and ev("!!document.querySelector('#serScreen .ph-reveal')"), 'v67: switching to onerr hides row (waits for next error), reveal button shown')
    seg('Видны'); ok(len(ev(ROW)) == 7, 'back to always: row visible')
    seg('Скрыты'); ok(len(ev(ROW)) == 0 and ev("!!document.querySelector('#serScreen .ph-reveal')"), 'never: row hidden, reveal button')
    seg('Видны'); ok(len(ev(ROW)) == 7, 'always again after never')
    # «После ошибок»: до ошибки скрыто, после — видно и при повторе
    seg('После ошибок'); ev("serNewTask(); serRender(true)")
    ok(len(ev(ROW)) == 0, 'onerr: hidden before any error')
    ev("__srQueue.push({alts:['понедельник среда']}); serListen()"); pg.wait_for_timeout(600); ev("serFinish()"); pg.wait_for_timeout(200)
    ok(len(ev(ROW)) == 7, 'onerr: shown after error')
    ev("__srQueue.push('hold'); serListen()"); pg.wait_for_timeout(150)
    ok(len(ev(ROW)) == 7, 'onerr: still shown on retry while listening')
    ok(ev("[...document.querySelectorAll('#serScreen .ser-seg button')].every(b=>b.disabled)"), 'segment buttons disabled while listening')
    ev("serStop(); ser.listening=false; serNewTask(); serRender(true)")
    ok(len(ev(ROW)) == 0, 'onerr: hidden again on new task')
    # ===== проверка по одному слову
    ev("serStop(); ser.listening=false")
    BTN = "document.querySelector('#serScreen .ph-say').textContent"
    def say(alts):
        ev("__srQueue.push(" + _json.dumps({'alts': alts}, ensure_ascii=False) + "); document.querySelector('#serScreen .ph-say').click()"); pg.wait_for_timeout(250)
    import json as _json
    ev("localStorage.setItem('sr.ser.names','always'); localStorage.setItem('sr.ser.check','step'); serOpen(); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender(true)")
    ok(ev(BTN) == '🎤 Назвать первое слово', 'step: first-word button')
    ok('hl' in ev("document.querySelector('#serScreen [data-hl=\"0\"]').className"), 'step: first word highlighted')
    ok('перед каждым словом' in ev("document.getElementById('serScreen').innerText"), 'step: hint shown')
    ev("__srQueue.push('hold'); document.querySelector('#serScreen .ph-say').click()"); pg.wait_for_timeout(100)
    ok(ev(BTN) == '⏺ Слушаю…' and 'rec' in ev("document.querySelector('#serScreen .ph-say').className"), 'step: red listening button')
    ok(ev("[...document.querySelectorAll('#serScreen .ser-seg button')].every(b=>b.disabled)"), 'step: segments disabled while listening')
    ok(ev("modeRec.maxAlternatives") == 3 and ev("modeRec.interimResults") is False, 'step: 3 alternatives, no interim')
    ev("stopModeRec(); ser.listening=false; serRender(true)")
    say(['понедельник'])
    r = ev(ROW)
    ok(r[0] == '1. понедельник ✅' and 'hl' in ev("document.querySelector('#serScreen [data-hl=\"1\"]').className") and ev(BTN) == '🎤 Назвать следующее слово', 'step: correct word ticked, moves on')
    ev("__spoken=[]"); say(['в среду', 'среду'])
    r = ev(ROW)
    ok(r[1] == '2. вторник ❌ ← в среду (это № 3)', 'step: wrong word explained: ' + r[1])
    ok(ev(BTN) == '🎤 Ещё раз это слово', 'step: retry button')
    ok(ev("[...document.querySelectorAll('#serScreen .abc-row button')].map(b=>b.textContent).join('|')").count('Пропустить') == 1, 'step: skip offered')
    ok('Нет. Нужно: вторник.' in ev("__spoken"), 'step: short model phrase after error')
    say(['вторник', 'вторники'])
    ok(ev(ROW)[1] == '2. вторник ✅' and ev(BTN) == '🎤 Назвать следующее слово', 'step: retry succeeds')
    say(['середа'])
    ev("[...document.querySelectorAll('#serScreen .abc-row button')].find(b=>b.textContent.startsWith('✔')).click()"); pg.wait_for_timeout(100)
    ok(ev(ROW)[2] == '3. среда ✅', 'step: "I said it correctly" accepts word')
    say(['кот'])
    ev("serStepSkip()"); pg.wait_for_timeout(100)
    ok(ev(ROW)[3].startswith('4. четверг ❌') and 'hl' in ev("document.querySelector('#serScreen [data-hl=\"4\"]').className"), 'step: skip moves on')
    say(['пятницу']); say(['субботу']);
    ev("__srQueue.push({alts:[]}); document.querySelector('#serScreen .ph-say').click()"); pg.wait_for_timeout(250)
    ok('Ничего не расслышал' in ev("document.getElementById('serScreen').innerText") and 'hl' in ev("document.querySelector('#serScreen [data-hl=\"6\"]').className"), 'step: nothing heard keeps place')
    n0 = ev("(serStats()['days:fwd']||{n:0}).n")
    say(['в воскресенье'])
    ok(ev("ser.res && ser.res.step") is True and ev("ser.res.k") == 4, 'step: summary first-try count ' + str(ev("ser.res && ser.res.k")))
    ok('С первой попытки: 4 из 7' in ev("document.getElementById('serScreen').innerText"), 'step: summary text')
    txt = ev("document.getElementById('serScreen').innerText")
    ok('вторник — со второй попытки' in txt and 'четверг — пропущено' in txt and 'Вы сказали' not in txt, 'step: summary notes')
    ok(ev("(serStats()['days:fwd']||{n:0}).n") == n0 + 1, 'step: one stat record per series')
    ok(ev(BTN) == '🎤 Ещё раз', 'step: again button after summary')
    ev("document.querySelector('#serScreen .ph-say').click()"); pg.wait_for_timeout(100)
    ok(ev(BTN) == '🎤 Назвать первое слово' and not ev("ser.res"), 'step: again restarts')
    # скрытые названия: ряд открывается по ходу
    ev("localStorage.setItem('sr.ser.names','never'); serNewTask(); serRender(true)")
    LEFT = "(document.querySelector('#serScreen .ser-left')||{}).textContent"
    ok(ev(ROW) == ['▢ ?'] and ev(LEFT) == 'ещё 6', 'step+never: only "▢ ?" and counter')
    ev("__spoken=[]"); say(['вторник'])
    ok(ev(ROW) == ['▢ ? ❌ ← вторник (это слово идёт позже)'] and 'Нет. Ещё раз.' in ev("__spoken"), 'step+never: heard shown, target hidden: ' + str(ev(ROW)))
    say(['понедельник'])
    ok(ev(ROW) == ['понедельник ✅', '▢ ?'] and ev(LEFT) == 'ещё 5', 'step+never: said word opens')
    ev("serStepSkip()"); pg.wait_for_timeout(100)
    ok(ev(ROW)[1] == 'вторник ❌' and ev(ROW)[2] == '▢ ?', 'step+never: skipped word opens')
    say(['понедельник'])
    ok('это слово уже было' in ev(ROW)[2], 'step+never: earlier word explained')
    ev("for (let i=0;i<10;i++) { if (ser.res) break; serStepSkip(); }"); pg.wait_for_timeout(100)
    ok(ev("ser.res && ser.res.step") is True and '▢' not in ev("document.getElementById('serScreen').innerText").split('С первой попытки')[1], 'step+never: summary not masked')
    # «После ошибок»: после первой ошибки весь ряд с номерами
    ev("localStorage.setItem('sr.ser.names','onerr'); serNewTask(); serRender(true)")
    ok(ev(ROW) == ['▢ ?'], 'step+onerr: hidden before error')
    say(['среда'])
    r = ev(ROW); ok(len(r) == 7 and r[0] == '1. понедельник ❌ ← среда (это № 3)', 'step+onerr: row opens after error: ' + str(r[:1]))
    # туда и обратно, «Продолжить»
    ev("localStorage.setItem('sr.ser.names','always'); ser.dir='round'; serNewTask(); serRender(true)")
    ok(ev(BTN) == '🎤 Назвать первое слово' and len(ev(ROW)) == 13, 'step round: 13 words')
    say(['понедельник']); say(['вторник'])
    ok('hl' in ev("document.querySelector('#serScreen [data-hl=\"2\"]').className"), 'step round: second word fine')
    ev("ser.dir='fwd'; ser.mode='cont'; serNewTask(); serRender(true)")
    g = ev("ser.given")
    ok(ev(BTN) == '🎤 Назвать следующее слово' and 'hl' in ev(f"document.querySelector('#serScreen [data-hl=\"{g}\"]').className"), 'step continue: starts after given words')
    ev("ser.mode='whole'")
    # старое значение 'live' становится пошаговой проверкой
    ev("localStorage.setItem('sr.ser.check','live')"); ok(ev("serPref().check") == 'step', 'live migrates to step')
    ev("localStorage.setItem('sr.ser.check','end'); serNewTask(); serRender(true)")
    ok(ev("ser.step") is None and ev(BTN) == '🎤 Говорить', 'end mode: normal button')
    # настройки
    ev("openSettings(); settShow('ser')")
    ok(ev("document.getElementById('labelSerCheck').innerText").startswith('🔢 Перечисления: когда'), 'setting label')
    ev("document.getElementById('serCheckSelect').value='step'; extraSettingChanged('serCheck')")
    ok(ev("serPref().check") == 'step', 'setting saved')
    ok('По одному слову' in ev("document.getElementById('optSerCL').textContent"), 'setting option label')
    # ===== v57: служебные слова, формы слов, «туда и обратно» по ходу
    ev("serOpen(); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask()")
    ok(ev("serEval(serTarget(), 'понедельник вторник среда четверг пятница суббота в воскресенье', null).allOk") is True, 'filler "в" ignored')
    ok(ev("serEval(serTarget(), 'понедельник во вторник в среду и четверг в пятницу в субботу в воскресенье', null).allOk") is True, 'case forms accepted')
    ok(ev("serEval(serTarget(), 'понедельник вторник срода четверг пятница суббота воскресенье', null).allOk") is False, 'real mistake still wrong')
    ok(ev("serEval(serTarget(), 'понедельник вторник среда четверг пятница суббота воскресенье кот', null).allOk") is False, 'real extra word still wrong')
    ev("ser.dir='round'; serNewTask()")
    ok(ev("serEval(serTarget(), 'понедельник вторник среда четверг пятница суббота воскресенье воскресенье суббота пятница четверг среда вторник понедельник', serTurnWord()).allOk") is True, 'round final ok')
    ev("localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ev("startMode('ser'); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask()")
    ok(ev("serEval(serTarget(), serTarget().slice(0,6).join(' ') + ' у неділю', null).allOk") is True, 'uk: "у неділю" accepted')
    # ===== v60: прокрутка к кнопке и остановка озвучки
    pg.set_viewport_size({'width': 360, 'height': 560})
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    ev("localStorage.setItem('sr.ser.names','always'); localStorage.setItem('sr.ser.check','step'); startMode('ser'); serStart('months'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender()")
    FIT = """(()=>{const b=document.querySelector('#serScreen .ph-say').getBoundingClientRect(), h=document.querySelector('#serScreen .ph-chip.hl'), hd=document.querySelector('.app-header').getBoundingClientRect();
      return {btnBottom:b.bottom, H:innerHeight, hlTop:h?h.getBoundingClientRect().top:null, hdr:hd.bottom}})()"""
    for k in range(4):
        say(['январь','февраль','март','апрель'][k:k+1])
    f = ev(FIT); ok(f['btnBottom'] <= f['H'] and (f['hlTop'] - 6 >= f['hdr'] - 1 or f['btnBottom'] - f['hlTop'] + 6 > f['H'] - f['hdr']), 'fit after correct word: ' + str(f))
    say(['кот'])
    f = ev(FIT); ok(f['btnBottom'] <= f['H'] and (f['hlTop'] - 6 >= f['hdr'] - 1 or f['btnBottom'] - f['hlTop'] + 6 > f['H'] - f['hdr']), 'fit after error: ' + str(f))
    ev("serStepSkip()"); pg.wait_for_timeout(150)
    f = ev(FIT); ok(f['btnBottom'] <= f['H'] and (f['hlTop'] - 6 >= f['hdr'] - 1 or f['btnBottom'] - f['hlTop'] + 6 > f['H'] - f['hdr']), 'fit after skip')
    pg.set_viewport_size({'width': 360, 'height': 740}); ev("serRender(true); ser.fit=true; serRender(true)"); f = ev(FIT)
    ok(f['btnBottom'] <= f['H'] and f['hlTop'] >= f['hdr'], 'taller screen: button and current word both visible ' + str(f))
    ev("for (let i=0;i<20;i++) { if (ser.res) break; serStepSkip(); }"); pg.wait_for_timeout(150)
    sc = ev("(()=>{const r=document.querySelector('#serScreen .ph-score').getBoundingClientRect(); return [r.top, r.bottom, innerHeight]})()")
    ok(sc[0] >= 0 and sc[1] <= sc[2], 'summary score visible ' + str(sc))
    # озвучка ряда: повторное нажатие останавливает
    ev("serNewTask(); serRender(true)")
    ev("window.__held=[]; window.__cancels=0; speechSynthesis.speak = u => { window.__held.push(u); setTimeout(()=>u.onstart&&u.onstart(),5) }; const c0=speechSynthesis.cancel.bind(speechSynthesis); speechSynthesis.cancel = () => { window.__cancels++; }")
    LB = "[...document.querySelectorAll('#serScreen .abc-row button')].map(b=>b.textContent)"
    ev("[...document.querySelectorAll('#serScreen .abc-row button')].find(b=>b.textContent==='🔊 Послушать').click()"); pg.wait_for_timeout(100)
    ok('⏹ Остановить' in ev(LB) and ev("ser.playing") is True and ev("__held.length") == 12, 'listen turns into stop')
    c = ev("__cancels")
    ev("[...document.querySelectorAll('#serScreen .abc-row button')].find(b=>b.textContent==='⏹ Остановить').click()"); pg.wait_for_timeout(100)
    ok('🔊 Послушать' in ev(LB) and ev("ser.playing") is False and ev("__cancels") > c, 'second tap stops playback')
    ok('hl' in ev("document.querySelector('#serScreen [data-hl=\"0\"]').className"), 'current word highlight restored after stop')
    ev("__held[11].onend && __held[11].onend()"); pg.wait_for_timeout(50)
    ok('🔊 Послушать' in ev(LB), 'late end of stopped playback ignored')
    ev("[...document.querySelectorAll('#serScreen .abc-row button')].find(b=>b.textContent==='🔊 Послушать').click()"); pg.wait_for_timeout(50)
    ev("__held[__held.length-1].onend()"); pg.wait_for_timeout(50)
    ok('🔊 Послушать' in ev(LB) and ev("ser.playing") is False, 'button returns after playback ends')
    ev("[...document.querySelectorAll('#serScreen .abc-row button')].find(b=>b.textContent==='🔊 Послушать').click()"); pg.wait_for_timeout(50)
    ev("document.querySelector('#serScreen .ser-row .ph-chip').click()"); pg.wait_for_timeout(50)
    ok(ev("ser.playing") is False and '🔊 Послушать' in ev(LB), 'tapping a word stops series playback')
    ev("[...document.querySelectorAll('#serScreen .abc-row button')].find(b=>b.textContent==='🔊 Послушать').click()"); pg.wait_for_timeout(50)
    ev("__srQueue.push('hold'); document.querySelector('#serScreen .ph-say').click()"); pg.wait_for_timeout(50)
    ok(ev("ser.playing") is False, 'mic stops playback')
    ev("stopModeRec(); ser.listening=false")
    # ===== v61: короткое «Да», если отмеченное слово ушло за экран
    pg.set_viewport_size({'width': 360, 'height': 560})
    ev("speechSynthesis.speak = u => { __spoken.push(u.text); setTimeout(()=>{u.onstart&&u.onstart(); u.onend&&u.onend();},5) }; speechSynthesis.cancel = () => {}")
    ev("localStorage.setItem('sr.ser.names','always'); localStorage.setItem('sr.ser.check','step'); serOpen(); serStart('months'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender()")
    sp = []
    for w in ['январь','февраль','март','апрель','май']:
        ev("__spoken=[]"); say([w]); sp.append((w, ev("__spoken.slice()"), ev("serChipVisible(ser.step.i-1)")))
    print(sp)
    ok(all((('Да.' in x[1]) == (not x[2])) for x in sp), 'yes spoken exactly when the ticked word is off screen')
    ok(any('Да.' in x[1] for x in sp), 'off-screen case occurs on a small screen')
    pg.set_viewport_size({'width': 360, 'height': 900})
    ev("serNewTask(); serRender()")
    ev("__spoken=[]"); say(['январь'])
    ok(ev("__spoken.length") == 0, 'visible word: silent tick')
    ev("serOpen(); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender()")
    pg.set_viewport_size({'width': 360, 'height': 420})
    for w in ['понедельник','вторник','среда','четверг','пятница','суббота']: say([w])
    ev("__spoken=[]"); say(['воскресенье'])
    ok('Да.' not in ev("__spoken") and len(ev("__spoken")) == 1, 'last word: only the summary is spoken ' + str(ev("__spoken")))
    pg.set_viewport_size({'width': 360, 'height': 740})
    # ===== v67: «После ошибок» — матрица переключений до и после распознавания
    pg.set_viewport_size({'width': 360, 'height': 740})
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    REV = "[...document.querySelectorAll('#serScreen .ph-reveal')].map(b=>b.textContent)"
    for check in ['end', 'step']:
        ev(f"localStorage.setItem('sr.ser.opts','1'); localStorage.setItem('sr.ser.check','{check}'); localStorage.setItem('sr.ser.names','always'); goHome(); startMode('ser'); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender(true)")
        tag = ' [' + check + ']'
        vis = lambda: len([x for x in ev(ROW) if not x.startswith('▢')])
        ok(vis() == 7, 'always before' + tag)
        seg('После ошибок'); ok(vis() == 0 and '👁 Показать ряд' in ev(REV), 'always→onerr before recognition: hidden + show button' + tag)
        seg('Видны'); ok(vis() == 7, 'onerr→always' + tag)
        seg('После ошибок')
        # ошибка
        if check == 'end':
            ev("__srQueue.push({alts:['понедельник среда']}); serListen()"); pg.wait_for_timeout(600); ev("serFinish()"); pg.wait_for_timeout(150)
        else:
            say(['среда'])
        ok(vis() >= 1 and 'Названия открыты после ошибки.' in ev("document.getElementById('serScreen').innerText") and '🙈 Скрыть ряд' in ev(REV), 'onerr: opened after error with note and hide button' + tag)
        ev("[...document.querySelectorAll('#serScreen .ph-reveal')].find(b=>b.textContent==='🙈 Скрыть ряд').click()"); pg.wait_for_timeout(100)
        ok(vis() == 0 or (check == 'step'), 'hide button hides' + tag)
        seg('Видны'); seg('После ошибок')
        ok(vis() == 0 or (check == 'step'), 'always→onerr after an error: hidden again' + tag)
        seg('Скрыты'); ok(vis() == 0 or (check == 'step'), 'never hidden' + tag)
        ev("[...document.querySelectorAll('#serScreen .ph-reveal')].find(b=>b.textContent==='👁 Показать ряд').click()"); pg.wait_for_timeout(100)
        ok('🙈 Скрыть ряд' in ev(REV), 'never + shown by button: hide button offered' + tag)
        seg('Видны'); ok(not ev(REV), 'always: no show/hide buttons' + tag)
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
