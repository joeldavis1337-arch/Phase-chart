"""Phase App regression harness. Usage: python3 tests/run.py [path/to/index.html]"""
import json, sys, os, threading, http.server, functools, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent
app = pathlib.Path(sys.argv[1] if len(sys.argv)>1 else ROOT.parent/'index.html').resolve()
cases = json.load(open(ROOT/'cases.json'))
out = ROOT/'out'; out.mkdir(exist_ok=True)
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(app.parent))
class Q(H.func):
    def log_message(self,*a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1',0), functools.partial(Q, directory=str(app.parent)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{srv.server_port}/{app.name}'
SEV = {'ok':0,'info':0,'warn':1,'fault':2}
LOAD = """(c)=>{
  try{localStorage.setItem('phaseChart_ampDetect',c.detect||'pk');}catch(e){}
  if(typeof isoDefaultCfg==='function') isoCfg=c.iso?JSON.parse(JSON.stringify(c.iso)):isoDefaultCfg();
  let id=1; nodes=c.nodes.map((n,i)=>({id:i+1,name:n.name,shape:n.shape,coupSide:n.coupSide,phaseUnstable:!!n.phaseUnstable,bearingType:n.bearingType||'auto',ci:i,rpm:'',notes:'',
     meas:n.meas.map(m=>Object.assign({id:id++,pos:m[0],label:m[1],amp:m[2],phase:m[3],ref:false},m[4]||{}))}));
  document.getElementById('amp-unit').value=c.unit;
  const L=document.getElementById('layout'); if(L) L.value=c.layout;
  renderSidebar(); runDiagnosis();
  return {results:diagResults.map(r=>({type:r.type,label:r.label,desc:r.desc})), sev:bubbleSeverity,
          labels:Object.fromEntries(nodes.flatMap(n=>n.meas.map(m=>[m.id,m.label])))};
}"""
report=[]; fails=0
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width':1400,'height':900})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(1200)
    pg.evaluate("()=>{try{closeWN()}catch(e){}}")
    for c in cases:
        r = pg.evaluate(LOAD, c)
        got = r['results']; e = c.get('expect',{}); problems=[]
        lbls=[g['label'] for g in got]
        for s in e.get('present',[]):
            if not any(s in l for l in lbls): problems.append(f'missing finding "{s}"')
        for s in e.get('absent',[]):
            hit=[l for l in lbls if s in l]
            if hit: problems.append(f'unexpected finding: {hit[0]}')
        for s,maxs in e.get('maxSeverityOf',{}).items():
            for g in got:
                if s in g['label'] and SEV[g['type']]>SEV[maxs]: problems.append(f'"{s}" rated {g["type"]}, expected no higher than {maxs}')
        for s_,mins in e.get('minSeverityOf',{}).items():
            m_=[g for g in got if s_ in g['label']]
            if not m_: problems.append(f'missing finding "{s_}"')
            for g in m_:
                if SEV[g['type']]<SEV[mins]: problems.append(f'"{s_}" rated {g["type"]}, expected at least {mins}')
        bl={r['labels'][k]:v for k,v in r['sev'].items()}
        for lab,want in e.get('bubbles',{}).items():
            if bl.get(lab)!=want: problems.append(f'bubble {lab} is {bl.get(lab)}, expected {want}')
        for s_,txt in e.get('descContains',{}).items():
            m_=[g for g in got if s_ in g['label']]
            if not m_: problems.append(f'missing finding "{s_}"')
            elif not any(txt in g['desc'] for g in m_): problems.append(f'"{s_}" text lacks "{txt}"')
        for t in e.get('bannedText',[]):
            if any(t in g['desc'] for g in got): problems.append(f'text fires: "{t}"')
        pg.evaluate("()=>{showTab('chart');redraw()}"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(out/f"{c['id']}.png"))
        fails+=bool(problems)
        report.append({'id':c['id'],'pass':not problems,'problems':problems,'findings':[f"[{g['type']}] {g['label']}" for g in got],'descs':[g['desc'] for g in got],
                       'bubbles':bl})
    b.close()
for x in report:
    print(('PASS ' if x['pass'] else 'FAIL ')+x['id'])
    for f in x['findings']: print('     ',f)
    for pr in x['problems']: print('   ✗',pr)
print(f"\n{len(report)-fails}/{len(report)} passed. page errors: {errs or 'none'}")
json.dump(report,open(out/'report.json','w'),indent=1,ensure_ascii=False)
