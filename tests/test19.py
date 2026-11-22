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
    def fresh(lang='ru', st=None):
        ev(f"localStorage.clear(); localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('app_timer_enabled','false')" + (f"; localStorage.setItem('sr.num.set', JSON.stringify({st}))" if st else ''))
        pg.reload(); pg.wait_for_timeout(500)
    def settle():
        for _ in range(40):
            if not ev("!!(nm.cur && nm.cur.trans)"): break
            pg.wait_for_timeout(100)
        pg.wait_for_timeout(150)
    def say(alt, wait=True):
        ev(f"__srQueue.push({{alts:[{alt!r}]}}); document.querySelector('#numScreen .nm-mic').click()"); pg.wait_for_timeout(400)
        if wait: settle()
    def setn(n, ctxp='null'):
        ev(f"nmStop(); nm.cur.n={n}; nm.cur.ctx={ctxp}; nm.cur.opts=null; nmRender()")
    fresh()
    # ===== стартовый экран, настройки
    order = ev("[...document.querySelectorAll('#modeSelect .mode-card[data-m]')].map(c=>c.dataset.m)")
    ok(order.index('num') == order.index('read') + 1, 'card after Reading aloud: ' + str(order))
    ok(ev("document.getElementById('modeNumTitle').textContent") == '🔟 Числа на слух', 'title')
    ev("openSettings(); settShow('num')"); pg.wait_for_timeout(150)
    ok(ev("document.querySelectorAll('#nmSettBox select').length") == 9 and ev("document.querySelectorAll('#nmSettBox input[type=checkbox]').length") == 5 and ev("document.querySelectorAll('#nmSettBox input[type=number]').length") == 2, 'settings: 9 selects, 5 checkboxes, from/to')
    ok(ev("getComputedStyle(document.getElementById('nmSetCustom')).display") == 'none', 'custom range hidden by default')
    ev("const s=document.getElementById('nmSetRange'); s.value='custom'; s.dispatchEvent(new Event('change'))")
    ok(ev("getComputedStyle(document.getElementById('nmSetCustom')).display") != 'none', 'custom range shown when chosen')
    ev("closeSettings(); localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== разбор услышанного
    cases = {'ru': [('13', 13), ('тринадцать', 13), ('Тринадцать.', 13), ('одиннадцать тринадцать', 11), ('двадцать один', 21), ('сто двадцать пять', 125), ('тысяча', 1000), ('автобус номер тринадцать', 13), ('девяносто девять', 99), ('ноль', 0), ('собака', None), ('две', 2)],
             'uk': [("п'ятнадцять", 15), ("дев'яносто дев'ять", 99), ('одинадцять', 11), ('двісті сорок', 240), ('тисяча', 1000), ('сорок 2', 2)],
             'en': [('thirteen', 13), ('thirty', 30), ('twenty-one', 21), ('one hundred twenty', 120), ('a hundred', 100), ('bus number fourteen', 14)]}
    for lang, cs in cases.items():
        ev(f"currentLang='{lang}'")
        for txt, want in cs:
            got = ev(f"nmParse({txt!r})")
            ok(got == want, f'{lang} parse {txt!r} -> {want} (got {got})')
    ev("currentLang='ru'")
    ok(ev("nmWords(11)") == 'одиннадцать' and ev("nmWords(1000)") == 'тысяча' and ev("nmWords(745)") == 'семьсот сорок пять', 'number words')
    ok('<span class="accent-char">и</span>' in ev("nmWordHtml(11)") and '<span class="accent-char">а</span>' in ev("nmWordHtml(13)"), 'stress marked: одИннадцать / тринАдцать')
    ok([ev(f"nmPlural({n}, ['год','года','лет'])") for n in (1, 2, 5, 11, 21, 22, 25)] == ['год', 'года', 'лет', 'лет', 'год', 'года', 'лет'], 'plural forms ru')
    # ===== голосом: верно с первого раза
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0})); startMode('num')"); pg.wait_for_timeout(700)
    ok(ev("!!nm.cur") and ev("nm.cur.phase") == 'ear' and ev("!!document.querySelector('#numScreen .nm-hidden')") and not ev("!!document.querySelector('#numScreen .nm-dig')"), 'number hidden on the ear step')
    ok(ev("__spoken.some(x => x === nmWords(nm.cur.n))"), 'number spoken at start')
    setn(11)
    i0 = ev("nm.i")
    say('11')
    ok(ev("nm.cur.phase") == 'done' and ev("nm.firstOk") == 1 and ev("!!document.querySelector('#numScreen .nm-dig')"), 'correct first time: done, number shown')
    pg.wait_for_timeout(2600)
    ok(ev("nm.i") == i0 + 1 and ev("nm.cur.phase") == 'ear', 'auto next number')
    sp = ev("__spoken"); k = max(i for i, x in enumerate(sp) if x == 'Верно!')
    ok(sp[k + 1:k + 3] == ['Следующее число.', ev("nmWords(nm.cur.n)")], 'praise, then "Next number", then the number: ' + str(sp[k:k + 3]))
    # ===== ошибка: сравнение, чтение, снова на слух
    setn(11); ev("__spoken.length=0")
    say('тринадцать')
    ok(ev("nm.cur.phase") == 'read' and ev("nm.cur.other") == 13, 'mistake: read step, other = heard 13')
    cmp = ev("[...document.querySelectorAll('#numScreen .nm-cmp .nm-dig')].map(e=>e.textContent)")
    ok(cmp == ['11', '13'], 'compare shows 11 and 13: ' + str(cmp))
    ok('Послышалось' in ev("document.querySelector('#numScreen .nm-cmp').textContent"), 'compare labels')
    pg.wait_for_timeout(3500)
    sp = ev("__spoken")
    ok('одиннадцать' in sp and 'тринадцать' in sp and any('Было' in x for x in sp) and any('Послышалось' in x for x in sp), 'both numbers spoken: ' + str(sp))
    ok(ev("((loadStats().ru.modes||{}).num||{}).conf['11>13']") == 1, 'confusion 11>13 in statistics')
    ok(ev("JSON.parse(localStorage.getItem('sr.misslog')).slice(-1)[0].m") == 'num', 'rejected answer in the log')
    ev("__spoken.length=0")
    say('одиннадцать', wait=False)
    ok(ev("nm.cur.phase") == 'read' and ev("nm.cur.trans") and not ev("!!document.querySelector('#numScreen .nm-mic')") and 'Верно' in ev("document.querySelector('#numScreen .nm-res').textContent"), 'read correctly: praise on the same screen, no answer button yet')
    pg.wait_for_timeout(700)
    ok(ev("nm.cur.trans") and 'одиннадцать' not in ev("__spoken"), 'pause after praise: number not spoken yet')
    settle(); pg.wait_for_timeout(1300)
    ok(ev("nm.cur.phase") == 'ear2' and ev("!!document.querySelector('#numScreen .nm-hidden')"), 'read correctly: hidden again, by ear')
    sp = ev("__spoken")
    ok(sp[:3] == ['Верно!', 'Теперь послушайте и повторите.', 'одиннадцать'], 'praise → prompt → number: ' + str(sp))
    ok('Теперь на слух.' in ev("document.querySelector('#numScreen .nm-phase').textContent"), 'title: Now by ear')
    ok(ev("!!document.querySelector('#numScreen .nm-mic.nm-cue')"), 'answer button flashes')
    say('11')
    ok(ev("nm.cur.phase") == 'done' and ev("nm.firstOk") == 1, 'by ear again: done, not counted as first time')
    # ошибка на слух после чтения — снова читать
    ev("nmNext()"); setn(14); say('40'); say('14')
    ok(ev("nm.cur.phase") == 'ear2', 'ear2 after reading')
    say('40')
    ok(ev("nm.cur.phase") == 'read', 'mistake by ear again: back to reading')
    # «Я сказал(а) верно»
    ev("nmNext()"); setn(12); f0 = ev("nm.firstOk"); say('20')
    ok(ev("!!document.querySelector('#numScreen .nm-countok')"), 'count-ok button after a voice mistake')
    ev("document.querySelector('#numScreen .nm-countok').click()"); pg.wait_for_timeout(200); settle()
    ok(ev("nm.cur.phase") == 'done' and ev("nm.firstOk") == f0 + 1 and ev("JSON.parse(localStorage.getItem('sr.misslog')).slice(-1)[0].fix") == 1, 'count-ok: done, first time, log marked')
    # повторы: прочитать 2 раза, на слух 2 раза
    ev("nmSetChange('read',2); nmSetChange('ear',2); nmSetChange('auto',0); nmNext()"); setn(15)
    say('50'); say('15')
    ok(ev("nm.cur.phase") == 'read' and ev("nm.cur.need") == 1, 'read twice: one more')
    say('15'); ok(ev("nm.cur.phase") == 'ear2' and ev("nm.cur.need") == 2, 'then by ear twice')
    say('15'); ok(ev("nm.cur.phase") == 'ear2' and ev("nm.cur.need") == 1, 'by ear: one more')
    say('15'); ok(ev("nm.cur.phase") == 'done' and ev("!!document.querySelector('#numScreen .nm-next.primary-btn')"), 'done; without auto — "Next number" button')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== «число звучит только по нажатию»
    ev("nmSetChange('tap',1); __spoken.length=0; nmNext()"); pg.wait_for_timeout(700)
    ok(ev("document.querySelector('#numScreen .nm-hidden.tap').textContent") == '▶ Послушать число', 'tap mode: "Hear the number" button')
    ok(ev("!__spoken.includes(nmWords(nm.cur.n))") and 'Нажмите «Послушать число».' in ev("__spoken"), 'tap mode: number not spoken by itself, prompt instead')
    ev("document.querySelector('#numScreen .nm-hidden.tap').click()"); pg.wait_for_timeout(300)
    ok(ev("__spoken.includes(nmWords(nm.cur.n))"), 'tap mode: number spoken after the tap')
    nn = ev("nm.cur.n"); say(str((nn + 1) % 21)); say(str(nn)); ev("__spoken.length=0"); pg.wait_for_timeout(300)
    ok(ev("nm.cur.phase") == 'ear2' and ev("!__spoken.includes(nmWords(nm.cur.n))"), 'tap mode after reading: waits for the tap')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== микрофон сам после числа
    ev("nmSetChange('autoMic',1); window.__srLive=0; nmNext()"); pg.wait_for_timeout(200)
    ev("__srQueue.push({alts:[String(nm.cur.n)]})"); pg.wait_for_timeout(900); settle()
    ok(ev("nm.cur.phase") == 'done' or ev("nm.firstOk") >= 1 and ev("nm.cur.first") is True, 'auto mic: answered without tapping the mic')
    # микрофон сам и на шаге «прочитать»: после объяснения ошибки и после «Верно!», если читать ещё раз
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0, autoMic:1, read:2, auto:0})); nmNext()"); pg.wait_for_timeout(200)
    ev("nmStop(); nm.cur.n=11; nmRender(); __spoken.length=0; __srQueue.push({alts:['13']}); document.querySelector('#numScreen .nm-mic').click()")
    pg.wait_for_timeout(600)
    ok(ev("nm.cur.phase") == 'read', 'auto mic: wrong answer → read')
    ev("__srQueue.push({alts:['11']}, {alts:['11']})")
    for _ in range(60):
        if ev("nm.cur.phase") == 'read' and ev("nm.cur.need") == 1: break
        pg.wait_for_timeout(100)
    ok(ev("nm.cur.phase") == 'read' and ev("nm.cur.need") == 1, 'auto mic after the explanation: first reading heard without a tap ' + str(ev("[nm.cur.phase, nm.cur.need]")))
    for _ in range(60):
        if ev("nm.cur.phase") != 'read': break
        pg.wait_for_timeout(100)
    ok('Прочитайте ещё раз.' in ev("__spoken"), 'after "Correct!" — prompt "Read it once more"')
    ok(ev("nm.cur.phase") in ('ear2', 'done'), 'second reading also without a tap: ' + str(ev("nm.cur.phase")))
    ev("nmStop(); __srQueue.length=0")
    # без «микрофон сам»: подсказка голосом и мигающая кнопка
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0, read:2, auto:0})); nmNext()"); pg.wait_for_timeout(200)
    ev("nmStop(); nm.cur.n=11; nmRender()"); say('13'); pg.wait_for_timeout(3500); say('11'); pg.wait_for_timeout(800)
    ok(ev("nm.cur.phase") == 'read' and not ev("nm.listening") and ev("!!document.querySelector('#numScreen .nm-mic.nm-cue')") and 'Прочитайте ещё раз.' in ev("__spoken"), 'without auto mic: prompt + flashing mic button')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0,auto:0}))"); ev("nmNext()"); pg.wait_for_timeout(900)
    ok(not ev("nm.listening"), 'auto mic off by default')
    ev("nmStop(); localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== выбор из кнопок
    ev("nmSetChange('answer','choice'); nmSetChange('opts',4); nmNext()"); setn(11)
    opts = ev("[...document.querySelectorAll('#numScreen .nm-choice')].map(b=>+b.textContent)")
    ok(len(opts) == 4 and 11 in opts and 13 in opts and len(set(opts)) == 4, 'choice: 4 buttons with 11 and the confused 13: ' + str(opts))
    ok('выберите' in ev("document.querySelector('#numScreen .nm-phase').textContent"), 'choice title')
    ev("[...document.querySelectorAll('#numScreen .nm-choice')].find(b=>b.textContent==='13').click()"); pg.wait_for_timeout(300); settle()
    ok(ev("nm.cur.phase") == 'read' and ev("!!document.querySelector('#numScreen .nm-readdone')") and ev("!!document.querySelector('#numScreen .nm-mic')"), 'wrong choice: read step with "I read it" and mic')
    ev("document.querySelector('#numScreen .nm-readdone').click()"); pg.wait_for_timeout(200); settle()
    ok(ev("nm.cur.phase") == 'ear2' and ev("!!document.querySelector('#numScreen .nm-choice')"), 'then choose again by ear')
    ev("[...document.querySelectorAll('#numScreen .nm-choice')].find(b=>b.textContent==='11').click()"); pg.wait_for_timeout(300)
    ok(ev("nm.cur.phase") == 'done', 'right choice: done')
    ev("nmSetChange('opts',2); nmNext()")
    ok(ev("document.querySelectorAll('#numScreen .nm-choice').length") == 2, '2 buttons setting')
    # ===== набрать цифрами
    ev("nmSetChange('answer','keys'); nmNext()"); setn(17)
    for k in ['1', '7']: ev(f"[...document.querySelectorAll('#numScreen .nm-key')].find(b=>b.textContent==='{k}').click()")
    ok(ev("document.querySelector('#numScreen .nm-typed').textContent") == '17', 'typed 17')
    ev("document.querySelector('#numScreen .nm-key.ok').click()"); pg.wait_for_timeout(300)
    ok(ev("nm.cur.phase") == 'done', 'keys: correct number')
    ev("nmNext()"); setn(17); ev("nmKey('7'); nmKey('0'); nmKey('del'); nmKey('0'); nmKey('ok')"); pg.wait_for_timeout(300)
    ok(ev("nm.cur.phase") == 'read' and ev("nm.cur.res.heardN") == 70, 'keys: 70 instead of 17 is a mistake')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== как показывать
    ev("nmSetChange('show','digits'); nmNext(); nm.cur.phase='read'; nm.cur.need=1; nmRender()")
    ok(ev("!!document.querySelector('#numScreen .nm-show .nm-dig')") and not ev("!!document.querySelector('#numScreen .nm-show .nm-word')"), 'digits only')
    ev("nmSetChange('show','words'); nmRender()")
    ok(not ev("!!document.querySelector('#numScreen .nm-show .nm-dig')") and ev("!!document.querySelector('#numScreen .nm-show .nm-word')"), 'word only')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== диапазоны
    for rng, exp in [('teens', list(range(11, 20))), ('tens', list(range(10, 100, 10))), ('to20', list(range(0, 21)))]:
        ev(f"nmSetChange('range','{rng}')")
        ok(sorted(ev("nmPool()")) == exp, f'range {rng}')
    ev("nmSetChange('range','pairs')"); pool = ev("nmPool()")
    ok(all(x in pool for x in (11, 13, 30, 12, 20, 14, 40)), 'hard pairs range')
    ev("nmSetChange('range','custom'); nmSetChange('from',5); nmSetChange('to',7)")
    ok(sorted(ev("nmPool()")) == [5, 6, 7], 'custom 5..7')
    ev("nmSetChange('from',900); nmSetChange('to',1000)"); ok(max(ev("nmPool()")) == 1000, 'up to 1000')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== чаще трудные
    ev("const s=loadStats(); s.ru.modes.num.words['17']={ok:0,bad:20}; saveStats(s); nmSetChange('range','to20'); nm.pool=null")
    picks = ev("(()=>{let k=0; for(let i=0;i<400;i++){ nm.last=null; if(nmPick()===17) k++; } return k})()")
    ok(picks > 80, 'smart: number with mistakes comes often (%d/400)' % picks)
    ev("nmSetChange('smart',0); nm.pool=null")
    picks2 = ev("(()=>{let k=0; for(let i=0;i<400;i++){ nm.last=null; if(nmPick()===17) k++; } return k})()")
    ok(picks2 < 50, 'smart off: uniform (%d/400)' % picks2)
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== фразы
    ev("nmSetChange('ctx',2); nmNext()")
    ok(ev("!!nm.cur.ctx") and ev("nm.cur.ctx.show.includes(String(nm.cur.n))"), 'phrase with the number: ' + str(ev("nm.cur.ctx && nm.cur.ctx.show")))
    ok(ev("(()=>{ for (let i=0;i<300;i++){ nmNext(); nmStop(); if(!nm.cur.ctx) return false; } return true })()"), 'only phrases: every number has a phrase (0 is replaced), 300 tries')
    ok(ev("(()=>{for(let i=0;i<300;i++){const c=nmCtxFor(21); if(c && /гривн|минут/.test(c.show)) return false;} return true})()"), 'no feminine phrases for 21')
    ok(ev("(()=>{for(let i=0;i<200;i++){const c=nmCtxFor(5); if(c && /Мне 5/.test(c.show)) return c.show==='Мне 5 лет';} return true})()"), 'agreement: Мне 5 лет')
    setn(13, "{show:'Кабинет 13', say:'Кабинет тринадцать'}"); ev("__spoken.length=0; nmSpeak(false)"); pg.wait_for_timeout(300)
    ok('Кабинет тринадцать' in ev("__spoken"), 'phrase spoken')
    say('кабинет тринадцать')
    ok(ev("nm.cur.phase") == 'done', 'phrase answer with the number accepted')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== итог занятия
    ev("nmSetChange('auto',0); nmSetChange('len',10); nmOpen()")
    for k in range(10):
        nn = ev("nm.cur.n")
        say(str(nn) if k % 3 else str((nn + 1) % 21))
        if ev("nm.cur.phase") == 'read':
            say(str(nn)); say(str(nn))
        ev("nmNext()"); pg.wait_for_timeout(100)
    ok(ev("nm.summary") and 'С первого раза' in ev("document.getElementById('numScreen').textContent"), 'summary after 10 numbers')
    ok('Путались' in ev("document.getElementById('numScreen').textContent"), 'summary lists confusions')
    ev("document.querySelector('#numScreen .nm-again').click()"); pg.wait_for_timeout(300)
    ok(not ev("nm.summary") and ev("nm.i") == 1, 'another session')
    ev("localStorage.setItem('sr.num.set', JSON.stringify({len:0}))")
    # ===== статистика, журнал, подсказка, обучение, справка
    ev("openStats(); statsTab='num'; renderStatsPanel()"); pg.wait_for_timeout(150)
    st = ev("document.getElementById('statsPanel').textContent")
    ok('11' in st and '13' in st, 'statistics tab shows numbers and confusions')
    ev("mlOpen=true; renderStatsPanel()")
    ok('Числа на слух' in ev("document.querySelector('#statsPanel .ml-box').textContent"), 'log shows mode name')
    ev("closeStats()")
    ev("goHome(); startMode('num'); ihSec=()=>0.3; ihNewTask()"); pg.wait_for_timeout(1500)
    ok(ev("!!document.querySelector('#numScreen .nm-mic.ih-pulse')"), 'idle hint pulses the answer button')
    ev("ihSec=()=>0; ihNewTask()")
    ev("tourStart('num')"); pg.wait_for_timeout(300)
    ok(ev("TOUR.active") and ev("TOUR.el && TOUR.el.classList.contains('nm-hidden')"), 'tutorial step 1')
    ev("tourStep(1)"); ok(ev("TOUR.el && TOUR.el.classList.contains('nm-ctl')"), 'tutorial step 2')
    ev("tourStep(1)"); ok(ev("TOUR.el && TOUR.el.classList.contains('nm-mic')"), 'tutorial step 3')
    ev("tourEnd()")
    ok(ev("['ru','uk','en'].every(l=>helpParse(l).keysOk)"), 'help keys match in all languages')
    ok(ev("['ru','uk','en'].every(l=>/🔟/.test(helpParse(l).items[HELP_KEYS.indexOf('m_num')].title) && /🔟/.test(helpParse(l).items[HELP_KEYS.indexOf('s_num')].title))"), 'help items for the mode')
    ev("openHelp()"); pg.wait_for_timeout(150)
    ok('Числа на слух' in ev("document.getElementById('helpOverlay').textContent"), 'mode help')
    ev("closeHelp()")
    # ===== «Читаю вслух»: красные слоги без светлой плашки в тёмной теме
    ev("document.documentElement.setAttribute('data-theme','dark'); goHome(); startMode('read'); rd.list=[]; rdSave(); rdAdd('корова'); rdStartWord(0)"); pg.wait_for_timeout(200)
    ev("__srQueue.push({alts:['карова']}); document.querySelector('#readScreen .rd-mic').click()"); pg.wait_for_timeout(400)
    bg = ev("(()=>{const b=document.querySelector('#readScreen .rd-res .rd-syl.bad'); const m=getComputedStyle(b).backgroundColor.match(/[\\d.]+/g).map(Number); return m})()")
    lum = (0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]) * (bg[3] if len(bg) > 3 else 1)
    ok(lum < 60, 'dark theme: red syllable without a light background ' + str(bg))
    # ===== язык
    ev("localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ev("startMode('num')"); pg.wait_for_timeout(300); setn(11)
    say('тринадцять')
    ok('одинадцять' in ev("document.querySelector('#numScreen .nm-show').textContent"), 'uk: word shown')
    ok(not errs, 'no page errors: ' + str(errs))
    ctx.close()
    # ===== вёрстка: 360/313/277/240 × ru/uk/en
    GEO = r"""(() => {
      const vw = document.documentElement.clientWidth, out = [];
      document.querySelectorAll('#numScreen *, #nmSettBox *').forEach(e => {
        if (!e.offsetParent) return;
        const r = e.getBoundingClientRect();
        if (r.right > vw + 1 || r.left < -1) out.push('OUT ' + e.className + ' ' + Math.round(r.right));
        if (e.tagName === 'BUTTON' && e.scrollWidth > e.clientWidth + 2) out.push('TEXT ' + e.className + ' «' + e.textContent.slice(0, 20) + '»');
        if (e.tagName === 'BUTTON' && r.height < 40) out.push('SMALL ' + e.className + ' ' + Math.round(r.height));
      });
      if (document.documentElement.scrollWidth > vw + 1) out.push('HSCROLL');
      return out;
    })()"""
    for lang in ['ru', 'uk', 'en']:
        for z in (1.0, 1.15, 1.3, 1.5):
            W, H = round(360 / z), round(640 / z)
            c2 = b.new_context(viewport={'width': W, 'height': H})
            c2.route('**/*', lambda r: r.continue_() if r.request.url.startswith('http://127.0.0.1') else r.abort())
            c2.add_init_script(MOCK)
            p2 = c2.new_page(); p2.goto(URL); p2.wait_for_timeout(300)
            p2.evaluate(f"localStorage.setItem('app_lang','{lang}'); localStorage.setItem('sr.tour.offer','0')"); p2.reload(); p2.wait_for_timeout(400)
            tag = f'{lang} {W}x{H}'
            scenes = [
              ('ear', "startMode('num'); nmStop(); nm.cur.n=777; nmRender()"),
              ('read', "nm.cur.phase='read'; nm.cur.need=2; nm.cur.other=787; nm.cur.res={ok:false, heardN:787, heardText:'787', viaVoice:true}; nmRender()"),
              ('readctx', "nm.cur.n=1000; nm.cur.other=100; nm.cur.ctx=nmCtxFor(1000)||{show:'Это стоит 1000 гривен', say:''}; nmRender()"),
              ('choice', "nmSetChange('answer','choice'); nmNext(); nmStop(); nm.cur.n=1000; nm.cur.opts=[1000, 100, 900, 990]; nmRender()"),
              ('keys', "nmSetChange('answer','keys'); nmNext(); nmStop(); nm.typed='1000'; nmRender()"),
              ('keysread', "nm.cur.phase='read'; nm.cur.need=1; nm.cur.res={ok:false, heardN:100}; nmRender()"),
              ('done', "nmSetChange('auto',0); nm.cur.phase='done'; nm.cur.res={ok:true}; nmRender()"),
              ('summary', "nm.summary=true; nm.i=20; nm.firstOk=13; nm.sessConf={'11 → 13':3,'14 → 40':2,'17 → 70':1,'19 → 90':1}; nmRender()"),
              ('settings', "openSettings(); settShow('num'); const s=document.getElementById('nmSetRange'); s.value='custom'; s.dispatchEvent(new Event('change'))"),
            ]
            for name, js in scenes:
                p2.evaluate(js); p2.wait_for_timeout(200)
                g = p2.evaluate(GEO)
                ok(not g, f'{tag} {name}: layout ' + str(g[:4]))
                if name in ('keys', 'choice') and z == 1.0:
                    kv = p2.evaluate("(()=>{const e=document.querySelector('#numScreen .nm-key.ok') || [...document.querySelectorAll('#numScreen .nm-choice')].pop(); return e.getBoundingClientRect().bottom <= innerHeight + 1})()")
                    ok(kv, f'{tag} {name}: all answer buttons visible without scrolling')
                if name == 'ear':
                    m = p2.evaluate("(()=>{const r=document.querySelector('#numScreen .nm-mic').getBoundingClientRect(); return r.bottom <= innerHeight + 1})()")
                    ok(m, f'{tag} ear: answer button visible')
            c2.close()
    b.close()
srv.shutdown()
print(f"{n - len(fails)}/{n} passed")
