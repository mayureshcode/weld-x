import * as THREE from '/vendor/three.module.min.js';
import {STLLoader} from '/vendor/STLLoader.js';
import {OrbitControls} from '/vendor/OrbitControls.js';
const host=document.getElementById('cell-view');
let renderer,scene,camera,controls,robot,groups={},joints=[],fixture,workpiece,seams,preview,loaded=false;
const status=document.getElementById('scene-status');
function pose(object,xyz,rpy){object.position.set(...xyz);object.rotation.set(...rpy,'XYZ');}
function solid(size,color){return new THREE.Mesh(new THREE.BoxGeometry(...size),new THREE.MeshStandardMaterial({color,metalness:.55,roughness:.5}));}
async function init(){
 const response=await fetch('/api/model');if(!response.ok)throw new Error('Runtime URDF not available');const model=await response.json();
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0x0b1420,1);renderer.outputColorSpace=THREE.SRGBColorSpace;host.replaceChildren(renderer.domElement);
 scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(38,1,.01,30);camera.up.set(0,0,1);camera.position.set(1.3,-1.45,1.05);controls=new OrbitControls(camera,renderer.domElement);controls.target.set(.25,0,.32);controls.enableDamping=true;
 scene.add(new THREE.HemisphereLight(0xcceeff,0x182434,2.5));const light=new THREE.DirectionalLight(0xffffff,4);light.position.set(1,-1,3);scene.add(light);
 const grid=new THREE.GridHelper(3,30,0x385d70,0x1e3243);grid.rotateX(Math.PI/2);grid.position.z=-.006;scene.add(grid);scene.add(new THREE.AxesHelper(.14));
 robot=new THREE.Group();scene.add(robot);groups.base_link=robot;
 joints=model.joints;
 // URDF order is not assumed: attach chains only when their parent exists.
 let pending=[...joints];for(let pass=0;pass<joints.length&&pending.length;pass++)pending=pending.filter(j=>{if(!groups[j.parent])return true;const origin=new THREE.Group(),motion=new THREE.Group();pose(origin,j.xyz,j.rpy);origin.add(motion);groups[j.parent].add(origin);groups[j.child]=motion;j.motion=motion;return false;});
 if(pending.length)throw new Error('Runtime model contains unresolved link hierarchy');
 const loader=new STLLoader();await Promise.all(model.links.map(async link=>{
  let geo;if(link.mesh)geo=await loader.loadAsync(link.mesh);else{geo=new THREE.CylinderGeometry(link.cylinder.radius,link.cylinder.radius,link.cylinder.length,20);geo.rotateX(Math.PI/2);}
  geo.computeVertexNormals();const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color:link.name==='base_link'?0xc88220:link.name.includes('torch')?0x96aab8:0xf3a32e,metalness:.55,roughness:.42}));pose(mesh,link.xyz,link.rpy);groups[link.name]?.add(mesh);
 }));
 fixture=solid([.22,.30,.20],0x42576a);workpiece=solid([.18,.24,.05],0x9eb2c3);scene.add(fixture,workpiece);seams=new THREE.Group();scene.add(seams);
 preview=new THREE.Mesh(new THREE.RingGeometry(.11,.12,60),new THREE.MeshBasicMaterial({color:0x67e8de,side:THREE.DoubleSide,transparent:true,opacity:.85}));preview.position.z=.002;preview.visible=false;scene.add(preview);
 const resize=()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};new ResizeObserver(resize).observe(host);resize();loaded=true;
 const animate=()=>{requestAnimationFrame(animate);controls.update();renderer.render(scene,camera);};animate();
 status.textContent='Observed joint feedback · drag to orbit · scroll to zoom';
}
function actualPose(object,value){if(!object||!value)return;object.position.set(...value.position);object.quaternion.set(...value.orientation);}
window.addEventListener('weldx-telemetry',e=>{
 const t=e.detail;if(!loaded)return;
 status.textContent=t.live?'Observed Gazebo joints and cell poses · not a substitute for execution evidence':'FEEDBACK STALE — displayed geometry is frozen';
 host.classList.toggle('stale',!t.live);
 for(const j of joints)if(j.type==='revolute'&&t.joint_positions[j.name]!==undefined)j.motion.quaternion.setFromAxisAngle(new THREE.Vector3(...j.axis),t.joint_positions[j.name]);
 actualPose(robot,t.robot_base_pose);actualPose(fixture,t.entity_poses?.fixture);actualPose(workpiece,t.entity_poses?.workpiece);
});
let lastJob='';window.addEventListener('weldx-selection',e=>{
 if(!loaded)return;const {state,candidate,seamId}=e.detail;const c=state.configuration;
 preview.visible=!!candidate;if(candidate)preview.position.set(candidate.base.x_m,candidate.base.y_m,.002);
 const key=state.config_hash+':'+(seamId||'');if(key===lastJob)return;lastJob=key;
 for(const child of [...seams.children]){seams.remove(child);child.geometry?.dispose();child.material?.dispose();}
 const wp=new THREE.Group();pose(wp,[c.workpiece.x_m,c.workpiece.y_m,c.workpiece.z_m],[c.workpiece.roll_rad,c.workpiece.pitch_rad,c.workpiece.yaw_rad]);
 for(const seam of c.job.seams){const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(seam.points_m.map(p=>new THREE.Vector3(...p))),new THREE.LineBasicMaterial({color:!seamId||seamId===seam.id?0x67e8de:0x506879}));wp.add(line);}seams.add(wp);
});
init().catch(error=>{status.textContent='3D view unavailable: '+error.message;host.textContent='No valid runtime model or WebGL connection. Execution remains backend-gated.';});
// Static engineering overlays from the exact cached backend plan. Robot motion
// remains exclusively observed telemetry; scenario predictions never move it.
let evidenceGroup=null,evidenceRequest=0,lastEvidenceKey='',lastEvidence=null;
function disposeGroup(group){if(!group)return;for(const child of [...group.children]){group.remove(child);child.geometry?.dispose();child.material?.dispose();}scene.remove(group);}
function drawEvidence(data,showPlanned){
 if(!loaded)return;disposeGroup(evidenceGroup);evidenceGroup=new THREE.Group();scene.add(evidenceGroup);
 if(showPlanned)for(const path of data.segments||[]){const colors={weld:0x67e8de,approach:0x6b9dd7,retreat:0xb79ee3,transition:0x879aa9};const kind=path.id.split(':').at(-1);const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(path.world_tcp_points_m.map(v=>new THREE.Vector3(...v))),new THREE.LineBasicMaterial({color:colors[kind]||0x879aa9}));evidenceGroup.add(line);}
 const p=data.scenario_preview,w=p?.worst_planned_residual;const label=document.getElementById('scene-evidence-status');
 if(w){const from=new THREE.Vector3(...w.target_world_m),delta=new THREE.Vector3(...w.delta_m);if(delta.length()>1e-12)evidenceGroup.add(new THREE.ArrowHelper(delta.clone().normalize(),from,delta.length()*50,0xffaa71,.008,.004));
  label.textContent=`${data.segments.length} exact planned segments · ${p.scenario.id} · predicted residual ${(w.norm_m*1000).toFixed(3)} mm · error arrow ×50 for visibility. Prediction only; no compensation or scene application.`;
 }else label.textContent=data.segments?.length?`${data.segments.length} exact cached planned TCP paths in world metres; not execution evidence. Approach blue · weld teal · retreat purple · transition gray.`:data.reason||'No exact trajectory evidence available.';
}
window.addEventListener('weldx-evidence-selection',async event=>{
 const v=event.detail,key=JSON.stringify([v.candidateId,v.source,v.scenarioId]);if(key===lastEvidenceKey&&lastEvidence){drawEvidence(lastEvidence,v.showPlanned);return;}
 lastEvidenceKey=key;const request=++evidenceRequest;const q=new URLSearchParams();if(v.candidateId)q.set('candidate_id',v.candidateId);if(v.source)q.set('source',v.source);if(v.scenarioId)q.set('scenario_id',v.scenarioId);
 try{const r=await fetch('/api/scene-evidence?'+q);if(!r.ok)throw new Error('scene evidence HTTP '+r.status);const data=await r.json();if(request!==evidenceRequest)return;lastEvidence=data;drawEvidence(data,v.showPlanned);}catch(error){if(request===evidenceRequest){disposeGroup(evidenceGroup);evidenceGroup=null;document.getElementById('scene-evidence-status').textContent='Scene evidence unavailable: '+error.message;}}
});
