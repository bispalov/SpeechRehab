# Тесты режима «💬 Фразы на слух» (v89)
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
Object.defineProperty(navigator, 'serviceWorker', {get(){return {register:()=>Promise.reject(new Error('blocked')), addEventListener(){}}}});
"""
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
window.Audio = function (src) { const a = { src, playbackRate: 1, play() { window.__played.push(src); setTimeout(() => { a.onended && a.onended(); }, 150); return Promise.resolve(); }, pause() {} }; return a; };
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
    ctx.add_init_script(MOCK); ctx.add_init_script(REC)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(400)
    ev = pg.evaluate
    def fresh(lang='ru', st=None):
        ev(f"localStorage.clear(); localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('app_timer_enabled','false')" + (f"; localStorage.setItem('sr.fph.set', JSON.stringify({json.dumps(st)}))" if st else ''))
        pg.reload(); pg.wait_for_timeout(500)
    def settle():
        for _ in range(40):
            if not ev("!!(fp.cur && fp.cur.trans)"): break
            pg.wait_for_timeout(100)
        pg.wait_for_timeout(150)
    def say(alt, wait=True, sel='#fphScreen .fp-mic'):
        ev(f"__srQueue.push({{alts:[{alt!r}]}}); document.querySelector({sel!r}).click()"); pg.wait_for_timeout(400)
        if wait: settle()
    def setp(t, c='eat', alt=None, yn=None):
        it = {'t': t, 'c': c, 'alt': alt or []}
        if yn is not None: it['yn'] = yn
        ev(f"fpStop(); fp.cur.it={json.dumps(it, ensure_ascii=False)}; fp.cur.t=fp.cur.it.t; fp.cur.opts=null; fp.cur.rec=null; fpRender()")

    fresh(st={'sess': 0})
    # ===== стартовый экран и настройки
    order = ev("[...document.querySelectorAll('#modeSelect .mode-card[data-m]')].map(c=>c.dataset.m)")
    ok(order.index('fph') == order.index('num') + 1, 'card after Numbers by ear: ' + str(order))
    ok(ev("document.getElementById('modeFphTitle').textContent") == '💬 Фразы на слух', 'title ru')
    ok(ev("HOME_MODES.includes('fph') && STAT_TABS.includes('fph') && SETT_FOR.fph === 'fph'"), 'registered: home, stats tab, settings group')
    ev("openSettings(); settShow('fph')"); pg.wait_for_timeout(150)
    ok(ev("document.querySelectorAll('#fpSettBox select').length") == 9 and ev("document.querySelectorAll('#fpSettBox input[type=checkbox]').length") == 8, 'settings: 9 selects, 8 checkboxes')
    ok(ev("document.getElementById('sgt_fph').textContent") == '💬 Фразы на слух', 'settings group title')
    ev("closeSettings()")
    # ===== банк фраз
    for L in ('ru', 'uk', 'en'):
        ok(ev(f"FP_BANK.{L}.length") == 33 and ev(f"FP_YN.{L}.length") == 20, f'{L}: 33 phrases, 20 yes/no questions')
        ok(ev(f"FP_BANK.{L}.every(x => x[2].length >= 2 && x[2].every(a => fpKey(a) !== fpKey(x[1])))"), f'{L}: every phrase has 2 different similar options')
        ok(ev(f"new Set(FP_BANK.{L}.map(x => fpKey(x[1]))).size === FP_BANK.{L}.length"), f'{L}: no duplicate phrases')
        ok(ev(f"FP_BANK.{L}.every(x => FP_CATS.{L}[x[0]])"), f'{L}: every phrase has a topic name')
    ok(ev("fpYN('да конечно')") == 1 and ev("fpYN('Нет.')") == 0 and ev("fpYN('собака')") is None, 'yes/no parse ru')
    ev("currentLang='en'"); ok(ev("fpYN('Yes')") == 1 and ev("fpYN('no it is not')") == 0, 'yes/no parse en'); ev("currentLang='ru'")
    # ===== повторить голосом: верно с первого раза
    ev("startMode('fph')"); pg.wait_for_timeout(900)
    ok(ev("!!fp.cur") and ev("fp.cur.phase") == 'ear' and ev("!!document.querySelector('#fphScreen .fp-hidden')") and not ev("!!document.querySelector('#fphScreen .fp-words')"), 'phrase hidden on the ear step')
    ok(ev("__spoken.includes(fp.cur.t)"), 'phrase spoken at start')
    ok(ev("!!document.querySelector('#fphScreen .fp-topic')"), 'topic shown above')
    setp('Дай мне ложку', alt=['Дай мне ножку', 'Дай мне вилку'])
    i0 = ev("fp.i")
    say('дай мне ложку')
    ok(ev("fp.cur.phase") == 'done' and ev("fp.firstOk") == 1 and ev("!!document.querySelector('#fphScreen .fp-words')"), 'correct first time: done, phrase shown')
    pg.wait_for_timeout(2600)
    ok(ev("fp.i") == i0 + 1 and ev("fp.cur.phase") == 'ear', 'auto next phrase')
    sp = ev("__spoken"); k = max(i for i, x in enumerate(sp) if x == 'Верно!')
    ok(sp[k + 1] == 'Следующая фраза.' and ev("fp.cur.t") in sp[k + 2:], 'praise, then "Next phrase", then the phrase: ' + str(sp[k:k + 3]))
    # ===== ошибка: выделение слова, было/послышалось, чтение, снова на слух
    setp('Дай мне ложку'); ev("__spoken.length=0")
    say('дай мне ножку')
    ok(ev("fp.cur.phase") == 'read', 'mistake: read step')
    bad = ev("[...document.querySelectorAll('#fphScreen .fp-words.main .fp-w.bad')].map(e=>e.textContent)")
    ok(bad == ['ложку'], 'misheard word marked: ' + str(bad))
    ok(ev("document.querySelector('#fphScreen .fp-heardbox').textContent") == 'дай мне ножку' and not ev("!!document.querySelector('#fphScreen .fp-words.cmp')"), 'heard phrase shown (the phrase itself is above)')
    pg.wait_for_timeout(3000)
    sp = ev("__spoken")
    ok('Было:' in sp and 'Послышалось:' in sp and 'Дай мне ложку' in sp and 'дай мне ножку' in sp, 'both phrases spoken: ' + str(sp))
    ok(ev("Object.keys(fp.sessConf)") == ['ложку → ножку'], 'confusion recorded for the summary')
    ok(ev("JSON.parse(localStorage.getItem('sr.misslog')).slice(-1)[0].m") == 'fph', 'rejected answer in the log')
    ok(ev("((loadStats().ru.modes||{}).fph||{}).words['дай мне ложку'].bad") == 1, 'mode statistics: mistake counted')
    ev("__spoken.length=0; document.querySelector('#fphScreen .fp-words.main .fp-w').click()"); pg.wait_for_timeout(150)
    ok(ev("__spoken") == ['Дай'], 'tap a word: it is spoken')
    say('дай мне ложку', wait=False)
    ok(ev("fp.cur.trans") and not ev("!!document.querySelector('#fphScreen .fp-mic')"), 'read correctly: praise, no answer button during the pause')
    settle(); pg.wait_for_timeout(1300)
    ok(ev("fp.cur.phase") == 'ear2' and ev("!!document.querySelector('#fphScreen .fp-hidden')"), 'then hidden again, by ear')
    ok('Теперь послушайте и повторите.' in ev("__spoken"), 'prompt before the phrase')
    say('дай мне ложку')
    ok(ev("fp.cur.phase") == 'done' and ev("fp.firstOk") == 1, 'by ear after reading: done, first-time count unchanged')
    # ===== «Я сказал(а) верно»
    ev("fpNext()"); pg.wait_for_timeout(300); setp('Закрой окно', 'home')
    say('открой окно')
    ok(ev("!!document.querySelector('#fphScreen .fp-countok')"), 'count-ok button after a voice mistake')
    ev("document.querySelector('#fphScreen .fp-countok').click()"); pg.wait_for_timeout(300)
    ok(ev("fp.cur.phase") == 'done' and ev("fp.cur.first") is True, 'count-ok on the ear step: done, counts as first time')
    ok(ev("JSON.parse(localStorage.getItem('sr.misslog')).slice(-1)[0].fix") == 1, 'log entry marked as fixed')
    # ===== ошибка распознавания: без петли
    ev("fpNext()"); pg.wait_for_timeout(300); setp('Где ключи?', 'home')
    ev("__srQueue.push({error:'no-speech'}); document.querySelector('#fphScreen .fp-mic').click()"); pg.wait_for_timeout(400)
    ok(ev("fp.cur.phase") == 'ear' and ev("!!(fp.cur.res && fp.cur.res.err)") and not ev("fp.listening"), 'recognition error: message, stays on the ear step')
    # ===== выбор из вариантов
    ev("fpSetChange('task','choose')"); pg.wait_for_timeout(400)
    setp('Хочешь пить?', alt=['Хочешь петь?', 'Хочешь спать?'])
    opts = ev("[...document.querySelectorAll('#fphScreen .fp-choice')].map(e=>e.textContent)")
    ok(len(opts) == 3 and 'Хочешь пить?' in opts and 'Хочешь петь?' in opts, 'choose: 3 options with the similar one: ' + str(opts))
    ok(not ev("!!document.querySelector('#fphScreen .fp-mic')"), 'choose: no microphone on the ear step')
    ev("[...document.querySelectorAll('#fphScreen .fp-choice')].find(e=>e.textContent==='Хочешь петь?').click()"); pg.wait_for_timeout(300)
    ok(ev("fp.cur.phase") == 'read' and ev("[...document.querySelectorAll('#fphScreen .fp-words.main .fp-w.bad')].map(e=>e.textContent)") == ['пить'], 'wrong choice: read step, word marked')
    ok(ev("!!document.querySelector('#fphScreen .fp-readdone')"), 'choose: "I read it aloud" button on the read step')
    ev("document.querySelector('#fphScreen .fp-readdone').click()"); pg.wait_for_timeout(300)
    ok(ev("fp.cur.phase") == 'ear2' and ev("document.querySelectorAll('#fphScreen .fp-choice').length") == 3, 'read done: choose again by ear')
    ev("[...document.querySelectorAll('#fphScreen .fp-choice')].find(e=>e.textContent==='Хочешь пить?').click()"); pg.wait_for_timeout(300)
    ok(ev("fp.cur.phase") == 'done', 'right choice: done')
    ev("fpSetChange('opts',4)"); ev("fpNext()"); pg.wait_for_timeout(300); setp('Сейчас обед', 'time', alt=['Сейчас ответ', 'Сейчас рассвет'])
    ok(ev("document.querySelectorAll('#fphScreen .fp-choice').length") == 4, 'choose: 4 options when set')
    # ===== да / нет
    ev("fpSetChange('task','yesno')"); pg.wait_for_timeout(400)
    ok(ev("fp.cur.it.c") == 'q' and ev("document.querySelectorAll('#fphScreen .fp-yn .fp-choice').length") == 2, 'yes/no: question with two buttons')
    setp('Снег белый?', 'q', yn=1)
    ev("document.querySelector('#fphScreen .fp-choice.no').click()"); pg.wait_for_timeout(300)
    ok(ev("fp.cur.phase") == 'read' and 'Да' in ev("document.querySelector('#fphScreen .fp-answer').textContent"), 'wrong yes/no: question shown with the right answer')
    ev("document.querySelector('#fphScreen .fp-readdone').click()"); pg.wait_for_timeout(300)
    say('да', sel='#fphScreen .fp-micyn')
    ok(ev("fp.cur.phase") == 'done', 'yes/no answered by voice')
    ev("fpSetChange('task','rep')"); pg.wait_for_timeout(300)
    # ===== свои фразы
    ev("fpStop(); fp.view='list'; fp.msg=''; fpRender()"); pg.wait_for_timeout(200)
    ok(ev("!!document.getElementById('fpInput')") and 'входят в «💾 Сохранить копию данных»' in ev("document.querySelector('#fphScreen .fp-recnote').textContent"), 'list: input and backup note')
    ev("const i=document.getElementById('fpInput'); i.value='Пора пить чай'; document.querySelector('#fphScreen .fp-add').click()"); pg.wait_for_timeout(200)
    ok(ev("fpOwnLoad()") == ['Пора пить чай'], 'own phrase added')
    ev("const i=document.getElementById('fpInput'); i.value='пора  пить чай'; document.querySelector('#fphScreen .fp-add').click()"); pg.wait_for_timeout(200)
    ok(ev("fpOwnLoad().length") == 1 and ev("document.querySelector('#fphScreen .fp-msg').textContent") == 'Такая фраза уже есть.', 'duplicate rejected')
    ok(ev("fpOwnAdd('Дай мне ложку')") == 'Такая фраза уже есть.', 'bank phrase is a duplicate too')
    ok(ev("fpOwnAdd('')") != '' and ev("fpOwnAdd('а б в г д е ж з и к л')") != '', 'empty and too long rejected')
    ev("localStorage.setItem('sr.phr.ru', JSON.stringify([{t:'Мне нужен врач'},{t:'Пора пить чай'}])); phr.loadedLang=null; fpRender()"); pg.wait_for_timeout(200)
    ev("document.querySelector('#fphScreen .fp-fromphr').click()"); pg.wait_for_timeout(200)
    ok(ev("fpOwnLoad()") == ['Пора пить чай', 'Мне нужен врач'], 'imported from My phrases without duplicates')
    ok(ev("document.querySelectorAll('#fphScreen .fp-row').length") == 2 + 33, 'rows: 2 own + 33 common')
    # ===== запись голоса в IndexedDB
    ev("document.querySelector('#fphScreen .fp-row .fp-rec').click()"); pg.wait_for_timeout(300)
    ok(ev("__recStarted") == 1 and ev("!!fp.mr") and ev("micBusy()"), 'recording started')
    ok(ev("document.querySelector('#fphScreen .fp-row .fp-rec').textContent") == '⏹ Стоп', 'stop button shown')
    ev("document.querySelector('#fphScreen .fp-row .fp-rec').click()"); pg.wait_for_timeout(700)
    ok(ev("!fp.mr") and ev("__tracksStopped") >= 1, 'recording stopped, microphone released')
    ok(ev("fpRecIndex().then(x => Object.keys(x.keys))") == ['пора пить чай'], 'saved in IndexedDB under the phrase key')
    ok(ev("fpRecIndex().then(x => x.bytes)") == 4000, 'size counted')
    ok('Записей голоса: 1, около 4 КБ.' == ev("document.querySelector('#fphScreen .fp-used').textContent"), 'usage line shown')
    ok(ev("document.querySelector('#fphScreen .fp-row .fp-say').classList.contains('fp-has')") and ev("getComputedStyle(document.querySelector('#fphScreen .fp-row .fp-recplay')).display") != 'none', 'row shows recorded state and play button')
    ok(not ev("localStorage.getItem('sr.fph.my.ru')").count('blob') and all(not k.startswith('sr-voice') for k in ev("Object.keys(localStorage)")), 'recording not in localStorage')
    # тренировка этой фразы: звучит запись, а не синтезатор
    ev("fpSetChange('src','own'); fp.view='do'; fp.pool=null; fpNext()"); pg.wait_for_timeout(300)
    ev("fpStop(); fp.cur.it={t:'Пора пить чай',c:'own',alt:[]}; fp.cur.t='Пора пить чай'; fp.cur.rec=null; fpRender(); __played.length=0; __spoken.length=0; fpSpeak(false)"); pg.wait_for_timeout(600)
    ok(len(ev("__played")) == 1 and 'Пора пить чай' not in ev("__spoken"), 'recorded voice played instead of the synthesiser')
    ev("fpSetChange('voice',0); __played.length=0; __spoken.length=0; fpSpeak(false)"); pg.wait_for_timeout(400)
    ok(len(ev("__played")) == 0 and 'Пора пить чай' in ev("__spoken"), 'voice setting off: synthesiser')
    ev("fpSetChange('voice',1); fpSetChange('words',1); fp.cur.rec=null; __spoken.length=0")
    ev("fpRecDel('Пора пить чай')"); pg.wait_for_timeout(200)
    ev("fp.cur.rec=null; fpSpeak(true)"); pg.wait_for_timeout(1800)
    ok(ev("__spoken") == ['Пора', 'пить', 'чай'], 'slowly: word by word with pauses: ' + str(ev("__spoken")))
    # удаление своей фразы удаляет и запись
    ev("fp.view='list'; fpRender()"); pg.wait_for_timeout(200)
    ev("document.querySelector('#fphScreen .fp-row .fp-rec').click()"); pg.wait_for_timeout(200); ev("document.querySelector('#fphScreen .fp-row .fp-rec').click()"); pg.wait_for_timeout(600)
    ev("document.querySelector('#fphScreen .fp-row .fp-del').click()"); pg.wait_for_timeout(400)
    ok(ev("fpOwnLoad()") == ['Мне нужен врач'] and ev("fpRecIndex().then(x => Object.keys(x.keys).length)") == 0, 'own phrase and its recording removed')
    ev("fpSetChange('src','all'); fp.view='do'; fpRender()")
    # ===== настройки: длина, тема, кнопка «Послушать»
    ev("fpSetChange('len','short'); fp.pool=null")
    ok(ev("fpPool().every(x => phrWords(x.t).length <= 3)"), 'short phrases only')
    ev("fpSetChange('len','all'); fpSetChange('cat','health'); fp.pool=null")
    ok(ev("fpPool().every(x => x.c === 'health')"), 'topic filter')
    ev("fpSetChange('cat','all'); fpSetChange('topic',0); fpNext()"); pg.wait_for_timeout(300)
    ok(not ev("!!document.querySelector('#fphScreen .fp-topic')"), 'topic hidden when off')
    ev("fpSetChange('topic',1); fpSetChange('tap',1); __spoken.length=0; fpNext()"); pg.wait_for_timeout(900)
    ok(ev("!!document.querySelector('#fphScreen .fp-play')") and ev("fp.cur.t") not in ev("__spoken") and 'Нажмите «Послушать фразу».' in ev("__spoken"), 'tap setting: phrase waits for the button')
    ev("document.querySelector('#fphScreen .fp-play').click()"); pg.wait_for_timeout(300)
    ok(ev("fp.cur.t") in ev("__spoken"), 'phrase spoken after the tap')
    ev("fpSetChange('tap',0)")
    # ===== микрофон сам
    ev("fpSetChange('autoMic',1); __srQueue.push('hold'); fpNext()"); pg.wait_for_timeout(1200)
    ok(ev("fp.listening"), 'autoMic: microphone on after the phrase')
    ev("stopModeRec(); fpSetChange('autoMic',0)"); pg.wait_for_timeout(300)
    # ===== итог занятия
    ev("fpSetChange('sess',10); fp.i=10; fp.firstOk=7; fp.sessConf={'ложку → ножку':2}; fpNext()"); pg.wait_for_timeout(300)
    t = ev("document.getElementById('fphScreen').textContent")
    ok('Занятие закончено' in t and 'С первого раза: 7 из 10' in t and 'ложку → ножку (2)' in t, 'session summary')
    # ===== статистика, справка, обучение
    ev("goHome(); openStats ? openStats() : 0"); pg.wait_for_timeout(200)
    ok(ev("statTabName('fph')") == '💬 Фразы на слух', 'stats tab name')
    ok(ev("HELP_KEYS.length") == 47 and ev("helpParse('ru').items.length") == 47 and ev("helpParse('uk').items.length") == 47 and ev("helpParse('en').items.length") == 47, 'help: 47 items in every language')
    ok(ev("TOUR_STEPS.fph.length") == 4 and ev("['ru','uk','en'].every(l => [1,2,3,4].every(i => TOUR_T[l]['fph'+i]))"), 'tutorial: 4 steps in 3 languages')
    # ===== язык
    ev("closeStats && closeStats(); localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ok(ev("document.getElementById('modeFphTitle').textContent") == '💬 Фрази на слух', 'uk title')
    ev("startMode('fph')"); pg.wait_for_timeout(400); setp('Дай мені ложку', alt=['Дай мені ніжку', 'Дай мені виделку'])
    say('дай мені ніжку')
    ok(ev("[...document.querySelectorAll('#fphScreen .fp-words.main .fp-w.bad')].map(e=>e.textContent)") == ['ложку'], 'uk: misheard word marked')
    ok(not errs, 'no page errors: ' + str(errs))
    ctx.close()
    # ===== записи голоса в копии данных (v90)
    import tempfile
    TMP = tempfile.mkdtemp() + '/'
    c4 = b.new_context(viewport={'width': 360, 'height': 740}, accept_downloads=True)
    c4.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    c4.add_init_script(MOCK); c4.add_init_script(REC)
    p4 = c4.new_page(); e4 = []; p4.on('pageerror', lambda e: e4.append(str(e))); p4.on('dialog', lambda d: d.accept())
    p4.goto(URL); p4.wait_for_timeout(300)
    p4.evaluate("localStorage.clear(); localStorage.setItem('app_lang','ru'); localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('sr.fph.my.ru', JSON.stringify(['Пора пить чай']))"); p4.reload(); p4.wait_for_timeout(400)
    p4.evaluate("fpRecPut('Пора пить чай', new Blob([new Uint8Array([1,2,3,250,251,252,0,7])], {type:'audio/webm'})).then(()=>{ currentLang='uk'; return fpRecPut('Дай мені ложку', new Blob([new Uint8Array(3000)], {type:'audio/ogg'})); }).then(()=>{ currentLang='ru'; })"); p4.wait_for_timeout(200)
    p4.evaluate("openSettings(); settShow('data')"); p4.wait_for_timeout(200)
    with p4.expect_download() as dl: p4.evaluate("document.getElementById('bkSaveBtn').click()")
    path = TMP + dl.value.suggested_filename; dl.value.save_as(path)
    obj = json.load(open(path, encoding='utf-8'))
    ok(sorted(x['k'] for x in obj.get('voice', [])) == ['ru|пора пить чай', 'uk|дай мені ложку'], 'backup: recordings of all languages saved: ' + str([x['k'] for x in obj.get('voice', [])]))
    ok(all(x['a'].startswith('data:audio/') for x in obj['voice']), 'backup: recordings as data: strings')
    ok('sr.fph.my.ru' in obj['data'], 'backup: own phrases saved')
    p4.wait_for_timeout(200)
    ok('записей голоса: 2' in p4.evaluate("document.getElementById('bkStatus').textContent"), 'status mentions recordings')
    # удалить всё и восстановить
    p4.evaluate("fpRecReplaceAll([]); localStorage.removeItem('sr.fph.my.ru')"); p4.wait_for_timeout(200)
    ok(p4.evaluate("fpRecAll().then(a=>a.length)") == 0, 'recordings cleared before restore')
    with p4.expect_navigation(timeout=5000):
        p4.set_input_files('#bkFile', path)
    p4.wait_for_timeout(700)
    got = p4.evaluate("fpRecAll().then(a=>Promise.all(a.map(([k,b])=>b.arrayBuffer().then(x=>[k,b.type,Array.from(new Uint8Array(x)).slice(0,8),b.size]))))")
    got = sorted(got)
    ok([g[0] for g in got] == ['ru|пора пить чай', 'uk|дай мені ложку'], 'restore: recordings back: ' + str([g[0] for g in got]))
    ok(got[0][2] == [1, 2, 3, 250, 251, 252, 0, 7] and got[0][1] == 'audio/webm' and got[1][3] == 3000 and got[1][1] == 'audio/ogg', 'restore: bytes and type identical')
    ok(p4.evaluate("localStorage.getItem('sr.fph.my.ru')") is not None, 'restore: own phrases back')
    # старая копия без записей не стирает текущие записи
    old = TMP + 'old.json'; o2 = dict(obj); o2.pop('voice'); json.dump(o2, open(old, 'w', encoding='utf-8'))
    with p4.expect_navigation(timeout=5000):
        p4.set_input_files('#bkFile', old)
    p4.wait_for_timeout(700)
    ok(p4.evaluate("fpRecAll().then(a=>a.length)") == 2, 'old backup without recordings keeps current recordings')
    # копия с пустым списком записей заменяет их
    emp = TMP + 'empty.json'; o3 = dict(obj); o3['voice'] = []; json.dump(o3, open(emp, 'w', encoding='utf-8'))
    with p4.expect_navigation(timeout=5000):
        p4.set_input_files('#bkFile', emp)
    p4.wait_for_timeout(700)
    ok(p4.evaluate("fpRecAll().then(a=>a.length)") == 0, 'backup with no recordings replaces them')
    # без записей сохранение работает как раньше
    p4.evaluate("openSettings(); settShow('data')"); p4.wait_for_timeout(200)
    with p4.expect_download() as dl: p4.evaluate("document.getElementById('bkSaveBtn').click()")
    p2_ = TMP + 'n.json'; dl.value.save_as(p2_)
    ok(json.load(open(p2_, encoding='utf-8')).get('voice') == [], 'no recordings: empty list')
    ok(not e4, 'no page errors (backup): ' + str(e4))
    c4.close()
    # ===== тёмная тема: выделенное слово без светлой плашки
    c3 = b.new_context(viewport={'width': 360, 'height': 740}); c3.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
    c3.add_init_script(MOCK); p3 = c3.new_page(); p3.goto(URL); p3.wait_for_timeout(300)
    p3.evaluate("localStorage.setItem('app_lang','ru'); localStorage.setItem('sr.tour.offer','0')"); p3.reload(); p3.wait_for_timeout(400)
    p3.evaluate("document.documentElement.setAttribute('data-theme','dark'); startMode('fph'); fpStop(); fp.cur.it={t:'Дай мне ложку',c:'eat',alt:[]}; fp.cur.t='Дай мне ложку'; fp.cur.phase='read'; fp.cur.need=1; fp.cur.res={ok:false, heard:'дай мне ножку', rows:phrCompare('Дай мне ложку',['дай мне ножку']).rows, viaVoice:true}; fpRender()")
    bg = p3.evaluate("(()=>{const b=document.querySelector('#fphScreen .fp-w.bad'); return getComputedStyle(b).backgroundColor.match(/[\\d.]+/g).map(Number)})()")
    lum = (0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]) * (bg[3] if len(bg) > 3 else 1)
    ok(lum < 60, 'dark theme: marked word without a light background ' + str(bg))
    c3.close()
    # ===== вёрстка: 360/313/277/240 × ru/uk/en
    GEO = r"""(() => {
      const vw = document.documentElement.clientWidth, out = [];
      document.querySelectorAll('#fphScreen *, #fpSettBox *').forEach(e => {
        if (!e.offsetParent) return;
        const r = e.getBoundingClientRect();
        if (r.right > vw + 1 || r.left < -1) out.push('OUT ' + e.className + ' ' + Math.round(r.right));
        if (e.tagName === 'BUTTON' && e.scrollWidth > e.clientWidth + 2) out.push('TEXT ' + e.className + ' «' + e.textContent.slice(0, 20) + '»');
        if (e.tagName === 'BUTTON' && r.height < 40) out.push('SMALL ' + e.className + ' ' + Math.round(r.height));
      });
      if (document.documentElement.scrollWidth > vw + 1) out.push('HSCROLL');
      return out;
    })()"""
    LONG = {'ru': 'Врач придёт в одиннадцать', 'uk': 'Лікар прийде об одинадцятій', 'en': 'Today we see the speech therapist'}
    for lang in ['ru', 'uk', 'en']:
        for z in (1.0, 1.15, 1.3, 1.5):
            W, Hh = round(360 / z), round(640 / z)
            c2 = b.new_context(viewport={'width': W, 'height': Hh})
            c2.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
            c2.add_init_script(MOCK); c2.add_init_script(REC)
            p2 = c2.new_page(); p2.goto(URL); p2.wait_for_timeout(300)
            p2.evaluate(f"localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('sr.fph.my.{lang}', JSON.stringify(['{LONG[lang]} и ещё немного слов']))"); p2.reload(); p2.wait_for_timeout(400)
            tag = f'{lang} {W}x{Hh}'
            L = LONG[lang]
            setit = f"fpStop(); fp.cur.it=(FP_BANK.{lang}.find(x=>x[1]==={L!r})||[])[1] ? {{t:{L!r},c:'health',alt:FP_BANK.{lang}.find(x=>x[1]==={L!r})[2]}} : {{t:{L!r},c:'health',alt:[]}}; fp.cur.t={L!r}; fp.cur.opts=null;"
            scenes = [
              ('ear', f"startMode('fph'); {setit} fpRender()"),
              ('read', f"{setit} fp.cur.phase='read'; fp.cur.need=2; fp.cur.res={{ok:false, heard:'xx yy zz длинное', rows:phrCompare({L!r},['что-то совсем другое']).rows, viaVoice:true}}; fpRender()"),
              ('choose', f"fpSetChange('task','choose'); fpSetChange('opts',4); fpNext(); {setit} fpRender()"),
              ('yesno', "fpSetChange('task','yesno'); fpNext(); fpStop(); fpRender()"),
              ('yesnoread', "fp.cur.phase='read'; fp.cur.need=1; fp.cur.res={ok:false, heard:'нет', yn:0, viaVoice:false}; fpRender()"),
              ('done', f"fpSetChange('task','rep'); fpSetChange('auto',0); fpNext(); {setit} fp.cur.phase='done'; fp.cur.res={{ok:true}}; fpRender()"),
              ('tap', "fpSetChange('tap',1); fpNext(); fpStop(); fpRender()"),
              ('summary', "fp.summary=true; fp.i=20; fp.firstOk=13; fp.sessConf={'ложку → ножку':3,'одиннадцать → тринадцать':2,'пить → петь':1}; fpRender()"),
              ('list', "fp.summary=false; fpSetChange('tap',0); fp.view='list'; fp.msg='Такая фраза уже есть.'; fpRender()"),
              ('settings', "openSettings(); settShow('fph')"),
            ]
            for name, js in scenes:
                p2.evaluate(js); p2.wait_for_timeout(250)
                g = p2.evaluate(GEO)
                ok(not g, f'{tag} {name}: layout ' + str(g[:4]))
                if name == 'ear':
                    m = p2.evaluate("(()=>{const r=document.querySelector('#fphScreen .fp-mic').getBoundingClientRect(); return r.bottom <= innerHeight + 1})()")
                    ok(m, f'{tag} ear: answer button visible')
                if name == 'yesno':
                    m = p2.evaluate("(()=>{const r=document.querySelector('#fphScreen .fp-choice.no').getBoundingClientRect(); return r.bottom <= innerHeight + 1})()")
                    ok(m, f'{tag} yesno: both buttons visible')
            c2.close()
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
sys.exit(1 if fails else 0)
