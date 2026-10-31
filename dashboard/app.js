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
 $('diagnostics').replaceChildren();for(const c of checks.filter(c=>$('diagnostic-filter').value==='all'||c.result===$('diagnostic-filter').value).slice(0,150)){const row=node('div','');row.className='record';row.append(node('strong',`${c.segment} / ${c.constraint} — ${c.result.toUpperCase()}`),node('span',c.reason));$('diagnostics').append(row);}
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
 for(const candidate of state.candidates.filter(c=>$('candidate-filter').value==='all'||c.classification===$('candidate-filter').value)){const row=document.createElement('tr');if(candidate.id===selected)row.classList.add('selected-row');const b=candidate.base;for(const value of [candidate.id.slice(0,10),`${b.x_m.toFixed(3)} / ${b.y_m.toFixed(3)}`,b.yaw_rad.toFixed(3),candidate.classification.replaceAll('_',' ')])row.append(node('td',value));const cell=document.createElement('td');const button=node('button','Inspect');button.onclick=()=>{selected=candidate.id;render();};cell.append(button);row.append(cell);$('candidates').append(row);}
 if(!state.candidates.length){const row=document.createElement('tr');const cell=node('td','No placements evaluated. Run detection, then search.');cell.colSpan=5;row.append(cell);$('candidates').append(row);}
 const candidate=state.candidates.find(x=>x.id===selected);$('candidate-detail').replaceChildren();if(candidate){$('candidate-detail').append(node('h3','Selected candidate: '+candidate.id.slice(0,10)));const meta=node('div','');meta.className='inspection-meta';for(const detail of [candidate.classification.replaceAll('_',' '),`Relocation ${candidate.evidence.relocation_m?.toFixed(3) ?? '—'} m`,`Robustness ${candidate.evidence.evaluation.robustness.outcome}`])meta.append(node('span',detail));$('candidate-detail').append(meta);const details=document.createElement('details');details.append(node('summary','Expand raw validation evidence'),node('pre',JSON.stringify(candidate.evidence,null,2)));$('candidate-detail').append(details);}
 showEvidence(candidate);renderExplorer();$('approval-form').hidden=!state.recommended;$('approve').disabled=busy||state.stage!=='RECOMMEND';$('apply').disabled=busy||!state.approval;
 $('audit').replaceChildren();for(const entry of [...state.audit].reverse()){const row=node('div','');row.className='record';row.append(node('strong',`${String(entry.sequence).padStart(3,'0')} / ${entry.kind}`),node('span',new Date(entry.time_unix_s*1000).toISOString()+' · '+entry.digest.slice(0,16)));$('audit').append(row);}
}

