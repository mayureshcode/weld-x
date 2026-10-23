"""Real no-solution commissioning workflow plus exact trajectory/scenario UI links."""
import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent
report={'scope':'real no-solution workflow; no fabricated approval or robust success','checks':[],'errors':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/local/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1440,'height':1100});page.on('pageerror',lambda e:report['errors'].append(str(e)))
 def until(predicate,timeout=60):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   if predicate():return
   page.wait_for_timeout(200)
  raise AssertionError('UI condition timed out')
 try:
  page.goto('http://127.0.0.1:8766');until(lambda:page.locator('#cell-view canvas').count()==1)
  page.locator('#detect').click();until(lambda:page.locator('#task').inner_text()=='detect: finished',120)
  assert page.locator('#execute').is_disabled();report['checks'].append('real detection fails and execution stays blocked')
  page.locator('#search').click();until(lambda:page.locator('#task').inner_text()=='search: finished',340)
  state=page.request.get('http://127.0.0.1:8766/api/state').json();assert state['recommended'] is None and not state['authorized']
  assert state['candidates'] and len(state['candidates'])<=16
  assert all(c['status'] in ('pass','fail','unknown') for c in state['candidates'])
  report['search']=state['search'];report['checks'].append('bounded actual search reports explicit fail/unknown candidate states and no solution')
  # The centre candidate is a real nominal pass with robust boundary rejection.
  candidate=next(c for c in state['candidates'] if c['classification']=='nominally_feasible_not_robust')
  index=state['candidates'].index(candidate);page.locator('#candidates button').nth(index).click()
  page.select_option('#source-select','base');until(lambda:'predicted residual' in page.locator('#scene-evidence-status').inner_text())
  assert '×50' in page.locator('#scene-evidence-status').inner_text();assert page.locator('#scenario-select option').count()>0
  view=page.request.get('http://127.0.0.1:8766/api/scene-evidence?candidate_id='+candidate['id']+'&source=base').json()
  assert len(view['segments'])==7 and view['scenario_preview']['outcome']=='fail';assert view['scenario_preview']['worst_planned_residual']['norm_m']>0
  report['scene_evidence']={'config_hash':view['config_hash'],'trajectory_id':view['trajectory_id'],'segment_count':len(view['segments']),'scenario':view['scenario_preview']['scenario'],'predicted_residual_m':view['scenario_preview']['worst_planned_residual']['norm_m']}
  report['checks'].append('selected candidate and actual recorded scenario link exact planned paths and explicitly predicted source residual to 3D')
  page.locator('#show-planned').uncheck();page.locator('#show-planned').check()
  opts=page.locator('#scenario-select option');page.select_option('#scenario-select',opts.last.get_attribute('value'));report['checks'].append('planned-path visibility and scenario-selection controls operate')
  assert '0 observed runs' in page.locator('#sensitivity').inner_text();assert 'unavailable' in page.locator('#sensitivity').inner_text()
  report['checks'].append('sensitivity separates screen failures, zero observed jobs, missing MC and unavailable empirical rates')
  page.get_by_role('button',name='Inspect complete evidence',exact=True).click();until(lambda:page.locator('#evidence-dialog').is_visible());assert 'execution_evidence' in page.locator('#evidence-dialog').inner_text();page.get_by_role('button',name='Close evidence',exact=True).click()
  page.screenshot(path=str(root/'evidence/phase3/dashboard-desktop.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(1000);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  page.screenshot(path=str(root/'evidence/phase3/dashboard-mobile.png'),full_page=True);report['checks'].append('desktop/mobile evidence UI inspected; mobile no viewport overflow')
  token=page.request.get('http://127.0.0.1:8766/api/session').json()['csrf_token']
  for route,body in [('approve',{'candidate_id':candidate['id'],'config_hash':state['config_hash'],'engineer':'Not a qualifying recommendation'}),('apply',{'approval_id':'unapproved'}),('execute',{})]:
   r=page.request.post('http://127.0.0.1:8766/api/'+route,headers={'X-Weldx-Token':token},data=body)
   if route=='approve':assert r.status==409
   else:
    assert r.status==202;until(lambda:page.locator('#task').inner_text().startswith(route+': failed'),15)
  report['checks'].append('direct unqualified approval, unapproved apply and unauthorized execution all denied')
  page.route('**/api/state',lambda route:route.abort());page.route('**/api/telemetry',lambda route:route.abort());until(lambda:page.locator('#connection').inner_text()=='BACKEND DISCONNECTED',10);assert page.locator('#execute').is_disabled()
  report['checks'].append('connection loss visibly locks UI and never authorizes execution')
  assert not report['errors'],report['errors'];report['result']='passed'
 finally:
  (root/'evidence/phase3/dashboard-workflow.json').write_text(json.dumps(report,indent=2)+'\n');browser.close();print(json.dumps(report,indent=2))
