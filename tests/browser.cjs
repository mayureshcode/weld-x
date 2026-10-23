// Real HTTP/backend tests with the unavailable production adapter, never fake physics.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
(async()=>{
 const base=process.env.WELDX_BASE_URL||'http://127.0.0.1:8765';
 const out=process.env.WELDX_EVIDENCE_DIR||'evidence';fs.mkdirSync(out,{recursive:true});
 const options={headless:true,args:['--no-sandbox']};
 if(process.env.WELDX_CHROMIUM)options.executablePath=process.env.WELDX_CHROMIUM;
 const browser=await chromium.launch(options);
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.waitForFunction(()=>document.querySelector('#connection').textContent==='API CONNECTED');
 if(!(await page.locator('#execute').isDisabled()))throw Error('Execution enabled without validation');
 await page.screenshot({path:path.join(out,'dashboard-desktop.png')});
 await page.locator('#detect').click();await page.waitForFunction(()=>document.querySelector('#stage').textContent==='DETECT');
 await page.waitForFunction(()=>!document.querySelector('#search').disabled);
 await page.locator('#search').click();await page.waitForFunction(()=>document.querySelector('#stage').textContent==='MAP');
 await page.waitForFunction(()=>document.querySelector('#candidates button'));
 await page.locator('#candidates button').first().click();
 await page.waitForFunction(()=>document.querySelector('#diagnostics').textContent.includes('UNKNOWN'));
 const snapshot=await (await page.request.get(base+'/api/state')).json();
 if(!snapshot.candidates.length||snapshot.candidates.some(c=>c.classification!=='validation_incomplete')||snapshot.authorized||snapshot.recommended)throw Error('Unknown records misclassified');
 await page.locator('#workflow-title').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'dashboard-records.png')});
 await page.locator('#detect').click();await page.waitForFunction(()=>document.querySelector('#stage').textContent==='DETECT');
 await page.waitForFunction(()=>!document.querySelector('#revalidate').disabled);
 await page.locator('#revalidate').click();await page.waitForFunction(()=>document.querySelector('#stage').textContent==='STOPPED');
 if(!(await page.locator('#execute').isDisabled()))throw Error('Unknown revalidation authorized execution');
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:path.join(out,'dashboard-mobile.png')});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile page overflows');
 await page.route('**/api/state',r=>r.abort());
 await page.waitForFunction(()=>document.querySelector('#connection').textContent==='BACKEND DISCONNECTED');
 if(!(await page.locator('#execute').isDisabled()))throw Error('Disconnect not fail-closed');
 await page.screenshot({path:path.join(out,'dashboard-disconnected.png')});
 if(errors.length)throw Error(errors.join(';'));
 fs.writeFileSync(path.join(out,'browser-tests.json'),JSON.stringify({result:'passed',tests:['initial_execution_disabled','backend_connected','detect_real_unknown_results','bounded_search_real_candidates','candidate_selection_real_diagnostics','unknown_revalidation_blocks_execution','mobile_no_page_overflow','disconnect_visible_and_fail_closed','no_browser_runtime_errors'],evaluated_candidates:snapshot.candidates.length,robotics_execution_tested:false,viewports:['1440x1100','390x844'],browser:await browser.version()},null,2)+'\n');
 fs.writeFileSync(path.join(out,'negative-runtime-check.json'),JSON.stringify({scope:'unavailable production adapter; NOT robotics simulation evidence',health:snapshot.health,search:snapshot.search,authorized:snapshot.authorized,recommended:snapshot.recommended,candidates:snapshot.candidates.map(c=>({id:c.id,base:c.base,classification:c.classification,nominal_check_count:c.evidence.evaluation.nominal.checks.length,unknown_checks:c.evidence.evaluation.nominal.checks.filter(x=>x.result==='unknown').length,robustness:c.evidence.evaluation.robustness.outcome}))},null,2)+'\n');
 console.log('9 browser checks passed; actual unknown candidates:',snapshot.candidates.length);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
