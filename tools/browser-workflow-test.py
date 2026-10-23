from playwright.sync_api import sync_playwright
from pathlib import Path
import json,time
root=Path(__file__).resolve().parent.parent
report={'scope':'actual connected dashboard and no-solution workflow, not a successful approved recovery','checks':[],'errors':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/local/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1440,'height':1100})
 page.on('pageerror',lambda e:report['errors'].append(str(e)))
 page.on('console',lambda m:report['errors'].append(m.text) if m.type=='error' else None)
 try:
  def until(predicate,timeout=30):
   deadline=time.monotonic()+timeout
   while time.monotonic()<deadline:
    if predicate():return
    page.wait_for_timeout(250)
   raise AssertionError('UI condition timed out')
  page.goto('http://127.0.0.1:8766');until(lambda:page.locator('#cell-view canvas').count()==1 and 'Observed' in page.locator('#scene-status').inner_text())
  assert page.locator('#execute').is_disabled();report['checks'].append('live URDF/observed-joint 3D view; execution initially blocked')
  page.locator('#detect').click();until(lambda:page.locator('#task').inner_text()=='detect: finished',90)
  state=page.request.get('http://127.0.0.1:8766/api/state').json();assert not state['authorized'];assert state['initial']['robustness']['outcome']=='fail';report['checks'].append('real detection rejected mandatory uncertainty boundary')
  page.locator('#search').click();until(lambda:page.locator('#task').inner_text()=='search: finished',340)
  state=page.request.get('http://127.0.0.1:8766/api/state').json();assert state['candidates'];assert len(state['candidates'])<=16;assert not state['authorized'];assert state['recommended'] is None
  for c in state['candidates']:
   b=c['base'];assert all(state['configuration']['search'][k]['minimum']<=b[k]<=state['configuration']['search'][k]['maximum'] for k in ['x_m','y_m','yaw_rad'])
  report['checks'].append('bounded actual search ended without robust recommendation; execute remains disabled')
  page.locator('#candidates button').first.click();assert 'Selected candidate:' in page.locator('#candidate-detail').inner_text();assert page.locator('#comparison table').count()==1
  report['checks'].append('real candidate selection linked map, comparison and diagnostics')
  page.get_by_role('button',name='Inspect complete evidence',exact=True).click();until(lambda:page.locator('#evidence-dialog').count()==1);assert '"plan"' in page.locator('#evidence-dialog').inner_text();page.get_by_role('button',name='Close evidence',exact=True).click();report['checks'].append('complete immutable candidate evidence available on demand')
  page.locator('#audit button').first.click();until(lambda:page.locator('#evidence-dialog').is_visible());assert '"payload"' in page.locator('#evidence-dialog').inner_text();page.get_by_role('button',name='Close evidence',exact=True).click();report['checks'].append('complete hash-linked audit payload available on demand')
  started=time.monotonic();response=page.request.get('http://127.0.0.1:8766/api/state');report['status_payload']={'bytes':len(response.body()),'wall_s':time.monotonic()-started,'previous_measured_bytes':22140267};assert len(response.body())<2000000
  page.select_option('#seam-select',state['configuration']['job']['seams'][0]['id']);page.select_option('#source-select','base');assert 'boundary' in page.locator('#diagnostics').inner_text();report['checks'].append('seam highlight and source-specific recorded diagnostics')
  page.screenshot(path=str(root/'evidence/phase2/dashboard-final-desktop.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(1500)
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1');page.screenshot(path=str(root/'evidence/phase2/dashboard-final-mobile.png'),full_page=True);report['checks'].append('mobile page has no viewport overflow')
  report['search']=state['search'];report['candidate_classes']={k:sum(c['classification']==k for c in state['candidates']) for k in set(c['classification'] for c in state['candidates'])}
  # Backend authorization is enforced even when the UI is bypassed.
  token=page.request.get('http://127.0.0.1:8766/api/session').json()['csrf_token']
  r=page.request.post('http://127.0.0.1:8766/api/execute',headers={'X-Weldx-Token':token},data={});assert r.status==202
  until(lambda:'execute: failed' in page.locator('#task').inner_text(),15);assert page.locator('#execute').is_disabled();report['checks'].append('direct unauthorized execution request denied by backend')
  page.route('**/api/state',lambda route:route.abort());page.route('**/api/telemetry',lambda route:route.abort());until(lambda:page.locator('#connection').inner_text()=='BACKEND DISCONNECTED',10)
  assert page.locator('#execute').is_disabled();page.screenshot(path=str(root/'evidence/phase2/dashboard-final-disconnected.png'),full_page=True);report['checks'].append('lost API/telemetry connection visibly locks UI and freezes 3D view')
  # Route-abort console messages above are deliberate disconnect evidence, not JS faults.
  report['errors']=[e for e in report['errors'] if 'net::ERR_FAILED' not in e]
  assert not report['errors'],report['errors'];report['result']='passed'
 finally:
  (root/'evidence/phase2/dashboard-workflow-tests.json').write_text(json.dumps(report,indent=2)+'\n');browser.close();print(json.dumps({k:v for k,v in report.items() if k!='search'},indent=2))
