import * as THREE from '/vendor/three.module.min.js';
import { STLLoader } from '/vendor/STLLoader.js';
import { GLTFLoader } from '/vendor/GLTFLoader.js';
import { OrbitControls } from '/vendor/OrbitControls.js';

const host = document.getElementById('cell-view');
const status = document.getElementById('scene-status');
const $ = id => document.getElementById(id);
let renderer, scene, camera, controls, robot, fixture, workpiece, seams, candidateMarker;
let groups = {}, jointMeta = [], mode = 'unavailable', loaded = false, frameRadius = 1.6;
let sceneCenter = new THREE.Vector3(0, 0, .6), robotCenter = null;
let latestEvidence = null, evidenceGroup = null, lastJob = '', evidenceKey = '', evidenceRequest = 0;
let currentCamera = 'home', resizeObserver = null, disposed = false;

function setStatus(s) { status.textContent = s; }
function pose(object, xyz, rpy) { object.position.set(...xyz); object.rotation.set(...rpy, 'XYZ'); }
function addSurface(size, color) {
  return new THREE.Mesh(new THREE.BoxGeometry(...size),
    new THREE.MeshStandardMaterial({color, roughness: .7, metalness: .35}));
}
function setViewportLabel(label) { $('view-mode').textContent = label; }
function setAccuracy(label) { $('view-accuracy').textContent = label; }
function boxFor(object) {
  const bounds = new THREE.Box3().setFromObject(object);
  if (!bounds.isEmpty()) return bounds;
  return new THREE.Box3(new THREE.Vector3(-1,-1,0), new THREE.Vector3(1,1,1));
}
function frameObject(object) {
  const box = boxFor(object);
  box.getCenter(sceneCenter);
  frameRadius = Math.max(.7, box.getSize(new THREE.Vector3()).length() * .50);
  controls.target.copy(sceneCenter);
  setCamera('home');
}
function setCamera(preset = 'home') {
  if (!camera || !controls) return;
  currentCamera = preset;
  const center = preset === 'robot' && robotCenter ? robotCenter : sceneCenter;
  const r = preset === 'robot' ? Math.max(.65, frameRadius * .30) : frameRadius * 2.15;
  const directions = {
    home: new THREE.Vector3(1, -1.35, .83),
    top: new THREE.Vector3(.001, .001, 1),
    side: new THREE.Vector3(1.5, -.001, .44),
    robot: new THREE.Vector3(1.1, -1, .65)
  };
  const delta = (directions[preset] || directions.home).normalize().multiplyScalar(r);
  camera.position.copy(center.clone().add(delta));
  camera.near = Math.max(.01, frameRadius / 800);
  camera.far = Math.max(60, frameRadius * 120);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
  for (const el of document.querySelectorAll('[data-camera]')) {
    el.classList.toggle('selected', el.dataset.camera === preset);
    el.setAttribute('aria-pressed', String(el.dataset.camera === preset));
  }
}
function bootRenderer() {
  renderer = new THREE.WebGLRenderer({antialias:true, alpha:true, powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.8));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.28;
  renderer.setClearColor(0x0a131b, 1);
  renderer.setSize(Math.max(host.clientWidth,320), Math.max(host.clientHeight,320),false);
  host.replaceChildren(renderer.domElement);
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0b151d, .015);
  camera = new THREE.PerspectiveCamera(42, 1, .01, 1000);
  camera.up.set(0,0,1);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = .055;
  controls.minDistance = .12;
  controls.maxDistance = 150;
  controls.screenSpacePanning = true;
  scene.add(new THREE.HemisphereLight(0xd9e5f0,0x24303c,2.5));
  const key = new THREE.DirectionalLight(0xffeed5,4.1);
  key.position.set(3, -4, 9);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x8bafc7, 1.6);
  fill.position.set(-4,3,5);
  scene.add(fill);
  const grid = new THREE.GridHelper(14,28,0x52616e,0x283543);
  grid.rotation.x=Math.PI/2;
  grid.position.z=-.013;
  scene.add(grid);
  resizeObserver = new ResizeObserver(() => {
    const w=Math.max(1,host.clientWidth),h=Math.max(1,host.clientHeight);
    renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
  });
  resizeObserver.observe(host);
  function animate() {
    if(disposed) return;
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene,camera);
  }
  animate();
}
async function loadGLB(url) {
  setViewportLabel('STATIC GLB / CAD PREVIEW');
  setAccuracy('SOURCE GLB · NOT JOINT SYNCHRONIZED');
  setStatus('Loading actual WELD-X workcell GLB…');
  const asset = await new GLTFLoader().loadAsync(url);
  const workcell = new THREE.Group();
  workcell.rotation.x = Math.PI/2; // Matches the known Gazebo preview SDF conversion.
  workcell.add(asset.scene);
  scene.add(workcell);
  frameObject(workcell);
  const foundRobot = workcell.getObjectByName('WELDX_ROBOT_ROOT');
  if(foundRobot) robotCenter = boxFor(foundRobot).getCenter(new THREE.Vector3());
  setStatus('SOURCE GLB PREVIEW · Static custom robot and positioner. Drag to inspect; no motion is inferred.');
}
async function loadURDF() {
  const r=await fetch('/api/model');
  if(!r.ok) throw new Error('Live runtime robot model unavailable (HTTP '+r.status+')');
  const model=await r.json();
  setViewportLabel('ROS JOINT MODEL / LIVE');
  setAccuracy('EXACT RUNTIME URDF · PROVISIONAL FIDELITY');
  robot=new THREE.Group();scene.add(robot);groups={base_link:robot};
  jointMeta=model.joints;
  let pending=[...jointMeta];
  for(let pass=0;pass<jointMeta.length && pending.length;pass++) {
    pending=pending.filter(j=>{
      if(!groups[j.parent])return true;
      const origin=new THREE.Group(),motion=new THREE.Group();
      pose(origin,j.xyz,j.rpy);
      origin.add(motion);groups[j.parent].add(origin);groups[j.child]=motion;
      j.motion=motion;
      return false;
    });
  }
  if(pending.length)throw new Error('Incomplete runtime URDF link chain');
  const loader=new STLLoader();
  await Promise.all(model.links.map(async l=>{
    let geo;
    if(l.mesh)geo=await loader.loadAsync(l.mesh);
    else if(l.cylinder){
      geo=new THREE.CylinderGeometry(l.cylinder.radius,l.cylinder.radius,l.cylinder.length,24);
      geo.rotateX(Math.PI/2);
    }else return;
    geo.computeVertexNormals();
    const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({
      color:l.name.includes('torch')?0xb9c4ce:l.name==='base_link'?0xe0a64a:0xf3bd62,
      roughness:.45,metalness:.48
    }));
    mesh.name=l.name;
    pose(mesh,l.xyz,l.rpy);
    groups[l.name]?.add(mesh);
  }));
  fixture=addSurface([.22,.3,.2],0x405360);
  workpiece=addSurface([.18,.24,.05],0x98aebc);
  scene.add(fixture,workpiece);
  seams=new THREE.Group();scene.add(seams);
  candidateMarker=new THREE.Mesh(new THREE.RingGeometry(.10,.112,72),
    new THREE.MeshBasicMaterial({color:0xf0ad45,side:THREE.DoubleSide}));
  candidateMarker.position.z=.001;candidateMarker.visible=false;scene.add(candidateMarker);
  frameObject(robot);
  sceneCenter = new THREE.Vector3(.25,0,.3);
  frameRadius=1.2;setCamera('home');
  robotCenter = new THREE.Vector3(.05,0,.35);
  setStatus('Runtime URDF loaded. Waiting for observed Gazebo joint feedback.');
}
async function init() {
  bootRenderer();
  const response=await fetch('/api/viewer-meta');
  if(!response.ok)throw new Error('Viewer metadata unavailable');
  const info=await response.json();
  mode=info.mode;
  if(mode==='glb-preview') await loadGLB(info.workcell_mesh);
  else if(mode==='live-urdf') await loadURDF();
  else {
    setViewportLabel('VIEWER OFFLINE');
    setAccuracy('NO MEASURED MODEL AVAILABLE');
    setStatus('No real robotics adapter or workcell preview is active.');
    throw new Error('No authorized scene source');
  }
  loaded=true;
}
window.addEventListener('weldx-telemetry', e=>{
  const t=e.detail || {};
  if(mode==='glb-preview'){
    host.classList.remove('stale');
    // The source GLB is static. ROS joints cannot safely move its mesh.
    return;
  }
  if(!loaded || mode!=='live-urdf')return;
  const positions=t.joint_positions || {};
  const fresh=t.live === true;
  host.classList.toggle('stale',!fresh);
  setStatus(fresh?'LIVE · Observed Gazebo joints / scene poses — not execution evidence':
    'STALE FEEDBACK · Frozen last observed pose, do not infer motion.');
  if(!fresh) return;
  for(const j of jointMeta) if(j.type==='revolute' && Number.isFinite(positions[j.name])) {
    j.motion.quaternion.setFromAxisAngle(new THREE.Vector3(...j.axis),positions[j.name]);
  }
  actualPose(robot,t.robot_base_pose);
  actualPose(fixture,t.entity_poses?.fixture);
  actualPose(workpiece,t.entity_poses?.workpiece);
});
function actualPose(object,value) {
  if(!object||!value)return;
  const p=value.position,q=value.orientation;
  if(!Array.isArray(p)||!Array.isArray(q)||p.length!==3||q.length!==4)return;
  if(![...p,...q].every(Number.isFinite))return;
  object.position.set(...p);object.quaternion.set(...q);
}
window.addEventListener('weldx-selection',event=>{
  if(!loaded || mode!=='live-urdf')return;
  const {state,candidate,seamId}=event.detail;
  const c=state.configuration;
  candidateMarker.visible=!!candidate;
  if(candidate)candidateMarker.position.set(candidate.base.x_m,candidate.base.y_m,.001);
  const key=state.config_hash+':'+(seamId||'');
  if(key===lastJob)return;
  lastJob=key;
  for(const child of [...seams.children]) {
    seams.remove(child);
    child.traverse(obj=>{obj.geometry?.dispose();obj.material?.dispose();});
  }
  const wp=new THREE.Group();pose(wp,[c.workpiece.x_m,c.workpiece.y_m,c.workpiece.z_m],
    [c.workpiece.roll_rad,c.workpiece.pitch_rad,c.workpiece.yaw_rad]);
  for(const seam of c.job.seams){
    const line=new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(seam.points_m.map(v=>new THREE.Vector3(...v))),
      new THREE.LineBasicMaterial({color:(!seamId||seam.id===seamId)?0x59cbe9:0x42586b}));
    wp.add(line);
  }
  seams.add(wp);
});
function disposeEvidence() {
  if(!evidenceGroup || !scene)return;
  evidenceGroup.traverse(obj=>{obj.geometry?.dispose();obj.material?.dispose();});
  scene.remove(evidenceGroup);evidenceGroup=null;
}
function drawEvidence(data,showPlanned) {
  if(!loaded || mode!=='live-urdf')return;
  disposeEvidence();evidenceGroup=new THREE.Group();scene.add(evidenceGroup);
  if(showPlanned)for(const path of data.segments || []) {
    const colors={weld:0x59cbe9,approach:0x728ee3,retreat:0xb598ea,transition:0x8499a8};
    const type=path.id.split(':').at(-1);
    const points=(path.world_tcp_points_m||[]).map(v=>new THREE.Vector3(...v));
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),
      new THREE.LineBasicMaterial({color:colors[type]||0x8499a8}));
    evidenceGroup.add(line);
  }
  const e=data.scenario_preview,w=e?.worst_planned_residual;
  if(w) {
    const from=new THREE.Vector3(...w.target_world_m),delta=new THREE.Vector3(...w.delta_m);
    if(delta.length()>1e-12)evidenceGroup.add(new THREE.ArrowHelper(
      delta.clone().normalize(),from,delta.length()*50,0xffa97a,.008,.004));
    $('scene-evidence-status').textContent=
      `${data.segments.length} exact planned segments · ${e.scenario.id} · predicted residual ${(w.norm_m*1000).toFixed(3)} mm · error arrow ×50. Prediction only; not observed execution.`;
  } else {
    $('scene-evidence-status').textContent=data.segments?.length
      ? `${data.segments.length} cached planned TCP paths; not observed execution.`
      : data.reason || 'No exact trajectory evidence available.';
  }
}
window.addEventListener('weldx-evidence-selection',async e=>{
  if(mode==='glb-preview') {
    $('scene-evidence-status').textContent='Custom GLB preview is static and uncalibrated. Planned paths cannot be safely overlaid.';
    return;
  }
  if(mode!=='live-urdf')return;
  const v=e.detail,key=JSON.stringify([v.candidateId,v.source,v.scenarioId]);
  if(key===evidenceKey && latestEvidence){drawEvidence(latestEvidence,v.showPlanned);return;}
  evidenceKey=key;const request=++evidenceRequest;
  const q=new URLSearchParams();
  if(v.candidateId)q.set('candidate_id',v.candidateId);
  if(v.source)q.set('source',v.source);
  if(v.scenarioId)q.set('scenario_id',v.scenarioId);
  try{
    const r=await fetch('/api/scene-evidence?'+q);
    if(!r.ok)throw new Error('scene evidence HTTP '+r.status);
    const data=await r.json();
    if(request!==evidenceRequest)return;
    latestEvidence=data;drawEvidence(data,v.showPlanned);
  }catch(error){
    if(request===evidenceRequest){
      disposeEvidence();latestEvidence=null;
      $('scene-evidence-status').textContent='Scene evidence unavailable: '+error.message;
    }
  }
});
for(const button of document.querySelectorAll('[data-camera]')) {
  button.addEventListener('click',()=>setCamera(button.dataset.camera));
}
$('view-focus').addEventListener('click',()=>{
  const parent=document.querySelector('.workspace');
  const expanded=parent.classList.toggle('viewer-expanded');
  $('view-focus').textContent=expanded?'Restore panel':'Expand view';
  $('view-focus').setAttribute('aria-pressed',String(expanded));
});
window.addEventListener('pagehide',()=>{
  disposed=true;resizeObserver?.disconnect();controls?.dispose();renderer?.dispose();
});
init().catch(error=>{
  setViewportLabel('SCENE UNAVAILABLE');
  setAccuracy('NO VERIFIED 3D SCENE');
  setStatus('3D viewer unavailable: '+error.message);
  if(host && !renderer)host.textContent='No valid workcell visualization; execution stays backend-gated.';
});
