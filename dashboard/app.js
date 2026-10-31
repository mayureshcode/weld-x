'use strict';
let state=null,token=null,selected=null,renderSignature='';
const $=id=>document.getElementById(id),S='http://www.w3.org/2000/svg';
const statusNames={robustly_feasible:['Qualified','pass'],nominally_feasible_not_robust:['Not robust','fail'],nominally_infeasible:['Failed','fail'],validation_incomplete:['Unverified','unknown']};
const steps=['DETECT','SEARCH','MAP','RECOMMEND','APPROVE','APPLY','REVALIDATE','EXECUTE'];
const t=(id,value)=>{$(id).textContent=String(value??'—')};
const el=(tag,value='')=>{const x=document.createElement(tag);x.textContent=String(value);return x};
const svg=(tag,attrs={},value)=>{const x=document.createElementNS(S,tag);for(const[k,v]of Object.entries(attrs))x.setAttribute(k,String(v));if(value!==undefined)x.textContent=String(value);return x};
const pretty=value=>String(value??'—').replaceAll('_',' ');
const num=(x,d=3)=>typeof x==='number'&&Number.isFinite(x)?x.toFixed(d):'—';
const classification=c=>statusNames[c.classification]||['Unknown','unknown'];
function chip(label,type){let x=el('span',label);x.className='status-chip '+type;return x}
function details(id,rows){$(id).replaceChildren();for(const[k,v]of rows)$(id).append(el('dt',k),el('dd',v))}
function empty(id,n,message){const r=el('tr'),c=el('td',message);c.colSpan=n;r.append(c);$(id).replaceChildren(r)}
function currentEvaluation(){let c=state?.candidates?.find(x=>x.id===selected);return c?c.evidence?.evaluation:(state?.final||state?.initial)}
function counts(checks){const n={pass:0,fail:0,unknown:0};for(const c of checks)n[c.result in n?c.result:'unknown']++;return n}
function nextAction(s){
 if(s.authorized)return 'Backend gates permit one simulated execution; verify the exact configuration.';
 if(s.stage==='RECOMMEND')return 'Inspect the recommended placement, then request engineer approval.';
 if(s.stage==='APPROVE')return 'Apply the approved configuration, then revalidate.';
 if(s.stage==='APPLY')return 'Revalidate the new configuration before execution.';
 if(s.stage==='MAP'&&!s.recommended)return 'No qualified solution: inspect unknown/failed checks and search limits.';
 if(s.stage==='STOPPED')return 'Execution blocked: inspect the final revalidation evidence.';
 if(s.stage==='DETECT')return 'Inspect detection checks, then run bounded placement search.';
 return 'Run detection to establish a traceable baseline.';
}
function renderSummary(){
 const s=state,c=s.configuration,h=s.health||{};
 t('stage',s.stage);$('stage').className='pill '+(['READY','COMPLETE'].includes(s.stage)?'pill-good':s.stage==='STOPPED'?'pill-bad':'pill-neutral');
 t('authorization',s.authorized?'AUTHORIZED':'LOCKED');$('authorization-card').classList.toggle('authorized',!!s.authorized);
 t('authreason',s.authorized?'Exact configuration passed mandatory backend gates; authorization is single-use.':'Missing, unknown, failed or stale mandatory evidence prevents execution.');
 t('next-action',nextAction(s));t('version',`REVISION ${c.revision} / JOB ${c.job.id}`);
 const online=h.adapter&&h.adapter!=='unavailable'&&h.ros==='connected'&&h.gazebo==='connected'&&h.moveit==='connected';
 t('runtime-summary',online?'REPORTED ONLINE':'NOT READY');$('runtime-summary').className=online?'good':'warning';
 t('runtime-caption',online?'Verify the reported measurements':'Robotics adapter not commissioned');
 const check=currentEvaluation()?.nominal?.checks||[],n=counts(check);
 t('validation-summary',!check.length?'UNKNOWN':n.fail?'FAILED':n.unknown?'UNKNOWN':'CHECKS PASS');
 $('validation-summary').className=n.fail?'bad':n.unknown||!check.length?'warning':'good';
 t('validation-caption',check.length?`${n.pass} passed · ${n.fail} failed · ${n.unknown} unknown`:'No complete robotics evidence');
 t('candidate-summary',s.candidates.length);
 t('candidate-caption',`${s.candidates.filter(x=>classification(x)[1]==='pass').length} qualified · ${s.candidates.filter(x=>classification(x)[1]==='unknown').length} unverified`);
 t('job-summary',c.job.id);t('job-caption',`${c.job.seams.length} defined seam(s) · robot model provisional`);
 $('runtime-warning').querySelector('strong').textContent=online?'RUNTIME CONNECTION REPORTED':'SIMULATOR NOT COMMISSIONED';
 $('runtime-warning').querySelector('p').textContent=online?'Reported connections do not establish physical safety, welding quality or certification.':'ABB IRB120 remains provisional. ROS 2, MoveIt 2, Gazebo and welding execution are not verified. Search points are not proof of feasibility.';
}
function renderWorkflow(){
 const s=state,busy=s.task?.status==='running'||!!s.active_operation;
 for(const [id,on]of Object.entries({detect:!busy,search:!busy&&['DETECT','STOPPED','MAP','RECOMMEND'].includes(s.stage),revalidate:!busy&&['IDLE','DETECT','APPLY','STOPPED'].includes(s.stage),execute:!busy&&!!s.authorized&&s.stage==='READY',cancel:busy,approve:!busy&&s.stage==='RECOMMEND',apply:!busy&&!!s.approval&&s.stage==='APPROVE'}))$(id).disabled=!on||!token;
 let cur=steps.indexOf(s.stage),done=s.stage==='READY'?6:s.stage==='COMPLETE'?7:cur-1;
 for(const li of $('workflow').children){let i=steps.indexOf(li.dataset.stage);li.classList.toggle('current',i===cur);li.classList.toggle('completed',i<=done&&done>=0);if(i===cur)li.setAttribute('aria-current','step');else li.removeAttribute('aria-current')}
 t('task',s.task?`${pretty(s.task.operation)} · ${pretty(s.task.status)}${s.task.error?' — '+s.task.error:''}`:'No active task');
 $('task').parentElement.classList.toggle('active',busy);
}
function renderConnections(){
 const s=state,c=s.configuration;details('health',Object.entries(s.health||{}).map(([k,v])=>[pretty(k),pretty(v)]));
 details('configuration',[['Robot',pretty(c.robot)],['Model',c.model_version],['Job / seams',`${c.job.id} / ${c.job.seams.length}`],['Base X / Y',`${num(c.base.x_m)} / ${num(c.base.y_m)} m`],['Base yaw',num(c.base.yaw_rad)+' rad'],['MC threshold (declared)',num(c.uncertainty.success_threshold*100,1)+'%'],['MC count',c.uncertainty.mc_count]]);
 t('hash',s.config_hash);$('copy-hash').disabled=!s.config_hash;
}
function selectCandidate(id){selected=id;renderPlot();renderCandidates();renderEvidence()}
function renderPlot(){
 const s=state,target=$('placement-map'),b=s.search?.bounds||s.configuration.search;
 target.replaceChildren(svg('title',{id:'plot-title'},'Candidate base locations'),svg('desc',{id:'plot-description'},'Backend x and y coordinate comparison; not robot collision geometry.'));
 const all=[s.configuration.base,...s.candidates.map(c=>c.base)].filter(c=>Number.isFinite(c.x_m)&&Number.isFinite(c.y_m));if(!all.length)return;
 let xmin=Math.min(b.x_m.minimum,...all.map(v=>v.x_m)),xmax=Math.max(b.x_m.maximum,...all.map(v=>v.x_m)),ymin=Math.min(b.y_m.minimum,...all.map(v=>v.y_m)),ymax=Math.max(b.y_m.maximum,...all.map(v=>v.y_m));
 if(xmin>=xmax){xmin-=.5;xmax+=.5}if(ymin>=ymax){ymin-=.5;ymax+=.5}
 const L=58,T=21,W=419,H=252,px=x=>L+(x-xmin)/(xmax-xmin)*W,py=y=>T+H-(y-ymin)/(ymax-ymin)*H;
 target.append(svg('rect',{x:L,y:T,width:W,height:H,rx:5,fill:'#0c1c2a',stroke:'#395068'}));
 for(let i=0;i<=4;i++){let x=L+i*W/4,y=T+i*H/4;target.append(svg('line',{x1:x,y1:T,x2:x,y2:T+H,stroke:'#2c4357','stroke-dasharray':'3 6'}),svg('line',{x1:L,y1:y,x2:L+W,y2:y,stroke:'#2c4357','stroke-dasharray':'3 6'}),svg('text',{x,y:291,'text-anchor':'middle',fill:'#acb9c9','font-size':11},num(xmin+i*(xmax-xmin)/4,2)),svg('text',{x:48,y:y+4,'text-anchor':'end',fill:'#acb9c9','font-size':11},num(ymax-i*(ymax-ymin)/4,2)))}
 target.append(svg('text',{x:268,y:313,'text-anchor':'middle',fill:'#b2cbdb','font-size':12},'X (m)'),svg('text',{x:16,y:156,'text-anchor':'middle',fill:'#b2cbdb','font-size':12,transform:'rotate(-90 16 156)'},'Y (m)'));
 const o=s.configuration.base;target.append(svg('rect',{x:px(o.x_m)-6,y:py(o.y_m)-6,width:12,height:12,rx:2,fill:'#91baff',stroke:'#c5ddff'}));
 for(const c of [...s.candidates.filter(c=>c.id!==selected),...s.candidates.filter(c=>c.id===selected)]){
  const tone=classification(c)[1],color=tone==='pass'?'#67d6a1':tone==='fail'?'#ff9e9e':'#f4c777';
  const g=svg('g',{class:'plot-point',role:'button',tabindex:0,'aria-label':`Inspect ${c.id.slice(0,10)} ${pretty(c.classification)}`});
  if(c.id===s.recommended)g.append(svg('circle',{cx:px(c.base.x_m),cy:py(c.base.y_m),r:12,fill:'none',stroke:'#fff','stroke-dasharray':'3 2'}));
  g.append(svg('circle',{cx:px(c.base.x_m),cy:py(c.base.y_m),r:c.id===selected?8:6,fill:color,stroke:c.id===selected?'#fff':'#102237','stroke-width':2}),svg('title',{},`${c.id.slice(0,10)} yaw ${num(c.base.yaw_rad)} rad`));
  g.addEventListener('click',()=>selectCandidate(c.id));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectCandidate(c.id)}});target.append(g);
 }
}
function renderCandidates(){
 const list=state.candidates,mode=$('candidate-filter').value,filtered=list.filter(c=>mode==='all'||classification(c)[1]===mode);
 t('count',list.length+' EVALUATED');$('candidates').replaceChildren();
 for(const c of filtered){const tr=el('tr');if(c.id===selected)tr.className='selected';
  for(const value of [c.id.slice(0,10),`${num(c.base.x_m)} / ${num(c.base.y_m)}`,num(c.base.yaw_rad)])tr.append(el('td',value));
  const ev=el('td'),[name,tone]=classification(c);ev.append(chip(name,tone));tr.append(ev);
  const last=el('td'),button=el('button','Inspect');button.className='mini-button';button.addEventListener('click',()=>selectCandidate(c.id));last.append(button);tr.append(last);$('candidates').append(tr);
 }
 if(!filtered.length)empty('candidates',5,list.length?'No records match your filter.':'Run detection and search to evaluate candidate positions.');
 const c=list.find(c=>c.id===selected),dest=$('candidate-detail');dest.replaceChildren();
 if(c){const ev=c.evidence?.evaluation,checks=ev?.nominal?.checks||[],n=counts(checks);
  dest.append(el('h3','Selected candidate · '+c.id.slice(0,12)));const grid=el('div');grid.className='inspector-grid';
  for(const [key,val]of [['Classification',classification(c)[0]],['Relocation',num(c.evidence?.relocation_m)+' m'],['Nominal checks',`${n.pass} pass / ${n.fail} fail / ${n.unknown} unknown`],['Robustness',pretty(ev?.robustness?.outcome||'unknown')]]){const d=el('div');d.className='inspector-stat';d.append(el('span',key),el('strong',val));grid.append(d)}dest.append(grid);
  const detailsEl=el('details');detailsEl.append(el('summary','Show complete raw candidate evidence'),el('pre',JSON.stringify(c.evidence,null,2)));dest.append(detailsEl);
 }else dest.append(el('p',list.length?'Select a candidate to inspect its evidence.':'No evaluated candidates yet.'));
 $('approval-form').hidden=!state.recommended;
}
function renderEvidence(){
 const ev=currentEvaluation(),checks=ev?.nominal?.checks||[],n=counts(checks);
 t('diagnostic-summary',checks.length?`${n.pass} pass · ${n.fail} fail · ${n.unknown} unknown / ${checks.length} recorded checks. Missing gates block execution.`:'No complete validation evidence. Execution remains blocked.');
 $('diagnostics').replaceChildren();const matches=checks.filter(c=>$('diagnostic-filter').value==='all'||c.result===$('diagnostic-filter').value);
 for(const c of matches.slice(0,150)){const d=el('div');d.className='record';const h=el('div');h.className='record-title';h.append(el('strong',pretty(c.segment)+' · '+pretty(c.constraint)),chip(pretty(c.result).toUpperCase(),c.result==='pass'?'pass':c.result==='fail'?'fail':'unknown'));d.append(h,el('p',c.reason||'No reason provided'));if(Number.isFinite(c.margin))d.append(el('small','Reported margin: '+num(c.margin,4)));$('diagnostics').append(d)}
 if(!matches.length)$('diagnostics').append(el('div',checks.length?'No matches for this filter.':'No validation records.'));
 if(matches.length>150)$('diagnostics').append(el('p',`Showing 150 of ${matches.length} checks; full raw evidence in candidate inspector.`));
 $('sensitivity').replaceChildren();for(const group of ev?.robustness?.groups||[]){const tr=el('tr');for(const value of [pretty(group.source),`${group.mc_passed} / ${group.mc_tested} (required ${group.mc_expected}; ${group.mc_unknown} unknown)`,`${group.boundary_passed} / ${group.boundary_tested} (required ${group.boundary_expected})`])tr.append(el('td',value));const d=el('td');d.append(chip(pretty(group.outcome),group.outcome==='pass'?'pass':group.outcome==='fail'?'fail':'unknown'));tr.append(d);$('sensitivity').append(tr)}
 if(!ev?.robustness?.groups?.length)empty('sensitivity',4,'No scenario records available.');
}
function renderAudit(){
 const dest=$('audit'),entries=state.audit||[];dest.replaceChildren();
 for(const e of [...entries].reverse().slice(0,80)){const d=el('div');d.className='record';d.append(el('strong',`${String(e.sequence).padStart(3,'0')} / ${pretty(e.kind)}`));d.append(el('small',`${Number.isFinite(e.time_unix_s)?new Date(e.time_unix_s*1000).toLocaleString():'No timestamp'} · hash ${String(e.digest||'').slice(0,16)}`));dest.append(d)}
 if(entries.length>80)dest.append(el('div',`Showing 80 of ${entries.length} records; complete history remains in backend.`));
 if(!entries.length)dest.append(el('div','No journal events.'));
}
function render(){if(!state)return;renderSummary();renderWorkflow();renderConnections();renderPlot();renderCandidates();renderEvidence();renderAudit()}
function disconnected(message){
 t('connection','BACKEND DISCONNECTED');$('connection').className='pill pill-bad';t('authorization','LOCKED');$('authorization-card').classList.remove('authorized');t('authreason','Backend unreachable; displayed records may be stale.');t('next-action','Restore the backend connection.');t('runtime-summary','DISCONNECTED');t('error',message);
 for(const b of document.querySelectorAll('button'))b.disabled=true;state=null;renderSignature='';
}
async function refresh(){
 try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error('Backend HTTP '+r.status);const incoming=await r.json();if(!incoming?.configuration||!Array.isArray(incoming.candidates))throw Error('Invalid backend snapshot');state=incoming;t('connection','API CONNECTED');$('connection').className='pill pill-good';
 const sig=JSON.stringify([state.stage,state.authorized,state.config_hash,state.candidates.map(c=>[c.id,c.classification]),state.recommended,state.approval?.id,state.audit?.length,state.task?.status,state.task?.error,state.active_operation,state.final?.elapsed_s,JSON.stringify(state.health)]);
 if(sig!==renderSignature){render();renderSignature=sig}if(!token)for(const b of document.querySelectorAll('.action-row button'))b.disabled=true;
 }catch(e){disconnected(e.message)}
}
async function post(route,body={}){
 if(!state||!token){t('error','No active backend session.');return}t('error','');
 try{const r=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-Weldx-Token':token},body:JSON.stringify(body)});const result=await r.json();if(!r.ok)throw Error(result.error||'HTTP '+r.status);await refresh()}catch(e){t('error',e.message)}
}
for(const action of ['detect','search','revalidate','execute','cancel'])$(action).addEventListener('click',()=>post(action));
$('approve').addEventListener('click',()=>post('approve',{candidate_id:state?.recommended,config_hash:state?.config_hash,engineer:$('engineer').value}));
$('apply').addEventListener('click',()=>post('apply',{approval_id:state?.approval?.id}));
$('candidate-filter').addEventListener('change',()=>{if(state)renderCandidates()});
$('diagnostic-filter').addEventListener('change',()=>{if(state)renderEvidence()});
$('copy-hash').addEventListener('click',async()=>{if(!state?.config_hash)return;try{await navigator.clipboard.writeText(state.config_hash);t('copy-hash','Copied')}catch{t('error','Clipboard unavailable: manually copy the displayed hash.')}});
(async()=>{try{const r=await fetch('/api/session');if(!r.ok)throw Error('HTTP '+r.status);token=(await r.json()).csrf_token;if(!token)throw Error('Session token missing')}catch(e){t('error','Session initialization failed: '+e.message)}await refresh();setInterval(refresh,1500)})();
