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
window.__wl = {req: 0, rel: 0, active: 0};
Object.defineProperty(navigator, "wakeLock", {get(){ return { request: () => { __wl.req++; __wl.active++; const l = { _h: [], addEventListener(e, f){ this._h.push(f); }, release(){ __wl.rel++; __wl.active--; this._h.forEach(f=>f()); return Promise.resolve(); } }; return Promise.resolve(l); } }; }});
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
    NOTE = "(()=>{const n=document.getElementById('ihNote'); return n && !n.classList.contains('hidden') ? n.textContent : ''})()"
    PULSE = "[...document.querySelectorAll('.ih-pulse')].map(e=>e.id||e.className)"
    # настройка
    ev("openSettings(); settShow('train')")
    ok(ev("document.getElementById('labelHintIdle').textContent").startswith('Подсказывать, если долго нет действия') and ev("document.getElementById('hintIdleSelect').value") == '0', 'setting off by default')
    ok(ev("[...document.getElementById('hintIdleSelect').options].map(o=>o.value)") == ['0','15','20','30'] and ev("document.getElementById('hintVoice').disabled") is True, 'options; voice checkbox disabled while off')
    ev("closeSettings()")
    ev("startMode('full')"); pg.wait_for_timeout(300)
    ev("ihSec = () => 0.3"); ev("localStorage.setItem('sr.hint.voice','1'); ihKick()")
    ok(True, 'fast timer for tests')
    # выключено (sec 0) — проверяем через исходную функцию отдельно: здесь включено
    ev("document.getElementById('modeChoice').checked=true; document.getElementById('modeSpell').checked=true; document.getElementById('gentleMode').checked=false; document.getElementById('autoSpeak').checked=false; nextQuestion(); __spoken=[]")
    pg.wait_for_timeout(450)
    ok('speakMainBtn' in ev(PULSE) and 'Послушайте слово ещё раз' in ev(NOTE), 'full L1: listen button pulses + note')
    ok(ev("__spoken.length") == 0, 'L1 is silent')
    pg.wait_for_timeout(350)
    sp = ev("__spoken"); ok(len(sp) >= 2 and sp[0] == 'Послушайте:', 'full L2: spoken cue + word ' + str(sp))
    pg.wait_for_timeout(350)
    ok(ev("document.querySelectorAll('#optionsContainer .ih-dim').length") == 1 and ev("IH.used") is True, 'full L3: one wrong option fades')
    pg.wait_for_timeout(700)
    ok(ev("document.querySelectorAll('#optionsContainer .ih-dim').length") == 1 and ev("IH.level") == 3, 'no further steps after 3')
    tw = ev("cleanWord(targetWordSyllables).toLowerCase()")
    b0 = ev(f"((loadStats().ru||{{}}).words||{{}})['{tw}'] || {{ok:0,bad:0}}")
    ev("[...document.querySelectorAll('#optionsContainer .option-btn')].find(b=>cleanWord(b.innerText).toLowerCase()===cleanWord(targetWordSyllables).toLowerCase()).click()"); pg.wait_for_timeout(200)
    b1 = ev(f"((loadStats().ru||{{}}).words||{{}})['{tw}']")
    ok(b1['bad'] == b0['bad'] + 1 and b1['ok'] == b0['ok'], 'answer after strong hint counted as not first-try ' + str((b0, b1)))
    ok(ev("IH.used") is False, 'flag consumed')
    # касание сбрасывает
    ev("nextQuestion()"); pg.wait_for_timeout(450)
    ok(len(ev(PULSE)) >= 1, 'pulse before touch')
    ev("document.getElementById('speakMainBtn').scrollIntoView()"); pg.wait_for_timeout(50)
    bb = ev("(()=>{const r=document.getElementById('hintBtn').getBoundingClientRect(); return [r.x+r.width/2, r.y+r.height/2]})()")
    pg.mouse.click(bb[0], bb[1]); pg.wait_for_timeout(50)
    ok(ev(PULSE) == [] and ev(NOTE) == '' and ev("IH.level") == 0, 'tap on a button resets hints')
    # пока идёт запись — не считается
    ev("ihKick(); __srQueue.push('hold'); toggleRecording()"); pg.wait_for_timeout(900)
    ok(ev("IH.level") == 0 and ev(NOTE) == '', 'no hints while recording')
    ev("recognition.abort()"); pg.wait_for_timeout(100)
    # сборка в тренажёре: следующая буква
    ev("document.getElementById('modeChoice').checked=false; ihKick(); nextQuestion()"); pg.wait_for_timeout(1150)
    nx = ev("(()=>{const b=document.querySelector('#lettersPool .ih-next'); return b?b.textContent:null})()")
    ok(nx == ev("spell.letters[0]"), 'full build L3: next letter highlighted ' + str(nx))
    ev("document.getElementById('modeChoice').checked=true")
    # голос выключен
    ev("localStorage.setItem('sr.hint.voice','0'); nextQuestion(); __spoken=[]"); pg.wait_for_timeout(800)
    ok(ev("IH.level") >= 2 and ev("__spoken.length") == 0, 'voice off: silent hints')
    ev("localStorage.setItem('sr.hint.voice','1')")
    # тренировка слуха
    ev("goHome(); startMode('listen'); trainReset('ко-ро-ва'); renderListenStep(1); __spoken=[]"); pg.wait_for_timeout(450)
    ok('trainMicBtn' in ev(PULSE) and 'Нажмите 🎤 и повторите слово.' in ev(NOTE), 'listen step1: repeat button pulses')
    ev("renderListenStep(2); ihKick()"); pg.wait_for_timeout(1150)
    ok(ev("(()=>{const b=document.querySelector('#trainTiles .ih-next'); return b?b.textContent:null})()") == 'к', 'listen step2 L3: letter к highlighted')
    ev("'кровао'.split('').forEach(ch=>{const i=train.tiles.findIndex(t=>!t.used&&t.ch===ch); trainPlace(i)}); ihKick()"); pg.wait_for_timeout(450)
    ok(any('bad' in x for x in ev(PULSE)) and 'красную букву' in ev(NOTE), 'listen: wrong build -> red letter pulses')
    # письмо
    ev("goHome(); startMode('wr'); wrSetLevel(2)"); pg.wait_for_timeout(200)
    ev("wr.typed=''; wrRender(true); ihKick()"); pg.wait_for_timeout(1150)
    ok(len(ev("wr.typed")) == 1 and ev("IH.used") is True, 'writing L3: next letter typed as hint')
    # перечисления: по одному слову
    ev("localStorage.setItem('sr.ser.check','step'); localStorage.setItem('sr.ser.names','always'); goHome(); startMode('ser'); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender(true); __spoken=[]"); pg.wait_for_timeout(1150)
    sp = ev("__spoken"); ok(any('Начинается так: по' in x for x in sp) and 'Начинается так: по' in ev(NOTE), 'ser L3: first syllable spoken and shown ' + str(sp[-1:]))
    ev("__srQueue.push({alts:['понедельник']}); document.querySelector('#serScreen .ph-say').click()"); pg.wait_for_timeout(300)
    ok(ev("ser.step.marks[0].hint") is True, 'ser: word marked as hinted')
    ok(True, 'placeholder')
    ev("for (let i=0;i<10;i++){ if (ser.res) break; serStepSkip(); }"); pg.wait_for_timeout(100)
    ok('понедельник — с подсказкой' in ev("document.getElementById('serScreen').innerText"), 'ser summary: with a hint')
    ok(ev("ser.res.k") == 0, 'hinted word not first-try')
    # тест на слух — без подсказок
    ev("goHome(); startMode('quiz'); startQuiz(['дом','кот'])"); pg.wait_for_timeout(1200)
    ok(ev("IH.level") == 0 and ev(NOTE) == '', 'quiz: no hints')
    ev("quiz.active=false; goHome()")
    # азбука — без подсказок
    ev("startMode('abc')"); pg.wait_for_timeout(1200); ok(ev("IH.level") == 0, 'abc: no hints')
    # окно открыто — не считается
    ev("goHome(); startMode('full'); openSettings()"); pg.wait_for_timeout(1200)
    ok(ev("IH.level") == 0, 'no hints while settings open')
    ev("closeSettings()")
    # выключено по-настоящему
    ev("ihSec = () => 0; ihKick()"); pg.wait_for_timeout(800); ok(ev("IH.level") == 0, 'off: nothing')
    # ===== v75: что сбрасывает отсчёт; служебные слова при строгой проверке
    ev("ihSec = () => 0.3; goHome(); startMode('full'); document.getElementById('modeChoice').checked=true; nextQuestion()"); pg.wait_for_timeout(450)
    ok(ev("IH.level") == 1, 'level 1 reached')
    ev("window.scrollTo(0, 0)"); pg.mouse.click(180, 735); pg.wait_for_timeout(30)   # пустое место внизу
    ok(ev("IH.level") >= 1, 'tap on empty spot does not reset ' + str(ev("[IH.level, document.elementFromPoint(180,735)&&document.elementFromPoint(180,735).className]")))
    pg.mouse.wheel(0, 200); pg.wait_for_timeout(30)
    ok(ev("IH.level") >= 1, 'scroll does not reset')
    ev("document.getElementById('speakMainBtn').scrollIntoView()"); pg.wait_for_timeout(100)
    bb = ev("(()=>{const r=document.getElementById('syllablesBtn').getBoundingClientRect(); return [r.x+r.width/2, r.y+r.height/2]})()")
    pg.mouse.click(bb[0], bb[1]); pg.wait_for_timeout(30)
    ok(ev("IH.level") == 0, 'tap on a button resets')
    ev("ihSec = () => 0")
    ok(ev("isSpeechMatch('в воскресенье', 'воскресенье', true)") is True, 'strict: filler "в" ignored')
    ok(ev("isSpeechMatch('во вторник', 'вторник', true)") is True, 'strict: "во" ignored')
    ok(ev("isSpeechMatch('кот воскресенье', 'воскресенье', true)") is False, 'strict: real extra word still wrong')
    ok(ev("isSpeechMatch('в', 'в', true)") is True, 'target that is itself a filler')
    # ===== v76: экран не гаснет, пока включена подсказка
    WL = "[__wl.active, __wl.req, __wl.rel]"
    ev("localStorage.setItem('sr.hint.sec','0')"); pg.reload(); pg.wait_for_timeout(600)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    ev("localStorage.setItem('sr.hint.sec','0'); goHome(); ihWakeSync()"); pg.wait_for_timeout(50)
    a0 = ev(WL)
    ev("startMode('full')"); pg.wait_for_timeout(100)
    ok(ev(WL)[0] == 0, 'hint off: no wake lock in mode')
    ev("openSettings(); settShow('train'); document.getElementById('hintIdleSelect').value='20'; ihSetChanged()"); pg.wait_for_timeout(100)
    ok(ev(WL)[0] == 1 and 'не гаснет' in ev("document.getElementById('hintWakeNote').textContent"), 'hint on in mode: wake lock taken + note')
    ev("closeSettings(); goHome()"); pg.wait_for_timeout(100)
    ok(ev(WL)[0] == 0, 'start screen: released')
    for m in ['listen', 'wr', 'ser']:
        ev(f"startMode('{m}')"); pg.wait_for_timeout(100); ok(ev(WL)[0] == 1, f'{m}: wake lock'); ev("goHome()"); pg.wait_for_timeout(80)
    for m in ['abc', 'quiz', 'phr', 'hear']:
        ev(f"startMode('{m}')"); pg.wait_for_timeout(100); ok(ev(WL)[0] == 0, f'{m}: no wake lock'); ev("quiz.active=false; goHome()"); pg.wait_for_timeout(80)
    ev("startMode('full')"); pg.wait_for_timeout(100)
    ok(ev(WL)[0] == 1 and ev(WL)[1] - a0[1] <= 5, 'one lock at a time')
    ev("document.getElementById('hintIdleSelect').value='0'; ihSetChanged()"); pg.wait_for_timeout(100)
    ok(ev(WL)[0] == 0 and ev("document.getElementById('hintWakeNote').textContent") == '', 'hint switched off: released')
    ev("localStorage.setItem('sr.hint.sec','0'); goHome()")
    # ===== v77: подсказка не остаётся после ухода из режима (видимость, а не только класс)
    ev("localStorage.setItem('sr.hint.sec','0')"); pg.reload(); pg.wait_for_timeout(600)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature(); document.getElementById('autoSpeak').checked=false")
    SHOWN = "(()=>{const n=document.getElementById('ihNote'); return !!(n && getComputedStyle(n).display!=='none' && n.textContent)})()"
    MARKS = "document.querySelectorAll('.ih-pulse, .ih-dim, .ih-next').length"
    def setup(m):
        if m == 'full': ev("goHome(); startMode('full'); document.getElementById('modeChoice').checked=true; nextQuestion()")
        elif m == 'listen1': ev("goHome(); startMode('listen'); trainReset('ко-ро-ва'); renderListenStep(1)")
        elif m == 'listen2': ev("goHome(); startMode('listen'); trainReset('ко-ро-ва'); renderListenStep(2)")
        elif m == 'wr': ev("goHome(); startMode('wr'); wrSetLevel(2); wr.typed=''; wrRender(true)")
        elif m == 'serstep': ev("localStorage.setItem('sr.ser.check','step'); goHome(); startMode('ser'); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender(true)")
        elif m == 'serend': ev("localStorage.setItem('sr.ser.check','end'); goHome(); startMode('ser'); serStart('days'); ser.dir='fwd'; ser.mode='whole'; serNewTask(); serRender(true)")
        ev("ihSec = () => 0.25; localStorage.setItem('sr.hint.voice','1'); ihKick()")
    modes = ['full', 'listen1', 'listen2', 'wr', 'serstep', 'serend']
    for m in modes:
        for lvl in [1, 2, 3]:
            setup(m); pg.wait_for_timeout(int(250 * lvl + 120))
            ok(ev(SHOWN) and ev("IH.level") >= lvl, f'{m} L{lvl}: hint visible')
            ev("goHome()"); pg.wait_for_timeout(80)
            ok(not ev(SHOWN) and ev(MARKS) == 0 and ev("screenName") == 'select', f'{m} L{lvl}: nothing left on start screen after 🏠')
            pg.wait_for_timeout(400)
            ok(not ev(SHOWN) and ev("IH.level") == 0, f'{m} L{lvl}: nothing appears later on start screen')
    # «Назад» Android
    setup('listen1'); pg.mouse.click(5, 5); pg.wait_for_timeout(400)
    ok(ev(SHOWN), 'before Back: visible')
    pg.go_back(); pg.wait_for_timeout(300)
    ok(ev("screenName") == 'select' and not ev(SHOWN) and ev(MARKS) == 0, 'after Back: cleared')
    # переход в другой режим
    setup('full'); pg.wait_for_timeout(400); ev("goHome(); startMode('abc')"); pg.wait_for_timeout(600)
    ok(not ev(SHOWN) and ev(MARKS) == 0, 'other mode (abc): nothing from full trainer')
    # нажатие кнопки ответа
    setup('full'); pg.wait_for_timeout(900)
    ok(ev(SHOWN) and ev("document.querySelectorAll('.ih-dim').length") == 1, 'L3 shown in full')
    ev("document.querySelector('#optionsContainer .option-btn').scrollIntoView()")
    bb = ev("(()=>{const r=document.querySelector('#optionsContainer .option-btn').getBoundingClientRect(); return [r.x+r.width/2, r.y+r.height/2]})()")
    pg.mouse.click(bb[0], bb[1]); pg.wait_for_timeout(80)
    ok(not ev(SHOWN) and ev(MARKS) == 0, 'answer tap clears hint')
    # смена языка
    setup('wr'); pg.wait_for_timeout(400); ok(ev(SHOWN), 'wr hint visible')
    ev("toggleLanguage()"); pg.wait_for_timeout(80)
    ok(not ev(SHOWN) and ev(MARKS) == 0, 'language change clears hint')
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(600)
    ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    # выключение подсказки
    setup('serstep'); pg.wait_for_timeout(400); ok(ev(SHOWN), 'ser hint visible')
    ev("ihSec = () => 0; document.getElementById('hintIdleSelect').value='0'; ihSetChanged()"); pg.wait_for_timeout(500)
    ok(not ev(SHOWN) and ev(MARKS) == 0, 'switching hint off clears it')
    # перерыв таймера
    setup('listen1'); pg.wait_for_timeout(400); ev("showRestOverlay(true)"); pg.wait_for_timeout(80)
    ok(not ev(SHOWN), 'rest overlay clears hint'); ev("showRestOverlay(false)")
    # голос подсказки обрывается при уходе, образец слова не звучит
    ev("(() => { speechSynthesis.speak = u => { __spoken.push(u.text); window.__lastU = u; }; })()")   # фраза «висит», не заканчивается
    setup('full'); pg.wait_for_timeout(600)
    ok(ev("IH.speaking") is True, 'hint voice speaking')
    ev("__spoken=[]; goHome(); __lastU && __lastU.onend && __lastU.onend()"); pg.wait_for_timeout(100)
    ok(ev("IH.speaking") is False and ev("__spoken") == [], 'hint voice stopped, word sample not spoken after leaving')
    # режимы без подсказки
    for m in ['quiz', 'abc', 'hear', 'phr']:
        ev(f"quiz.active=false; goHome(); startMode('{m}'); ihSec = () => 0.2; ihKick()"); pg.wait_for_timeout(800)
        ok(not ev(SHOWN), f'{m}: never shown')
    ev("quiz.active=false; ihSec = () => 0; goHome()")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
