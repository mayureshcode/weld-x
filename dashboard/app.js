'use strict';
let state=null, token=null, selected=null;
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
 const ev=evidence(candidate);const checks=ev?.nominal?.checks||[];
 const counts={pass:0,fail:0,unknown:0};for(const c of checks)counts[c.result]++;
 text('diagnostic-summary',checks.length?`${counts.pass} pass / ${counts.fail} fail / ${counts.unknown} unknown — ${checks.length} checks`:'No complete validation evidence. Execution remains blocked.');
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
 text('count',`${state.candidates.length} EVALUATED`);$('candidates').replaceChildren();
 for(const candidate of state.candidates){const row=document.createElement('tr');const b=candidate.base;for(const value of [candidate.id.slice(0,10),`${b.x_m.toFixed(3)} / ${b.y_m.toFixed(3)}`,b.yaw_rad.toFixed(3),candidate.classification.replaceAll('_',' ')])row.append(node('td',value));const cell=document.createElement('td');const button=node('button','Inspect');button.onclick=()=>{selected=candidate.id;render();};cell.append(button);row.append(cell);$('candidates').append(row);}
 if(!state.candidates.length){const row=document.createElement('tr');const cell=node('td','No placements evaluated. Run detection, then search.');cell.colSpan=5;row.append(cell);$('candidates').append(row);}
 const candidate=state.candidates.find(x=>x.id===selected);$('candidate-detail').replaceChildren();if(candidate){$('candidate-detail').append(node('h3','Selected candidate: '+candidate.id.slice(0,10)));const pre=node('pre',JSON.stringify(candidate.evidence,null,2));$('candidate-detail').append(pre);}
 showEvidence(candidate);$('approval-form').hidden=!state.recommended;$('approve').disabled=busy||state.stage!=='RECOMMEND';$('apply').disabled=busy||!state.approval;
 $('audit').replaceChildren();for(const entry of [...state.audit].reverse()){const row=node('div','');row.className='record';row.append(node('strong',`${String(entry.sequence).padStart(3,'0')} / ${entry.kind}`),node('span',new Date(entry.time_unix_s*1000).toISOString()+' · '+entry.digest.slice(0,16)));$('audit').append(row);}
}
async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw new Error(`API ${response.status}`);state=await response.json();render();}catch(error){text('connection','BACKEND DISCONNECTED');$('connection').className='tag bad';text('authorization','LOCKED');text('authreason','Backend unreachable. Displayed records may be stale.');text('error',error.message);for(const button of document.querySelectorAll('button'))button.disabled=true;}}
for(const action of ['detect','search','revalidate','execute','cancel'])$(action).onclick=()=>post(action);
$('approve').onclick=()=>post('approve',{candidate_id:state.recommended,config_hash:state.config_hash,engineer:$('engineer').value});
$('apply').onclick=()=>post('apply',{approval_id:state.approval.id});
(async()=>{try{const r=await fetch('/api/session');token=(await r.json()).csrf_token;}catch(error){text('error','Session initialization failed: '+error.message);}await refresh();setInterval(refresh,1500);})();
