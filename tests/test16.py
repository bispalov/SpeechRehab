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


REC = r"""
window.__gum = 'ok'; window.__tracksStopped = 0; window.__recStarted = 0; window.__played = [];
try {
  if (!navigator.mediaDevices) Object.defineProperty(navigator, 'mediaDevices', { value: {}, configurable: true });
  navigator.mediaDevices.getUserMedia = async () => {
    if (window.__gum === 'deny') { const e = new Error('denied'); e.name = 'NotAllowedError'; throw e; }
    return { getTracks: () => [{ stop() { window.__tracksStopped++; } }] };
  };
} catch (e) {}
window.MediaRecorder = class {
  constructor(s) { this.stream = s; this.state = 'inactive'; this.mimeType = 'audio/webm'; window.__mr = this; }
  start() { this.state = 'recording'; window.__recStarted++; }
  stop() { if (this.state === 'inactive') return; this.state = 'inactive'; if (this.ondataavailable) this.ondataavailable({ data: new Blob([new Uint8Array(4000)]) }); setTimeout(() => this.onstop && this.onstop(), 10); }
};
window.Audio = function (src) { return { src, play() { window.__played.push(src); setTimeout(() => { this.onended && this.onended(); }, 200); return Promise.resolve(); }, pause() {} }; };
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 360, 'height': 740})
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    ctx.add_init_script(MOCK); ctx.add_init_script(REC)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(400)
    ev = pg.evaluate
    def fresh(lang='ru', extra=''):
        ev(f"localStorage.clear(); localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('app_timer_enabled','false'); {extra}")
        pg.reload(); pg.wait_for_timeout(500)
    def say(alt):
        ev(f"__srQueue.push({{alts:[{alt!r}]}}); document.querySelector('#readScreen .rd-mic').click()"); pg.wait_for_timeout(350)
    fresh()
    # ===== стартовый экран и настройки
    order = ev("[...document.querySelectorAll('#modeSelect .mode-card[data-m]')].map(c=>c.dataset.m)")
    ok(order.index('read') == order.index('listen') + 1, 'card after listening: ' + str(order))
    ok(ev("document.getElementById('modeReadTitle').textContent") == '📖 Читаю вслух', 'ru title')
    ok('read' in ev("HOME_MODES") and ev("SCREEN_IDS.read") == 'readScreen', 'registered mode')
    ev("openSettings(); settShow('read')"); pg.wait_for_timeout(200)
    ok(ev("document.querySelectorAll('#rdSettBox select').length") == 5 and ev("document.querySelectorAll('#rdSettBox input[type=checkbox]').length") == 5, 'settings group: 5 selects + 5 checkboxes')
    ok(ev("document.getElementById('sgt_read').textContent") == '📖 Читаю вслух', 'settings group title')
    ev("closeSettings()")
    # ===== список
    ev("startMode('read')"); pg.wait_for_timeout(200)
    ok(ev("rd.view") == 'list' and 'Список пуст' in ev("document.getElementById('readScreen').textContent"), 'empty list message')
    ok(not ev("!!document.querySelector('#readScreen .rd-start')"), 'no start button on empty list')
    pg.fill('#rdInput', 'Корова'); pg.click('#readScreen .ph-add'); pg.wait_for_timeout(150)
    ok(ev("rd.list.length") == 1 and ev("rd.list[0].w") == 'корова', 'word added (lowercased)')
    pg.fill('#rdInput', 'корова'); pg.click('#readScreen .ph-add'); pg.wait_for_timeout(150)
    ok(ev("rd.list.length") == 1 and 'уже в списке' in ev("document.getElementById('readScreen').textContent"), 'duplicate rejected')
    pg.fill('#rdInput', 'два слова'); pg.press('#rdInput', 'Enter'); pg.wait_for_timeout(150)
    ok(ev("rd.list.length") == 1 and 'одно слово' in ev("document.getElementById('readScreen').textContent") and ev("document.getElementById('rdInput').value") == 'два слова', 'two words rejected, text kept')
    pg.fill('#rdInput', 'помидор'); pg.press('#rdInput', 'Enter'); pg.wait_for_timeout(150)
    ok(ev("rd.list.length") == 2 and ev("JSON.parse(localStorage.getItem('sr.read.ru')).length") == 2, 'saved to sr.read.ru')
    # ===== ступень 1: слоги, подсветка, образец не звучит до попытки
    ev("__spoken.length=0; rdStartWord(0)"); pg.wait_for_timeout(300)
    ok(ev("[...document.querySelectorAll('#readScreen .rd-show .rd-syl')].map(b=>b.textContent).join('-')") == 'ко-ро-ва', 'syllables from dictionary')
    ok('Ступень 1 из 4' in ev("document.getElementById('readScreen').textContent"), 'stage 1 of 4')
    pg.wait_for_timeout(500)
    ok(ev("document.querySelectorAll('#readScreen .rd-show .rd-syl.on').length") == 1, 'syllable highlighted')
    hl = []
    for k in range(4):
        hl.append(ev("[...document.querySelectorAll('#readScreen .rd-show .rd-syl')].findIndex(b=>b.classList.contains('on'))")); pg.wait_for_timeout(950)
    ok(hl[:3] == [0, 1, 2] and hl[3] == -1, 'highlight moves syllable by syllable then clears: ' + str(hl))
    ok(not any('корова' in x for x in ev("__spoken")), 'word not spoken before the attempt')
    ev("document.querySelectorAll('#readScreen .rd-show .rd-syl')[1].click()"); pg.wait_for_timeout(200)
    ok(ev("__spoken.slice(-1)[0]") == 'ро', 'tap syllable speaks it')
    # ===== попытка с ошибкой
    ev("__spoken.length=0")
    say('карова')
    txt = ev("document.querySelector('#readScreen .rd-res').textContent")
    ok('Не совсем' in txt and 'карова' in txt, 'wrong attempt: verdict and heard')
    ok(ev("[...document.querySelectorAll('#readScreen .rd-res .rd-syl')].map(b=>b.classList.contains('bad'))") == [True, False, False], 'first syllable red')
    pg.wait_for_timeout(1500)
    ok(any('корова' in x for x in ev("__spoken")), 'model spoken after the mistake')
    ev("document.querySelectorAll('#readScreen .rd-res .rd-syl')[0].click()"); pg.wait_for_timeout(150)
    ok(ev("__spoken.slice(-1)[0]") == 'ко', 'tap red syllable speaks it')
    ok('Верно подряд: 0 из 2' in ev("document.getElementById('readScreen').textContent"), 'streak reset')
    ev("document.querySelector('#readScreen .rd-countok').click()"); pg.wait_for_timeout(150)
    ok(ev("rd.list[0].k") == 1 and 'Засчитано' in ev("document.getElementById('readScreen').textContent"), '"I said it correctly" counts')
    say('корова')
    ok(ev("rd.list[0].s") == 2 and ev("rd.stageNext") and ev("!!document.querySelector('#readScreen .rd-nextstage')") and not ev("!!document.querySelector('#readScreen .rd-mic')"), 'stage done after 2 in a row')
    # ===== ступень 2: целиком медленно, подсветка по слову
    ev("document.querySelector('#readScreen .rd-nextstage').click()"); pg.wait_for_timeout(700)
    ok('Ступень 2 из 4' in ev("document.getElementById('readScreen').textContent") and ev("!!document.querySelector('#readScreen .rd-show .rd-word.joined')"), 'stage 2: whole word')
    ok(ev("!!document.querySelector('#readScreen .rd-show .rd-word.sweep')"), 'stage 2: highlight sweeps along the word')
    say('корова'); say('корова')
    ev("rdNextStage()"); pg.wait_for_timeout(300)
    ok('Ступень 3 из 4' in ev("document.getElementById('readScreen').textContent") and not ev("!!document.querySelector('#readScreen .rd-replay')"), 'stage 3: no highlight button')
    say('8'); 
    ok(ev("rd.res.ok") is False, 'wrong word at stage 3')
    say('корова'); say('корова')
    # ===== ступень 4: на слух
    ev("__spoken.length=0; rdNextStage()"); pg.wait_for_timeout(800)
    ok(ev("!document.querySelector('#readScreen .rd-show .rd-syl')") and ev("!!document.querySelector('#readScreen .rd-hidden')"), 'stage 4: word hidden')
    ok(ev("document.querySelector('#readScreen .rd-hidden').textContent") == '🐮', 'picture on the by-ear step')
    ok(any('корова' in x for x in ev("__spoken")), 'stage 4: word spoken')
    ok(ev("document.querySelector('#readScreen .rd-mic').textContent") == '🎤 Повторить', 'mic label "Repeat"')
    say('корона')
    ok(ev("rd.list[0].s") == 3 and ev("rd.revealed") and ev("!!document.querySelector('#readScreen .rd-show .rd-syl')") and 'Вернёмся к чтению' in ev("document.getElementById('readScreen').textContent"), 'mistake by ear: word shown, back to stage 3')
    say('корова'); say('корова'); ev("rdNextStage()"); pg.wait_for_timeout(300)
    say('корова'); say('корова')
    ok(ev("rd.done") == 'day' and ev("rd.list[0].d.length") == 1 and not ev("rd.list[0].done") and ev("rd.list[0].s") == 1, 'by ear done today; not learned yet (2 days)')
    ok(ev("!!document.querySelector('#readScreen .rd-next.primary-btn')"), 'next word is the main button')
    ev("rd.list[0].d=['2026-01-01']; rd.list[0].s=4; rdStartWord(0)"); pg.wait_for_timeout(300)
    say('корова'); say('корова')
    ok(ev("rd.done") == 'word' and ev("rd.list[0].done") == 1, 'learned after 2 different days')
    ev("rdNextWord()"); pg.wait_for_timeout(300)
    ok(ev("rd.list[rd.i].w") == 'помидор' and ev("[...document.querySelectorAll('#readScreen .rd-show .rd-syl')].map(b=>b.textContent).join('-')") == 'по-ми-дор', 'next word, syllables by rule')
    ev("rdBack()"); pg.wait_for_timeout(200)
    ok(ev("rd.view") == 'list' and 'Освоено (1)' in ev("document.getElementById('readScreen').textContent"), 'learned list collapsed with count')
    ev("document.querySelector('#readScreen .rd-donebtn').click()"); pg.wait_for_timeout(100)
    ev("document.querySelector('#readScreen .rd-ret').click()"); pg.wait_for_timeout(100)
    ok(ev("rd.list[0].done") == 0 and ev("rd.list[0].d.length") == 0, 'learned word brought back')
    # ===== настройки
    ev("rdSetChange('need',1); rdSetChange('ear',0); rdSetChange('start',2); rdSetChange('days',1)")
    ev("rd.list=[]; rdSave(); rdAdd('собака'); rdStartWord(0)"); pg.wait_for_timeout(200)
    ok('Ступень 2 из 3' in ev("document.getElementById('readScreen').textContent"), 'start step 2, no by-ear step: 2 of 3')
    say('собака')
    ok(ev("rd.list[0].s") == 3, 'need=1: one correct moves on')
    ev("rdNextStage()"); pg.wait_for_timeout(200); say('собака')
    ok(ev("rd.done") == 'word', 'without by-ear step: learned after stage 3 (days=1)')
    ev("rdSetChange('okModel',1); rd.list=[]; rdSave(); rdAdd('корова'); rdStartWord(0); __spoken.length=0"); pg.wait_for_timeout(200)
    say('корова'); pg.wait_for_timeout(1200)
    ok(any('корова' in x for x in ev("__spoken")), 'okModel: model after a correct try')
    ev("localStorage.removeItem('sr.read.set')")
    # ===== цифры
    ev("rd.list=[]; rdSave(); rdAdd('восемь'); rdStartWord(0)"); pg.wait_for_timeout(200)
    say('8')
    ok(ev("rd.res.ok") is True and ev("rd.res.heard") == 'восемь', '"8" counts as "восемь"')
    # ===== послушать себя
    ev("rd.list=[]; rdSave(); rdAdd('корова'); rdStartWord(0); __spoken.length=0; __played.length=0"); pg.wait_for_timeout(200)
    ev("document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(200)
    ok(ev("rd.recording") and ev("document.querySelector('#readScreen .rd-rec').textContent") == '⏹ Стоп' and ev("document.querySelector('#readScreen .rd-mic').disabled"), 'recording: stop button, mic disabled')
    ok(ev("micBusy()"), 'recording counts as microphone busy')
    ev("document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(150)
    ok(not ev("rd.recording") and ev("__played.length") == 1 and ev("rd.playing"), 'stopped: own recording plays')
    ok(ev("__tracksStopped") >= 1, 'microphone released after recording')
    pg.wait_for_timeout(1500)
    ok(any('корова' in x for x in ev("__spoken")) and not ev("rd.playing"), 'then the model plays')
    ok(ev("!!document.querySelector('#readScreen .rd-self')"), '"myself again" button appears')
    ls = ev("JSON.stringify(localStorage)")
    ok('blob:' not in ls, 'recording not in localStorage')
    ok('blob:' not in ev("JSON.stringify(Object.fromEntries(Object.keys(localStorage).filter(bkOwnKey).map(k=>[k,localStorage.getItem(k)])))"), 'recording not in backup data')
    ev("document.querySelector('#readScreen .rd-self').click()"); pg.wait_for_timeout(100)
    ok(ev("__played.length") == 2, 'play myself again')
    pg.wait_for_timeout(400)
    ev("rdSetChange('recSec',3); rdStartWord(0); __played.length=0"); pg.wait_for_timeout(100)
    ok(not ev("!!document.querySelector('#readScreen .rd-self')"), 'new word: old recording gone')
    ev("document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(3400)
    ok(not ev("rd.recording") and ev("__played.length") == 1, 'recording stops by itself after 3 s')
    pg.wait_for_timeout(1500)
    ev("window.__gum='deny'; document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(200)
    ok('Нет доступа к микрофону' in ev("document.querySelector('#readScreen .rd-recmsg').textContent"), 'denied: message')
    ev("window.__gum='ok'; window.__MR=window.MediaRecorder; window.MediaRecorder=undefined; document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(200)
    ok('не поддерживается' in ev("document.querySelector('#readScreen .rd-recmsg').textContent"), 'no MediaRecorder: message')
    ev("window.MediaRecorder=window.__MR; 0")
    # уход из режима во время записи
    ev("__tracksStopped=0; document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(150)
    ev("goHome()"); pg.wait_for_timeout(150)
    ok(not ev("rd.recording") and ev("__tracksStopped") >= 1 and ev("rd.rec") is None, 'leaving the mode stops recording and drops it')
    # нельзя записывать во время распознавания
    ev("startMode('read'); rdStartWord(0); window.__srLive=1"); pg.wait_for_timeout(200)
    ev("rd.listening=true; rdSyncBtns()")
    ok(ev("document.querySelector('#readScreen .rd-rec').disabled"), 'record disabled while listening')
    ev("rd.listening=false; rdSyncBtns(); window.__srLive=0")
    # ===== таймер: перерыв ждёт запись
    ev("document.getElementById('timerEnabled').checked=true; toggleTimerFeature(); document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(150)
    ev("timerSecondsLeft=1"); pg.wait_for_timeout(1300)
    ok(ev("restPending") and ev("document.getElementById('restOverlay').classList.contains('hidden')"), 'rest waits while recording')
    ev("document.querySelector('#readScreen .rd-rec').click()"); pg.wait_for_timeout(4000)
    ok(ev("timerMode") == 'rest' and not ev("document.getElementById('restOverlay').classList.contains('hidden')"), 'rest starts after playback')
    ev("skipRest(); document.getElementById('timerEnabled').checked=false; toggleTimerFeature()")
    # ===== мостики
    ev("goHome(); startMode('listen')"); pg.wait_for_timeout(300)
    w0 = ev("train.clean")
    ev("__srQueue.push({alts:['абракадабра']}); trainMic()"); pg.wait_for_timeout(400)
    ok(ev("!!document.querySelector('#listenScreen .rd-bridge')"), 'listening: bridge after a failed try')
    ev("document.querySelector('#listenScreen .rd-bridge').click()"); pg.wait_for_timeout(300)
    ok(ev("screenName") == 'read' and ev("rd.view") == 'do' and ev("rdCur().w") == w0.lower() and ev("rd.from") == 'listen', 'bridge opens the word in reading mode')
    ok(ev("document.querySelector('#readScreen .rd-back').textContent") == '← Назад', 'back button says Back')
    ev("appBack()"); pg.wait_for_timeout(200)
    ok(ev("screenName") == 'listen' and ev("train.clean") == w0 and ev("!!document.querySelector('#listenScreen #trainMicBtn')"), 'Back returns to listening with the same word')
    ev("goHome(); startMode('full')"); pg.wait_for_timeout(300)
    ev("__srQueue.push({alts:['абракадабра']}); toggleRecording()"); pg.wait_for_timeout(500)
    ok(ev("!!document.querySelector('#speechResultBox .rd-bridge')"), 'full trainer: bridge after a wrong answer')
    tw = ev("targetWordClean")
    ev("document.querySelector('#speechResultBox .rd-bridge').click()"); pg.wait_for_timeout(300)
    ok(ev("screenName") == 'read' and ev("rdCur().w") == tw.lower(), 'bridge from the full trainer')
    ev("rdBack()"); pg.wait_for_timeout(200)
    ok(ev("screenName") == 'full', 'back to the full trainer')
    # ===== предложения из статистики и статистика режима
    ev("goHome(); const s=loadStats(); s.ru=s.ru||{words:{},conf:{}}; s.ru.modes=s.ru.modes||{}; s.ru.modes.listen={words:{'лошадь':{ok:0,bad:3},'дом':{ok:5,bad:0}},conf:{},days:{}}; saveStats(s); startMode('read'); rd.view='list'; rd.sugOpen=true; rdRender()"); pg.wait_for_timeout(200)
    chips = ev("[...document.querySelectorAll('#readScreen .ph-chip')].map(b=>b.textContent)")
    ok('➕ лошадь' in chips and '➕ дом' not in chips, 'suggestions from listening mistakes: ' + str(chips))
    ev("[...document.querySelectorAll('#readScreen .ph-chip')].find(b=>b.textContent==='➕ лошадь').click()"); pg.wait_for_timeout(150)
    ok(ev("rd.list.some(x=>x.w==='лошадь')"), 'suggestion added')
    ok(ev("Object.keys(((loadStats().ru.modes||{}).read||{}).days||{}).length") >= 1, 'attempts recorded in read statistics')
    ev("openStats(); statsTab='read'; renderStatsPanel()"); pg.wait_for_timeout(150)
    ok('📖 Читаю вслух' in ev("document.getElementById('statsOverlay').textContent"), 'statistics tab')
    ev("closeStats()")
    # ===== подсказка при бездействии
    ev("ihSec=()=>0.3; rd.list=[]; rdSave(); rdAdd('корова'); rdStartWord(0); __spoken.length=0; ihNewTask()"); pg.wait_for_timeout(1500)
    ok(ev("!!document.querySelector('#readScreen .rd-mic.ih-pulse')"), 'idle hint pulses the mic button')
    ok(not any('корова' in x for x in ev("__spoken")), 'idle hint on reading steps does not play the word')
    ev("ihSec=()=>0; ihNewTask(); localStorage.removeItem('sr.hint.sec')")
    # ===== обучение и справка
    ev("rd.list=[]; rdSave(); rd.view='list'; rdRender(); tourStart('read')"); pg.wait_for_timeout(300)
    ok(ev("TOUR.active") and ev("TOUR.el && TOUR.el.classList.contains('ph-addrow')"), 'tutorial step 1 on the list')
    ev("tourEnd()")
    ev("rdAdd('корова'); rd.view='list'; rdRender(); tourStart('read')"); pg.wait_for_timeout(300)
    ev("tourStep(1)"); pg.wait_for_timeout(200)
    ev("document.querySelector('#readScreen .rd-start').click()"); pg.wait_for_timeout(700)
    ok(ev("rd.view") == 'do' and ev("TOUR.el && TOUR.el.classList.contains('rd-show')"), 'tutorial goes into training: syllables step')
    ev("tourEnd()")
    ok(ev("['ru','uk','en'].every(l=>helpParse(l).keysOk)"), 'help keys match items in all languages')
    ok(ev("['ru','uk','en'].every(l=>/📖/.test(helpParse(l).items.find(i=>i.key==='m_read').title) && /📖/.test(helpParse(l).items.find(i=>i.key==='s_read').title) && /👂/.test(helpParse(l).items.find(i=>i.key==='m_listen').title))"), 'help keys point to the right items')
    ev("openHelp()"); pg.wait_for_timeout(200)
    ht = ev("document.getElementById('helpOverlay').textContent")
    ok('📖 Читаю вслух' in ht and 'Настройки «Читаю вслух»' in ht and 'Вся справка' in ht, 'mode help shows reading items')
    ev("closeHelp()")
    # ===== «Назад» и язык
    ev("rdStartWord(0)"); pg.wait_for_timeout(100)
    ev("appBack()"); ok(ev("rd.view") == 'list', 'Back: training -> list')
    ev("appBack()"); ok(ev("screenName") == 'select', 'Back: list -> home')
    ev("localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ev("startMode('read')"); pg.wait_for_timeout(200)
    ok(ev("rd.list.length") == 0 and '📖 Читаю вголос' in ev("document.getElementById('readScreen').textContent"), 'uk: own list, uk texts')
    ev("rdAdd('корова'); rdStartWord(0)"); pg.wait_for_timeout(200)
    ok('Сходинка 1 з 4' in ev("document.getElementById('readScreen').textContent"), 'uk stage text')
    ok(ev("JSON.parse(localStorage.getItem('sr.read.ru')||'[]').length") >= 1, 'ru list kept')
    ok(not errs, 'no page errors: ' + str(errs))
    ctx.close()

    # ===== вёрстка: маленькие экраны и крупный шрифт (360 / 1.15 / 1.3 / 1.5), три языка
    GEO = r"""(() => {
      const vw = document.documentElement.clientWidth, out = [];
      document.querySelectorAll('#readScreen button, #readScreen input, #readScreen .step-title, #readScreen .step-note, #readScreen .ph-score').forEach(e => {
        if (!e.offsetParent) return;
        const r = e.getBoundingClientRect();
        if (r.right > vw + 1 || r.left < -1) out.push('OUT ' + e.className + ' ' + Math.round(r.right));
        if (e.tagName === 'BUTTON' && e.scrollWidth > e.clientWidth + 2) out.push('TEXT ' + e.className + ' «' + e.textContent.slice(0, 20) + '»');
        if (e.tagName === 'BUTTON' && r.height < 40 && !e.closest('.joined')) out.push('SMALL ' + e.className + ' h=' + Math.round(r.height));
      });
      if (document.documentElement.scrollWidth > vw + 1) out.push('HSCROLL');
      return out;
    })()"""
    WORDS = {'ru': 'достопримечательность', 'uk': 'відповідальність', 'en': 'responsibility'}
    for lang in ['ru', 'uk', 'en']:
        for z in (1.0, 1.15, 1.3, 1.5):
            W, H = round(360 / z), round(640 / z)
            c2 = b.new_context(viewport={'width': W, 'height': H})
            c2.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
            c2.add_init_script(MOCK); c2.add_init_script(REC)
            p2 = c2.new_page(); p2.goto(URL); p2.wait_for_timeout(300)
            lw = WORDS[lang]
            p2.evaluate(f"localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('sr.read.{lang}', JSON.stringify([{{w:'{lw}',s:1,k:1,d:['2026-11-01'],done:0}},{{w:'дом',s:1,k:0,d:[],done:1}}]))"); p2.reload(); p2.wait_for_timeout(500)
            tag = f'{lang} {W}x{H}'
            scenes = [
              ('list', "startMode('read'); rd.sugOpen=true; rd.doneOpen=true; rd.msg=rdT().exists; rdRender()"),
              ('stage1', "rdStartWord(0)"),
              ('result', "rd.prev={s:1,k:0,d:[],done:0,revealed:false}; rd.res={ok:false, heard:'" + lw[:-2] + "', bad:[0,2], fixed:false}; rdRender()"),
              ('stage2', "rdCur().s=2; rdStartWord(0)"),
              ('stage3done', "rdCur().s=3; rdStartWord(0); rd.stageNext=true; rd.stageMsg=rdT().stageDone; rd.res={ok:true,heard:'" + lw + "',bad:[],fixed:false}; rdRender()"),
              ('stage4', "rdCur().s=4; rdStartWord(0)"),
              ('rec', "rd.rec='blob:x'; rd.recording=true; rd.recMsg=ex().ownRecording; rdRender()"),
              ('done', "rd.recording=false; rd.done='day'; rdRender()"),
            ]
            for name, js in scenes:
                p2.evaluate(js); p2.wait_for_timeout(250)
                g = p2.evaluate(GEO)
                ok(not g, f'{tag} {name}: layout ' + str(g[:4]))
                if name in ('stage2', 'stage3done'):
                    one = p2.evaluate("(()=>{const wd=document.querySelector('#readScreen .rd-show .rd-word.joined'); if(!wd) return 'none'; const s=wd.querySelector('.rd-syl'); return [wd.offsetHeight <= s.offsetHeight*1.4, parseFloat(s.style.fontSize||getComputedStyle(s).fontSize)]})()")
                    ok(one == 'none' or one[0] or one[1] <= 20, f'{tag} {name}: whole word on one line (or smallest font) ' + str(one))
                if name == 'stage1':
                    mic = p2.evaluate("(()=>{const r=document.querySelector('#readScreen .rd-mic').getBoundingClientRect(); return [r.top, r.bottom, innerHeight]})()")
                    ok(mic[1] <= mic[2] + 1, f'{tag} stage1: mic button visible without scrolling ' + str(mic))
            c2.close()
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
