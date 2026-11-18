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

    pg.set_viewport_size({'width': 360, 'height': 740})
    def put(word, st='train', fn='trainLb'):
        ev("'%s'.split('').forEach(ch=>{const i=%s.tiles.findIndex(t=>(!t.used||t.reuse)&&t.ch===ch); %s.place(i)})" % (word, st, fn))
    # --- настройка
    ev("openSettings(); settShow('train')")
    ok(ev("document.getElementById('labelBuildLetters').textContent").startswith('Буквы для сборки слова'), 'setting label')
    ok(ev("[...document.getElementById('buildLettersSelect').options].map(o=>o.value)") == ['word','extra','abc'], 'three options')
    ok('🧩 тренажёр и 👂 слух' in ev("document.getElementById('labelRequireSpeech').innerText"), 'require label names modes')
    ev("closeSettings && closeSettings()")
    # --- только буквы слова
    ev("localStorage.setItem('sr.build','word'); goHome(); startMode('listen'); trainReset('ко-ро-ва'); renderListenStep(2)")
    ok(sorted(ev("train.tiles.map(t=>t.ch)")) == sorted('корова'), 'word: only word letters')
    # --- лишние буквы
    counts = set(); sim_ok = True
    for _ in range(25):
        ev("localStorage.setItem('sr.build','extra'); trainReset('ко-ро-ва'); renderListenStep(2)")
        ch = ev("train.tiles.map(t=>t.ch)"); extra = len(ch) - 6; counts.add(extra)
        rest = list(ch)
        for c in 'корова': rest.remove(c)
        if any(c in 'корова' for c in rest): sim_ok = False
    ok(counts <= {1, 2, 3} and len(counts) >= 2, 'extra: 1–3 extra letters ' + str(counts))
    ok(sim_ok, 'extra letters not from the word')
    ev("trainReset('дом'); renderListenStep(2)")
    ex = [t for t in ev("train.tiles.map(t=>t.ch)")]
    for c in 'дом': ex.remove(c)
    ok(any(c in 'тнаё' for c in ex) or len(ex) >= 1, 'extra letters for дом: ' + ''.join(ex))
    put('корова'[:0]); ev("trainReset('ко-ро-ва'); renderListenStep(2)"); put('корова')
    ok(ev("train.builtOk") is True and ev("document.getElementById('trainNextBuild').disabled") is False, 'extra: complete with spare tiles left')
    # --- вся азбука
    ev("localStorage.setItem('sr.build','abc'); trainReset('ко-ро-ва'); renderListenStep(2)")
    ok(ev("train.tiles.length") == 33 and ev("document.getElementById('trainTiles').classList.contains('lb-abc-set')"), 'abc: full alphabet grid')
    put('корова')
    ok(ev("train.builtOk") is True and ev("train.tiles.every(t=>!t.used)"), 'abc: letters reusable, word built')
    ev("trainClear()"); put('карова')
    ok(ev("[...document.querySelectorAll('#trainSlots .letter-tile')].map(b=>b.classList.contains('bad'))") == [False, True, False, False, False, False], 'abc: wrong letter red')
    ev("trainRemove(1)"); put('о')
    ok(ev("train.builtOk") is True, 'abc: fixed in place')
    w = ev("document.documentElement.scrollWidth"); ok(w <= 360, 'abc: no horizontal scroll')
    pg.set_viewport_size({'width': 277, 'height': 600}); ok(ev("document.documentElement.scrollWidth") <= 277, 'abc: fits 277')
    pg.set_viewport_size({'width': 360, 'height': 740})
    # --- смена настройки на открытом шаге
    ev("document.getElementById('buildLettersSelect').value='word'; lbSetChanged()")
    ok(ev("train.tiles.length") == 6 and ev("document.querySelectorAll('#trainTiles .letter-tile').length") == 6, 'setting change applies on open step')
    # --- полный тренажёр
    ev("localStorage.setItem('sr.build','extra'); goHome(); startMode('full'); targetWordSyllables='ко-ро-ва'; targetWordClean='корова'; document.getElementById('modeSpell').checked=true; setupSpellBuilder('ко-ро-ва')"); pg.wait_for_timeout(200)
    np = ev("document.querySelectorAll('#lettersPool .letter-tile').length")
    ok(7 <= np <= 9, 'full: extra letters in pool ' + str(np))
    ok(ev("document.querySelectorAll('#lettersTarget .letter-slot').length") == 6, 'full: slots shown')
    ok(ev("Math.max(...[...document.querySelectorAll('#lettersPool .letter-tile')].map(b=>b.getBoundingClientRect().width))") < 100, 'full: compact tiles')
    ev("__spoken=[]"); put('кровао', 'spell', 'spellLb')
    ok(ev("document.querySelectorAll('#lettersTarget .letter-tile.bad').length") >= 1 and 'Не совсем. Замените красные буквы.' in ev("__spoken"), 'full: wrong build red + voice')
    ev("lbClear(spell); renderSpellTiles(); __spoken=[]"); put('корова', 'spell', 'spellLb')
    ok(any('коров' in x.lower() for x in ev("__spoken")) and ev("document.querySelectorAll('#lettersTarget .letter-tile.bad').length") == 0, 'full: correct build speaks word')
    ev("localStorage.setItem('sr.build','abc'); setupSpellBuilder('ко-ро-ва')")
    ok(ev("document.querySelectorAll('#lettersPool .letter-tile').length") == 33, 'full: abc alphabet')
    # uk азбука
    ev("localStorage.setItem('app_lang','uk')"); pg.reload(); pg.wait_for_timeout(500)
    ev("localStorage.setItem('sr.build','abc'); startMode('listen'); trainReset('кіт'); renderListenStep(2)")
    ok('ї' in ev("train.tiles.map(t=>t.ch).join('')"), 'uk alphabet')
    ev("localStorage.setItem('sr.build','word')")
    # ===== v66: при «Вся азбука» слоги не подсказываются
    ev("localStorage.setItem('app_lang','ru')"); pg.reload(); pg.wait_for_timeout(500)
    ev("document.getElementById('spellSyllableHint').checked=true; localStorage.setItem('sr.build','word'); startMode('listen'); trainReset('ко-ро-ва'); renderListenStep(2)")
    ok('ко • ро • ва' in ev("document.getElementById('listenScreen').innerText"), 'word mode: syllables shown')
    ev("document.getElementById('buildLettersSelect').value='abc'; lbSetChanged()")
    ok('ко • ро • ва' not in ev("document.getElementById('listenScreen').innerText") and ev("train.tiles.length") == 33, 'abc: syllables hidden (setting changed on open step)')
    ev("goHome(); startMode('full'); targetWordSyllables='ко-ро-ва'; targetWordClean='корова'; document.getElementById('modeSpell').checked=true; setupSpellBuilder('ко-ро-ва')")
    ok(ev("document.getElementById('syllableDisplay').style.display") == 'none', 'full abc: syllables hidden before assembly')
    put('корова', 'spell', 'spellLb')
    ok(ev("document.getElementById('syllableDisplay').style.display") == '', 'full abc: syllables shown after correct assembly')
    ev("document.getElementById('buildLettersSelect').value='word'; lbSetChanged()")
    ok(ev("document.getElementById('syllableDisplay').style.display") == '' and ev("spell.tiles.length") == 6, 'full word: syllables back')
    ok('слоги не подсказываются' in ev("document.getElementById('optBuildAbc').textContent"), 'option text explains')
    ev("localStorage.setItem('sr.build','word')")
    ok(not errs, 'no page errors: ' + '; '.join(errs))
    b.close()
srv.shutdown()
print(f'{n - len(fails)}/{n} passed')
sys.exit(1 if fails else 0)
