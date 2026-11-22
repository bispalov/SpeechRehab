import threading, http.server, functools, sys, json
from playwright.sync_api import sync_playwright
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sr_site import make_root, shots_dir
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=make_root()); H.log_message=lambda *a, **k: None
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
MOCK = """Object.defineProperty(navigator,'serviceWorker',{get(){return {register:()=>Promise.reject()}}});
speechSynthesis.speak=u=>{}; class F{start(){}stop(){}abort(){}}; window.SpeechRecognition=F; window.webkitSpeechRecognition=F;"""
CHECK = r"""(() => {
  const out = [], vw = document.documentElement.clientWidth;
  document.querySelectorAll('button, .mode-card, select, input, label, .ph-chip, .chip, .sug, .wr-typed, .abc-prefix, .step-title, .ser-hint, .ph-score').forEach(e => {
    if (!e.offsetParent && getComputedStyle(e).position !== 'fixed') return;
    const r = e.getBoundingClientRect();
    if (r.width === 0) return;
    const txt = (e.innerText || e.value || '').trim().slice(0, 30);
    if (e.scrollWidth > e.clientWidth + 2 && !['SELECT','INPUT'].includes(e.tagName)) out.push('TEXT-OVERFLOW ' + e.className + ' «' + txt + '» ' + e.scrollWidth + '>' + e.clientWidth);
    if (r.right > vw + 1 || r.left < -1) out.push('OUT-OF-SCREEN ' + e.className + ' «' + txt + '» right=' + Math.round(r.right) + ' vw=' + vw);
  });
  const ti = document.getElementById('appTitle'), tr = ti.getBoundingClientRect(), fs = parseFloat(getComputedStyle(ti).fontSize);
  if (getComputedStyle(ti).visibility === 'hidden' || tr.width < 40 || fs < 14 || ti.scrollWidth > ti.clientWidth + 1) out.push('TITLE ' + Math.round(tr.width) + 'px font ' + fs);
  if (document.documentElement.scrollWidth > vw + 1) out.push('PAGE-HSCROLL ' + document.documentElement.scrollWidth + '>' + vw);
  return [...new Set(out)];
})()"""
SCENES = [
 ('select', "goHome()"),
 ('full', "startMode('full')"),
 ('listen1', "goHome(); startMode('listen')"),
 ('listen2', "renderListenStep(2); train.heard='код'; train.heardOk=false; updateTrainSayUI()"),
 ('listen3', "renderListenStep(3)"),
 ('listen4', "renderListenStep(4)"),
 ('quizsetup', "goHome(); startMode('quiz')"),
 ('quizword', "localStorage.setItem('sr.quiz.replay','true'); startQuiz(['дом','кот'])"),
 ('wr1', "quiz.active=false; goHome(); startMode('wr'); wrSetLevel(1); wr.typed=wrNorm(wr.target)[0]+'ыыы'; wrCheck()"),
 ('wr3', "localStorage.setItem('sr.phr.ru', JSON.stringify([{t:'Мне нужно позвонить дочери'}])); phr.loadedLang=null; wrSetLevel(3); wrShow()"),
 ('wrdone', "wr.typed=wr.target; wrCheck()"),
 ('abc', "goHome(); startMode('abc'); abcState.line=['я','хочу','позвонить']; abcState.fn=true; abcState.prefix='п'; abcRender()"),
 ('abcfree', "abcState.mode='free'; abcState.typed='тиливизор'; abcRender()"),
 ('hear', "goHome(); startMode('hear')"),
 ('phrlist', "goHome(); startMode('phr')"),
 ('phrdo', "if(!phr.list.length){phr.list=[{t:'Please give me some water',n:0,k:0,l:0}]} phrEnter(0); phr.res=phrCompare(phr.list[0].t,['мне нушно позвонит дочке']); phrRender(true)"),
 ('serlist', "goHome(); startMode('ser')"),
 ('serdo', "serStart('days'); ser.dir='round'; serNewTask(); ser.listening=true; ser.buf='понедельник среда'; serFinish()"),
 ('readlist', "goHome(); localStorage.setItem('sr.read.'+currentLang, JSON.stringify([{w:'достопримечательность',s:2,k:1,d:['2026-11-17'],done:0},{w:'корова',s:1,k:0,d:[],done:0},{w:'дом',s:1,k:0,d:[],done:1}])); rd.lang=null; startMode('read'); rd.sugOpen=true; rd.doneOpen=true; rd.msg=rdT().exists; rdRender()"),
 ('read1', "rdStartWord(1)"),
 ('read1res', "rd.prev={s:1,k:0,d:[],done:0,revealed:false}; rd.res={ok:false, heard:'карова', bad:[0], fixed:false, stage:1}; rdRender()"),
 ('read2long', "rdStartWord(0)"),
 ('read2done', "rd.stageNext=true; rd.stageMsg=rdT().stageDone; rd.res={ok:true, heard:'достопримечательность', bad:[], fixed:false}; rdRender()"),
 ('read4', "rdCur().s=4; rdStartWord(0)"),
 ('read4bad', "rd.revealed=true; rd.stageMsg=rdT().backStage; rdCur().s=3; rd.res={ok:false, heard:'достопримечательно', bad:[6,7], fixed:false}; rd.prev={s:4,k:0,d:[],done:0,revealed:false}; rdRender()"),
 ('readrec', "rd.rec='blob:x'; rd.recording=true; rd.recMsg=ex().ownRecording; rdRender()"),
 ('readdone', "rd.recording=false; rd.rec=null; rd.done='day'; rd.res={ok:true,heard:'достопримечательность',bad:[],fixed:false}; rdRender()"),
 ('num_ear', "goHome(); localStorage.setItem('sr.num.set', JSON.stringify({len:0})); startMode('num'); nmStop(); nm.cur.n=777; nmRender()"),
 ('num_read', "nm.cur.phase='read'; nm.cur.need=2; nm.cur.other=787; nm.cur.res={ok:false, heardN:787, heardText:'787', viaVoice:true}; nmRender()"),
 ('num_choice', "nmSetChange('answer','choice'); nmNext(); nmStop(); nm.cur.opts=[1000,100,900,990]; nmRender()"),
 ('num_keys', "nmSetChange('answer','keys'); nmNext(); nmStop(); nm.typed='1000'; nmRender()"),
 ('num_sum', "nm.summary=true; nm.i=20; nm.firstOk=13; nm.sessConf={'11 → 13':3,'14 → 40':2}; nmRender(); localStorage.removeItem('sr.num.set')"),
 ('sett_num', "goHome(); openSettings(); settShow('num')"),
 ('fph_ear', "goHome(); closeSettings(); localStorage.setItem('sr.fph.set', JSON.stringify({sess:0})); startMode('fph'); fpStop(); fp.cur.it={t:'Врач придёт в одиннадцать',c:'health',alt:['Врач придёт в тринадцать','Врач придёт в двенадцать']}; fp.cur.t=fp.cur.it.t; fp.cur.opts=null; fpRender()"),
 ('fph_read', "fp.cur.phase='read'; fp.cur.need=2; fp.cur.res={ok:false, heard:'врач придёт в тринадцать', rows:phrCompare(fp.cur.t,['врач придёт в тринадцать']).rows, viaVoice:true}; fpRender()"),
 ('fph_choose', "fpSetChange('task','choose'); fpSetChange('opts',4); fpNext(); fpStop(); fpRender()"),
 ('fph_yn', "fpSetChange('task','yesno'); fpNext(); fpStop(); fpRender()"),
 ('fph_list', "fp.view='list'; fpRender(); localStorage.removeItem('sr.fph.set')"),
 ('sett_fph', "goHome(); openSettings(); settShow('fph')"),
 ('sett_read', "goHome(); openSettings(); settShow('read')"),
 ('stats_read', "closeSettings(); openStats(); statsTab='read'; renderStatsPanel()"),
 ('stats_close', "closeStats()"),
 ('listen_bridge', "goHome(); startMode('listen'); train.attempts=1; train.heard='код'; train.heardOk=false; updateTrainSayUI()"),
 ('settings', "goHome(); openSettings()"),
 ('sett_train', "settShow('train')"), ('sett_abc', "settShow('abc')"), ('sett_ser', "settShow('ser')"),
 ('stats', "closeSettings(); openStats()"),
 ('dict', "closeStats(); openDict()"),
 ('help', "closeDict(); openHelp()"),
]
langs = sys.argv[1:] or ['ru']
with sync_playwright() as p:
    b = p.chromium.launch()
    for lang in langs:
      for zoom in (1.0, 1.15, 1.3, 1.5):
        pg = b.new_page(viewport={'width': round(360/zoom), 'height': round(760/zoom)})
        pg.add_init_script(MOCK + "localStorage.setItem('sr.tour.offer','0'); localStorage.setItem('app_lang','%s'); localStorage.setItem('app_timer_enabled','true');" % lang)
        pg.goto('http://127.0.0.1:%d/SpeechRehab/index.html' % srv.server_address[1]); pg.wait_for_timeout(500)
        tot = 0
        for name, js in SCENES:
            try: pg.evaluate(js)
            except Exception as e: print(lang, zoom, name, 'JSERR', e); continue
            pg.wait_for_timeout(150)
            res = pg.evaluate(CHECK)
            if res:
                tot += len(res)
                print(f'[{lang} {zoom}] {name}:'); [print('   ', r) for r in res]
            if name in ('wr1','abc','serdo','phrdo','settings','select','readlist','read1res','read2long','read4bad','readrec','sett_read','num_read','num_choice','num_keys','sett_num','fph_read','fph_yn','sett_fph'): pg.screenshot(path=os.path.join(shots_dir(), f'z_{lang}_{zoom}_{name}.png'))
        print(f'== {lang} zoom {zoom}: {tot} issues')
        pg.close()
    b.close()
srv.shutdown()
