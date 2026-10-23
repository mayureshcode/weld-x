'use strict';
let state=null, token=null, selected=null;
let candidateKey=null, detailKey=null, auditKey=null, mapKey=null, evidenceKey=null;
const $=id=>document.getElementById(id);
const text=(id,value)=>{$(id).textContent=value;};
function node(tag,value){const n=document.createElement(tag);n.textContent=value;return n;}
function dl(id,rows){$(id).replaceChildren();for(const [key,value] of rows){$(id).append(node('dt',key),node('dd',String(value)));}}
async function post(path,body={}){
 try{const response=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-Weldx-Token':token},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw new Error(data.error);text('error','');await refresh();return data;}
 catch(error){text('error',error.message);return null;}
}
function evidence(candidate){return candidate?candidate.evidence.evaluation:(state.final||state.initial);}
function showEvidence(candidate){
 const ev=evidence(candidate);const source=$('source-select')?.value||'';
 const key=JSON.stringify([candidate?.id,ev?.config_hash,ev?.elapsed_s,source]);if(key===evidenceKey)return;evidenceKey=key;
 const trials=(ev?.robustness?.trials||[]).filter(t=>!source||t.scenario.source===source);
 const checks=source?trials.flatMap(t=>(t.summary_checks||t.plan?.checks||[]).filter(c=>c.result!=='pass').map(c=>({...c,reason:t.scenario.id+' — '+c.reason}))):(ev?.nominal?.checks||[]);
 text('source-detail',trials.length?`${trials.length} recorded trials; ${trials.filter(t=>t.outcome==='fail').length} confirmed failures; ${trials.filter(t=>t.outcome==='unknown').length} incomplete. Select source to inspect scenario constraints.`:'No uncertainty trials recorded for this selection.');
 const counts={pass:0,fail:0,unknown:0};for(const c of checks)counts[c.result]++;
 text('diagnostic-summary',checks.length?`${counts.pass} pass / ${counts.fail} fail / ${counts.unknown} unknown — ${checks.length} ${source?'displayed scenario-summary checks':'checks'}`:'No complete validation evidence. Execution remains blocked.');
 $('diagnostics').replaceChildren();for(const c of checks){const row=node('div','');row.className='record';row.append(node('strong',`${c.segment} / ${c.constraint} — ${c.result.toUpperCase()}`),node('span',c.reason));$('diagnostics').append(row);}
 $('sensitivity').replaceChildren();for(const group of ev?.robustness?.groups||[]){const row=document.createElement('tr');for(const value of [group.source,`${group.mc_passed} / ${group.mc_tested}; ${group.mc_unknown} unknown (required ${group.mc_expected})`,`${group.boundary_passed} / ${group.boundary_tested} (required ${group.boundary_expected})`,group.outcome])row.append(node('td',value));$('sensitivity').append(row);}
 if(!ev)$('sensitivity').append(node('tr','No scenario records available.'));
}
function render(){
 text('connection','API CONNECTED');$('connection').className='tag good';
 text('stage',state.stage);text('authorization',state.authorized?'AUTHORIZED':'LOCKED');
 text('authreason',state.authorized?'Exact configuration passed mandatory backend gates.':'Mandatory robotics evidence is missing, unknown or failed.');
 text('version',`Revision ${state.configuration.revision} / ${state.configuration.job.id}`);text('hash',state.config_hash);
 dl('health',Object.entries(state.health));const c=state.configuration;
 dl('configuration',[['Robot',c.robot],['Model version',c.model_version],['Job / seams',`${c.job.id} / ${c.job.seams.length}`],['Base x / y',`${c.base.x_m} / ${c.base.y_m} m`],['Base yaw',`${c.base.yaw_rad} rad`],['MC threshold',`${c.uncertainty.success_threshold*100}% (declared)`],['MC samples / source',c.uncertainty.mc_count]]);
 const busy=state.task?.status==='running'||!!state.active_operation;
 $('detect').disabled=busy;$('search').disabled=busy||!['DETECT','STOPPED','MAP','RECOMMEND'].includes(state.stage);
 $('revalidate').disabled=busy||!['IDLE','DETECT','APPLY','STOPPED'].includes(state.stage);$('execute').disabled=busy||!state.authorized;$('cancel').disabled=!busy;
 text('task',state.task?`${state.task.operation}: ${state.task.status}${state.task.error?' — '+state.task.error:''}`:'No active task');
 for(const li of document.querySelectorAll('.workflow li'))li.classList.toggle('current',li.textContent.toUpperCase().includes(state.stage));
 text('count',`${state.candidates.length} EVALUATED`);const nextCandidates=JSON.stringify(state.candidates.map(c=>[c.id,c.classification]));if(candidateKey!==nextCandidates){candidateKey=nextCandidates;$('candidates').replaceChildren();
 for(const candidate of state.candidates){const row=document.createElement('tr');const b=candidate.base;for(const value of [candidate.id.slice(0,10),`${b.x_m.toFixed(3)} / ${b.y_m.toFixed(3)}`,b.yaw_rad.toFixed(3),candidate.classification.replaceAll('_',' ')])row.append(node('td',value));const cell=document.createElement('td');const button=node('button','Inspect');button.onclick=()=>selectCandidate(candidate.id);cell.append(button);row.append(cell);$('candidates').append(row);}
 if(!state.candidates.length){const row=document.createElement('tr');const cell=node('td','No placements evaluated. Run detection, then search.');cell.colSpan=5;row.append(cell);$('candidates').append(row);}
 }
 const candidate=state.candidates.find(x=>x.id===selected);const nextDetail=candidate?.id||'';if(detailKey!==nextDetail){detailKey=nextDetail;$('candidate-detail').replaceChildren();if(candidate){$('candidate-detail').append(node('h3','Selected candidate: '+candidate.id.slice(0,10)));const pre=node('pre',JSON.stringify({base:candidate.base,classification:candidate.classification,robustness:candidate.evidence.evaluation.robustness.groups},null,2));$('candidate-detail').append(pre);const full=node('button','Inspect complete evidence');full.onclick=()=>inspectRecord('/api/evidence?candidate_id='+encodeURIComponent(candidate.id),$('candidate-detail'));$('candidate-detail').append(full);}}
 renderMap();renderComparison(candidate);
 const previousSeam=$('seam-select').value;if($('seam-select').dataset.job!==state.config_hash){$('seam-select').replaceChildren(node('option','All seams'));$('seam-select').firstChild.value='';for(const seam of state.configuration.job.seams){const o=node('option',seam.id);o.value=seam.id;$('seam-select').append(o);}$('seam-select').dataset.job=state.config_hash;}
 window.dispatchEvent(new CustomEvent('weldx-selection',{detail:{state,candidate,seamId:$('seam-select').value}}));
 const connected=state.health.adapter==='real_ROS2';const healthy=state.health.ros==='connected'&&state.health.gazebo==='live_pose_feedback'&&state.health.controllers==='active'&&state.health.moveit==='services_ready';text('runtime-title',connected&&!healthy?'ROBOTICS CONNECTION FAULT':connected?'REAL ROBOTICS ADAPTER / EVIDENCE GATED':'ROBOTICS RUNTIME NOT CONNECTED');text('runtime-notice',connected&&!healthy?'A simulator, planner, controller or feedback connection is missing or stale. Execution remains blocked.':connected?'Actual Jazzy / Harmonic / MoveIt telemetry. ABB model physical fidelity is provisional. Uncertainty trials require complete observed execution for success; insufficient budgets remain unknown and blocked.':'No real ROS adapter is selected. Missing or unknown evidence blocks execution.');
 showEvidence(candidate);$('approval-form').hidden=!state.recommended;$('approve').disabled=busy||state.stage!=='RECOMMEND';$('apply').disabled=busy||!state.approval;
 const nextAudit=state.audit.at(-1)?.digest||'';if(auditKey!==nextAudit){auditKey=nextAudit;$('audit').replaceChildren();for(const entry of [...state.audit].reverse()){const row=node('div','');row.className='record';row.append(node('strong',`${String(entry.sequence).padStart(3,'0')} / ${entry.kind}`),node('span',new Date(entry.time_unix_s*1000).toISOString()+' · '+entry.digest.slice(0,16)));const inspect=node('button','Inspect record');inspect.onclick=()=>inspectRecord('/api/audit?sequence='+entry.sequence,row);row.append(inspect);$('audit').append(row);}}
}
let refreshing=false;
async function refresh(){if(refreshing)return;refreshing=true;try{const response=await fetch('/api/state');if(!response.ok)throw new Error(`API ${response.status}`);state=await response.json();render();}catch(error){text('connection','BACKEND DISCONNECTED');$('connection').className='tag bad';text('authorization','LOCKED');text('authreason','Backend unreachable. Displayed records may be stale.');text('error',error.message);for(const button of document.querySelectorAll('button'))button.disabled=true;}finally{refreshing=false;}}
for(const action of ['detect','search','revalidate','execute','cancel'])$(action).onclick=()=>post(action);
$('approve').onclick=()=>post('approve',{candidate_id:state.recommended,config_hash:state.config_hash,engineer:$('engineer').value});
$('apply').onclick=()=>post('apply',{approval_id:state.approval.id});
(async()=>{try{const r=await fetch('/api/session');token=(await r.json()).csrf_token;}catch(error){text('error','Session initialization failed: '+error.message);}await refresh();setInterval(refresh,1500);})();
function selectCandidate(id){selected=id;const candidate=state.candidates.find(c=>c.id===id);if(candidate)$('map-yaw').value=String(candidate.base.yaw_rad);render();}
function renderMap(force=false){
 const svg=$('placement-map'),region=state.configuration.search,width=svg.clientWidth,height=svg.clientHeight;
 if(width<=0)return;const nextMap=JSON.stringify([state.candidates.map(c=>[c.id,c.classification]),selected,$('map-yaw').value,width,height,state.recommended]);if(force!==true&&mapKey===nextMap)return;mapKey=nextMap;svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.replaceChildren();
 const ns='http://www.w3.org/2000/svg';function el(tag,attrs,label){const e=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,String(v));if(label!==undefined)e.textContent=label;svg.append(e);return e;}
 const left=60,right=22,top=24,bottom=44,dx=region.x_m.maximum-region.x_m.minimum,dy=region.y_m.maximum-region.y_m.minimum;
 const x=v=>left+(v-region.x_m.minimum)/(dx||1)*(width-left-right),y=v=>height-bottom-(v-region.y_m.minimum)/(dy||1)*(height-top-bottom);
 const yaws=[...new Set(state.candidates.map(c=>c.base.yaw_rad))].sort((a,b)=>a-b);if(!yaws.length)yaws.push(state.configuration.base.yaw_rad);
 const previous=$('map-yaw').value;$('map-yaw').replaceChildren(...yaws.map(v=>{const o=node('option',v.toFixed(4));o.value=String(v);return o;}));if(yaws.map(String).includes(previous))$('map-yaw').value=previous;
 const yaw=Number($('map-yaw').value);const candidates=state.candidates.filter(c=>Math.abs(c.base.yaw_rad-yaw)<1e-9);
 for(let i=0;i<=4;i++){const a=region.x_m.minimum+dx*i/4,b=region.y_m.minimum+dy*i/4;el('line',{x1:x(a),x2:x(a),y1:top,y2:height-bottom,stroke:'#253c4d'});el('line',{x1:left,x2:width-right,y1:y(b),y2:y(b),stroke:'#253c4d'});if(i%2===0){el('text',{x:x(a),y:height-bottom+22,'text-anchor':'middle'},a.toFixed(2));el('text',{x:left-10,y:y(b)+4,'text-anchor':'end'},b.toFixed(2));}}
 el('text',{x:width-right,y:height-8,'text-anchor':'end'},'world x (m)');el('text',{x:8,y:16},'y (m)');
 let plotted=0;for(let ix=0;ix<1000&&plotted<500;ix++){const a=region.x_m.minimum+ix*region.x_m.step;if(a>region.x_m.maximum+1e-9)break;for(let iy=0;iy<1000&&plotted<500;iy++){const b=region.y_m.minimum+iy*region.y_m.step;if(b>region.y_m.maximum+1e-9)break;el('circle',{cx:x(a),cy:y(b),r:3,fill:'none',stroke:'#567082'});plotted++;}}
 const colors={robustly_feasible:'#72d7a3',nominally_feasible_not_robust:'#ffc775',nominally_infeasible:'#ff9999',validation_incomplete:'#bda7ed',unevaluated:'#567082'};
 for(const c of candidates){const circle=el('circle',{cx:x(c.base.x_m),cy:y(c.base.y_m),r:selected===c.id?9:7,fill:colors[c.classification]||'#567082',tabindex:0,role:'button','aria-label':`Candidate ${c.id.slice(0,10)}, x ${c.base.x_m}, y ${c.base.y_m}, yaw ${c.base.yaw_rad}, ${c.classification}`,class:'point'});const title=document.createElementNS(ns,'title');title.textContent=c.id+' · '+c.classification;circle.append(title);circle.onclick=()=>selectCandidate(c.id);circle.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectCandidate(c.id);}};if(state.recommended===c.id)el('text',{x:x(c.base.x_m),y:y(c.base.y_m)-14,'text-anchor':'middle'},'★');}
 const original=state.original_base||state.configuration.base;if(original.x_m>=region.x_m.minimum&&original.x_m<=region.x_m.maximum&&original.y_m>=region.y_m.minimum&&original.y_m<=region.y_m.maximum)el('text',{x:x(original.x_m),y:y(original.y_m)+6,'text-anchor':'middle',fill:'#ffffff'},'+');
 text('map-status',`${candidates.length} evaluated points at yaw ${yaw.toFixed(4)} rad; ${plotted} coarse-grid locations shown. No spatial interpolation.`);
}
function renderComparison(candidate){
 $('comparison').replaceChildren();if(!candidate)return;const original=state.initial,ev=candidate.evidence.evaluation;
 function margin(e){const values=(e?.nominal?.checks||[]).filter(c=>c.constraint==='joint_limits'&&c.margin!==null).map(c=>c.margin);return values.length?Math.min(...values).toFixed(4)+' rad':'Not available';}
 const table=document.createElement('table');for(const values of [['Evidence','Original','Selected'],['Classification',original?'See original diagnostics':'Not validated',candidate.classification.replaceAll('_',' ')],['Joint margin',margin(original),margin(ev)],['Relocation','0 m',candidate.evidence.relocation_m.toFixed(4)+' m'],['Recommendation','Engineer-controlled',candidate.id===state.recommended?'Best qualifying tested candidate':'Not authorized / not recommended']]){const row=document.createElement('tr');for(const v of values)row.append(node('td',v));table.append(row);}$('comparison').append(table);
}
async function telemetry(){try{const r=await fetch('/api/telemetry');if(!r.ok)throw new Error('telemetry unavailable');window.dispatchEvent(new CustomEvent('weldx-telemetry',{detail:await r.json()}));}catch(e){window.dispatchEvent(new CustomEvent('weldx-telemetry',{detail:{live:false,joint_positions:{}}}));}}
$('map-yaw').onchange=()=>renderMap(true);window.addEventListener('resize',()=>{if(state)renderMap(true);});
$('seam-select').onchange=()=>window.dispatchEvent(new CustomEvent('weldx-selection',{detail:{state,candidate:state?.candidates.find(c=>c.id===selected),seamId:$('seam-select').value}}));
$('source-select').onchange=()=>{if(state)showEvidence(state.candidates.find(c=>c.id===selected));};
setInterval(telemetry,300);telemetry();

async function inspectRecord(url,target){try{const r=await fetch(url);if(!r.ok)throw new Error('Evidence HTTP '+r.status);const body=await r.json();document.getElementById('evidence-dialog')?.remove();const dialog=document.createElement('dialog');dialog.id='evidence-dialog';const close=node('button','Close evidence');close.onclick=()=>dialog.close();const pre=node('pre',JSON.stringify(body,null,2));pre.className='full-record';dialog.append(close,pre);document.body.append(dialog);dialog.showModal();}catch(e){text('error',e.message);}}