const XNS='http://www.w3.org/2000/svg';
function xsvg(name,attributes={},value){const e=document.createElementNS(XNS,name);for(const [key,val] of Object.entries(attributes))e.setAttribute(key,String(val));if(value!==undefined)e.textContent=String(value);return e;}
function renderExplorer(){
 const c=state.configuration, items=state.candidates||[], base=c.base, bounds=state.search?.bounds||c.search;
 const svg=$('placement-plot');svg.replaceChildren(xsvg('title',{id:'plot-title'},'Candidate base positions'),xsvg('desc',{id:'plot-desc'},'Actual backend x and y candidate points, not collision geometry'));
 const all=[base,...items.map(v=>v.base)].filter(v=>Number.isFinite(v.x_m)&&Number.isFinite(v.y_m));
 if(!all.length)return;
 let xmin=Math.min(bounds.x_m.minimum,...all.map(v=>v.x_m)),xmax=Math.max(bounds.x_m.maximum,...all.map(v=>v.x_m));
 let ymin=Math.min(bounds.y_m.minimum,...all.map(v=>v.y_m)),ymax=Math.max(bounds.y_m.maximum,...all.map(v=>v.y_m));
 if(xmin===xmax){xmin-=0.5;xmax+=0.5;}if(ymin===ymax){ymin-=0.5;ymax+=0.5;}
 const L=60,T=18,W=424,H=240,px=x=>L+(x-xmin)/(xmax-xmin)*W,py=y=>T+H-(y-ymin)/(ymax-ymin)*H;
 svg.append(xsvg('rect',{x:L,y:T,width:W,height:H,rx:5,fill:'#0e2030',stroke:'#456075'}));
 for(let i=0;i<=4;i++){const x=L+i*W/4,y=T+i*H/4;svg.append(xsvg('line',{x1:x,y1:T,x2:x,y2:T+H,stroke:'#2d465a','stroke-dasharray':'3 5'}),xsvg('line',{x1:L,y1:y,x2:L+W,y2:y,stroke:'#2d465a','stroke-dasharray':'3 5'}));svg.append(xsvg('text',{x,y:280,fill:'#bbd0de','font-size':11,'text-anchor':'middle'},(xmin+i*(xmax-xmin)/4).toFixed(2)),xsvg('text',{x:50,y:y+4,fill:'#bbd0de','font-size':11,'text-anchor':'end'},(ymax-i*(ymax-ymin)/4).toFixed(2)));}
 svg.append(xsvg('text',{x:270,y:301,fill:'#c8dbe7','font-size':12,'text-anchor':'middle'},'X (m)'),xsvg('text',{x:14,y:140,fill:'#c8dbe7','font-size':12,transform:'rotate(-90 14 140)','text-anchor':'middle'},'Y (m)'));
 svg.append(xsvg('rect',{x:px(base.x_m)-6,y:py(base.y_m)-6,width:12,height:12,fill:'#91baff',stroke:'#e0eafa'}));
 for(const item of items){if(!Number.isFinite(item.base.x_m)||!Number.isFinite(item.base.y_m))continue;const type=item.classification,color=type==='robustly_feasible'?'#75d5a7':type==='validation_incomplete'?'#ffc775':'#ff9999';const g=xsvg('g',{role:'button',tabindex:'0','aria-label':'Inspect '+item.id.slice(0,10)+' '+type.replaceAll('_',' ')});if(item.id===state.recommended)g.append(xsvg('circle',{cx:px(item.base.x_m),cy:py(item.base.y_m),r:12,fill:'none',stroke:'#f6fbff','stroke-dasharray':'3 2'}));g.append(xsvg('circle',{cx:px(item.base.x_m),cy:py(item.base.y_m),r:item.id===selected?8:6,fill:color,stroke:item.id===selected?'white':'#142638','stroke-width':2}));g.append(xsvg('title',{},item.id.slice(0,10)+' · '+type+' · yaw '+item.base.yaw_rad.toFixed(3)));const select=()=>{selected=item.id;render();};g.addEventListener('click',select);g.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select();}});svg.append(g);}
 const health=state.health||{},online=health.adapter&&health.adapter!=='unavailable'&&health.gazebo==='connected'&&health.moveit==='connected';
 text('runtime-summary',online?'REPORTED ONLINE':'NOT READY');
 text('runtime-note',online?'Adapter status; verify measurement':'ROS / Gazebo / MoveIt unavailable');
 const ev=candidateEvidenceForSummary(),checks=ev?.nominal?.checks||[];
 text('validation-summary',!checks.length?'UNKNOWN':checks.some(x=>x.result==='fail')?'FAILED':checks.some(x=>x.result==='unknown')?'UNKNOWN':'CHECKS PASS');
 text('validation-note',checks.length?checks.length+' recorded checks; backend controls authorization':'No complete robotics evidence');
 text('candidate-summary',items.length);text('job-summary',c.job.id);text('job-note',c.job.seams.length+' seam(s) · model provisional');
 text('next-step',state.authorized?'Backend authorizes a single simulated execution.':state.stage==='DETECT'?'Next: inspect constraints and search within bounded limits.':state.stage==='MAP'&&!state.recommended?'No qualified solution: inspect failed / unknown evidence and runtime connections.':state.stage==='RECOMMEND'?'Next: inspect and approve the exact recommendation.':state.stage==='APPROVE'?'Next: apply the approved placement and revalidate.':state.stage==='APPLY'?'Next: revalidate the updated configuration.':state.stage==='STOPPED'?'Execution is blocked. Inspect final revalidation evidence.':'Next: run detection and inspect mandatory constraints.');
 $('copy-hash').disabled=!state.config_hash;
}
function candidateEvidenceForSummary(){const item=state.candidates.find(x=>x.id===selected);return item?item.evidence.evaluation:(state.final||state.initial);}

async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw new Error(`API ${response.status}`);state=await response.json();render();}catch(error){text('connection','BACKEND DISCONNECTED');$('connection').className='tag bad';text('authorization','LOCKED');text('authreason','Backend unreachable. Displayed records may be stale.');text('error',error.message);for(const button of document.querySelectorAll('button'))button.disabled=true;}}
for(const action of ['detect','search','revalidate','execute','cancel'])$(action).onclick=()=>post(action);
$('approve').onclick=()=>post('approve',{candidate_id:state.recommended,config_hash:state.config_hash,engineer:$('engineer').value});
$('apply').onclick=()=>post('apply',{approval_id:state.approval.id});
(async()=>{try{const r=await fetch('/api/session');token=(await r.json()).csrf_token;}catch(error){text('error','Session initialization failed: '+error.message);}await refresh();setInterval(refresh,1500);})();

$('candidate-filter').addEventListener('change',()=>{if(state)render();});
$('diagnostic-filter').addEventListener('change',()=>{if(state)render();});
$('copy-hash').addEventListener('click',async()=>{if(!state?.config_hash)return;try{await navigator.clipboard.writeText(state.config_hash);text('copy-hash','Copied');}catch(error){text('error','Clipboard unavailable; copy the displayed hash manually.');}});
