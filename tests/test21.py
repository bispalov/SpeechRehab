# «Полный тренажёр»: сам включать микрофон после выбора и сборки слова (v91)
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
window.__spoken = []; window.__srQueue = []; window.__srLive = 0; window.__srStarts = 0; window.__busy = false;
class FakeSR {
  constructor(){ this.lang=''; this.maxAlternatives=1; }
  start(){ window.__srLive++; window.__srStarts++; this._on=true; const me=this;
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
try { Object.defineProperty(speechSynthesis, 'speaking', { get: () => window.__busy, configurable: true }); } catch (e) {}
try { Object.defineProperty(speechSynthesis, 'pending', { get: () => false, configurable: true }); } catch (e) {}
Object.defineProperty(navigator, 'serviceWorker', {get(){return {register:()=>Promise.reject(new Error('blocked')), addEventListener(){}}}});
"""

fails = []; n = 0
def ok(cond, name):
    global n; n += 1
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 360, 'height': 640})
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(400)
    ev = pg.evaluate
    def fresh(lang='ru', auto=True, req=True, spell=True, choice=True, gentle=True):
        ev(f"""localStorage.clear(); localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0');
              localStorage.setItem('app_timer_enabled','false'); localStorage.setItem('sr.build','word');
              localStorage.setItem('app_full_automic','{str(auto).lower()}'); localStorage.setItem('app_require_speech','{str(req).lower()}');
              localStorage.setItem('app_mode_spell','{str(spell).lower()}'); localStorage.setItem('app_mode_choice','{str(choice).lower()}');
              localStorage.setItem('app_gentle','{str(gentle).lower()}'); localStorage.setItem('app_autospeak','false')""")
        pg.reload(); pg.wait_for_timeout(500)
        ev("document.getElementById('timerEnabled').checked=false; toggleTimerFeature(); startMode('full')"); pg.wait_for_timeout(300)
    def choose(right=True):
        ev("""(()=>{ const t=targetWordClean.toLowerCase(); const bs=[...document.querySelectorAll('.option-btn')];
               const x = %s ? bs.find(b=>b.innerText.toLowerCase()===t) : bs.find(b=>b.innerText.toLowerCase()!==t); x.click(); })()""" % ('true' if right else 'false'))
    def build(word=None):
        ev("""(()=>{ const w = %s || spell.letters.join(''); w.split('').forEach(ch=>{const i=spell.tiles.findIndex(t=>(!t.used||t.reuse)&&t.ch===ch); spellLb.place(i)}) })()""" % (json.dumps(word) if word else 'null'))
    def rec_in_view():
        return ev("(()=>{const r=document.getElementById('recordBtn').getBoundingClientRect(); return r.top>=0 && r.bottom<=innerHeight})()")

    # ===== настройка
    fresh(auto=False)
    ev("openSettings(); settShow('train')"); pg.wait_for_timeout(150)
    lbl = ev("document.getElementById('labelFullAutoMic').textContent")
    ok('Проговорить' in lbl and 'микрофон' in lbl and 'Обязательно проговаривать' in lbl, 'label ru: ' + lbl)
    ok(ev("document.getElementById('fullAutoMic').checked") is False, 'off by default')
    ev("document.getElementById('requireSpeech').checked=false; saveSettings()")
    ok(ev("document.getElementById('fullAutoMic').disabled") is True, 'disabled without «require speech»')
    ev("document.getElementById('requireSpeech').checked=true; saveSettings()")
    ok(ev("document.getElementById('fullAutoMic').disabled") is False, 'enabled with «require speech»')
    ev("document.getElementById('fullAutoMic').click()")
    ok(ev("localStorage.getItem('app_full_automic')") == 'true', 'saved')
    pg.reload(); pg.wait_for_timeout(400)
    ok(ev("document.getElementById('fullAutoMic').checked") is True, 'restored after reload')
    ok(ev("document.documentElement.scrollWidth") <= 360, 'settings: no horizontal scroll')

    # ===== выключено — микрофон сам не включается
    fresh(auto=False); choose(); pg.wait_for_timeout(300); build(); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 0, 'setting off: no microphone')

    # ===== «обязательно проговаривать» выключено — тоже нет
    fresh(auto=True, req=False); choose(); pg.wait_for_timeout(300); build(); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 0, 'require speech off: no microphone')

    # ===== основной путь: выбор → сборка → прокрутка вверх → микрофон
    fresh(); choose(); pg.wait_for_timeout(900)
    ok(ev("__srStarts") == 0, 'after choice (building still to do): no microphone yet')
    ok(not rec_in_view(), 'record button is off screen while building (360x640)')
    ev("__srQueue.push('hold')"); build(); pg.wait_for_timeout(300)
    ok(ev("__srStarts") == 0, 'not at once: waits for the word to be said')
    pg.wait_for_timeout(2200)
    ok(ev("__srStarts") == 1 and ev("isRecording") is True, 'microphone on after building')
    ok(rec_in_view(), 'scrolled to «Проговорить и проверить себя»')
    ok(ev("document.getElementById('recordBtn').classList.contains('nm-cue')"), 'record button blinks')
    ok(ev("document.getElementById('recordBtn').innerText") == ev("i18n.ru.recordBtnStop"), 'button shows recording state')
    # верный ответ
    ev("recognition.stop()"); pg.wait_for_timeout(100)
    ev("__srQueue.push({alts:[targetWordClean.toLowerCase()]}); toggleRecording()"); pg.wait_for_timeout(600)
    ok(ev("speechPassed") is True and ev("document.getElementById('speechResultBox').className").endswith('correct'), 'correct answer accepted, next unlocked')

    # ===== ожидание озвучки: пока синтезатор говорит, микрофон не включается
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("__busy=true; __srQueue.push('hold')"); build(); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 0, 'waits while speech synthesis is speaking')
    ev("__busy=false"); pg.wait_for_timeout(1800)
    ok(ev("__srStarts") == 1, 'microphone on once speaking is over')
    ev("recognition.abort()"); pg.wait_for_timeout(100)

    # ===== неверный ответ — микрофон сам не включается повторно
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['абракадабра']})"); build(); pg.wait_for_timeout(2600)
    ok(ev("__srStarts") == 1 and ev("speechPassed") is False, 'auto microphone heard a wrong word')
    pg.wait_for_timeout(3000)
    ok(ev("__srStarts") == 1 and ev("!!document.querySelector('#speechResultBox .full-countok')"), 'after a wrong answer: no restart, «I said it correctly» available')

    # ===== ошибка распознавания — без петли
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("__srQueue.push({error:'no-speech'})"); build(); pg.wait_for_timeout(2600); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 1, 'recognition error: microphone not restarted')

    # ===== неверная сборка — нет; исправлено — да
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("__srQueue.push('hold')")
    w = ev("spell.letters.join('')")
    if len(set(w)) > 1:
        wrong = w[1] + w[0] + w[2:] if w[0] != w[1] else w[::-1]
        build(wrong); pg.wait_for_timeout(2500)
        ok(ev("__srStarts") == 0, 'wrong build: no microphone')
        ev("lbClear(spell); renderSpellTiles(); spell.spoken=null"); build(); pg.wait_for_timeout(2500)
        ok(ev("__srStarts") == 1, 'fixed build: microphone on')
    ev("try{recognition.abort()}catch(e){}"); pg.wait_for_timeout(100)

    # ===== без сборки: сразу после выбора
    fresh(spell=False); ev("__srQueue.push('hold')"); choose(); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 1 and rec_in_view(), 'no building: microphone after the right choice')
    ev("recognition.abort()"); pg.wait_for_timeout(100)
    fresh(spell=False, gentle=False); ev("__srQueue.push('hold')"); choose(right=False); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 1, 'strict mode, wrong choice (word shown): microphone too — the word still has to be said')
    ev("recognition.abort()"); pg.wait_for_timeout(100)
    fresh(spell=True, gentle=False); choose(right=False); pg.wait_for_timeout(1500)
    ok(ev("__srStarts") == 0, 'strict mode with building: waits for the build')

    # ===== отмена: следующее слово, уход на главный экран, обучение
    fresh(); choose(); pg.wait_for_timeout(300); build(); pg.wait_for_timeout(200)
    ev("nextQuestion()"); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 0, 'next word before the microphone: cancelled')
    fresh(); choose(); pg.wait_for_timeout(300); build(); pg.wait_for_timeout(200)
    ev("goHome()"); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 0, 'left the mode: cancelled')
    fresh(); choose(); pg.wait_for_timeout(300); build(); pg.wait_for_timeout(200)
    ev("TOUR.active = true"); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 0, 'tutorial running: no microphone'); ev("TOUR.active = false")
    fresh(); choose(); pg.wait_for_timeout(300); ev("speechPassed = true"); build(); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 0, 'word already said: no microphone')

    # ===== человек сам нажал 🎤 до сборки
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("window.scrollTo(0,0); __srQueue.push({alts:[targetWordClean.toLowerCase()]}); toggleRecording()"); pg.wait_for_timeout(500)
    ok(ev("speechPassed") is True and ev("__srStarts") == 1, 'said correctly before building')
    ev("spellCardTarget && window.scrollTo(0, spellCardTarget() || 0)"); pg.wait_for_timeout(200); y0 = ev("scrollY")
    build(); pg.wait_for_timeout(2600)
    ok(ev("__srStarts") == 1, 'then built: no microphone again')
    ok(not ev("document.getElementById('recordBtn').classList.contains('nm-cue')"), 'no blinking')
    ok(ev("scrollY") >= y0 - 2, 'not scrolled back up to the button')
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("fullCountOk && (isRecording=false, fullCountOk())"); pg.wait_for_timeout(200)
    build(); pg.wait_for_timeout(2600)
    ok(ev("__srStarts") == 0, '«I said it correctly» before building: no microphone')
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['абракадабра']}); toggleRecording()"); pg.wait_for_timeout(500)
    ok(ev("speechPassed") is False and ev("nextIsLocked()") is True, 'said wrongly before building, next still locked')
    ev("__srQueue.push('hold')"); build(); pg.wait_for_timeout(2600)
    ok(ev("__srStarts") == 2 and rec_in_view(), 'wrong before building: after the build back to the button, microphone on')
    ev("recognition.abort()"); pg.wait_for_timeout(100)
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("speechAttempts = MAX_SPEECH_ATTEMPTS; updateNextLock()")
    build(); pg.wait_for_timeout(2600)
    ok(ev("__srStarts") == 0, 'attempts used up (next unlocked): no microphone')
    fresh(); choose(); pg.wait_for_timeout(300)
    ev("__srQueue.push('hold')"); build(); pg.wait_for_timeout(300)
    ev("toggleRecording()"); pg.wait_for_timeout(2500)
    ok(ev("__srStarts") == 1, 'pressed 🎤 while the word was being said: only one start')
    ev("try{recognition.abort()}catch(e){}"); pg.wait_for_timeout(100)

    # ===== справка и языки
    for L, word in (('ru', 'Сам включать микрофон'), ('uk', 'Самому вмикати мікрофон'), ('en', 'Turn the microphone on by itself')):
        ev(f"localStorage.setItem('app_lang','{L}')"); pg.reload(); pg.wait_for_timeout(400)
        ok(word in ev("helpParse(currentLang).items.map(i=>i.html||i.text||JSON.stringify(i)).join(' ')") or word in ev("document.body.innerHTML"), f'{L}: help mentions the setting')
        lb = ev("document.getElementById('labelFullAutoMic').textContent")
        ok(lb and ev("i18n[currentLang].recordBtnStart").split(' ')[1].rstrip('и') in lb, f'{L}: label names the button: ' + lb)
    ok(ev("helpParse('ru').items.length") == ev("HELP_KEYS.length") == 48, 'help item count')
    # вёрстка настройки
    for W in (360, 313, 277, 240):
        pg.set_viewport_size({'width': W, 'height': 600})
        for L in ('ru', 'uk', 'en'):
            ev(f"localStorage.setItem('app_lang','{L}')"); pg.reload(); pg.wait_for_timeout(300)
            ev("openSettings(); settShow('train')"); pg.wait_for_timeout(150)
            r = ev("(()=>{const e=document.getElementById('fullAutoMic').closest('label').getBoundingClientRect(); return [e.left, e.right, document.documentElement.clientWidth, document.documentElement.scrollWidth]})()")
            ok(r[0] >= 0 and r[1] <= r[2] + 1 and r[3] <= r[2] + 1, f'{L} {W}: setting fits ' + str(r))
    ok(not errs, 'no page errors: ' + str(errs))
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
sys.exit(1 if fails else 0)
