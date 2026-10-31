import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const container=document.getElementById('workcell-canvas');
const message=document.getElementById('workcell-message');
const badge=document.getElementById('workcell-model-status');
const telemetry=document.getElementById('workcell-telemetry');
let camera,controls,renderer,model,frameId=0,disposed=false;
const scene=new THREE.Scene();
scene.background=new THREE.Color('#171b1a');
scene.fog=new THREE.Fog('#171b1a',18,50);
const hemi=new THREE.HemisphereLight(0xfff0d7,0x3c4750,2.4);scene.add(hemi);
const key=new THREE.DirectionalLight(0xffebcb,3.2);key.position.set(7,10,6);scene.add(key);
const fill=new THREE.DirectionalLight(0x72a3a9,1.8);fill.position.set(-8,5,-5);scene.add(fill);
const ground=new THREE.GridHelper(24,36,0x5b5348,0x353d3b);ground.position.y=-0.04;scene.add(ground);
const gridMarker=new THREE.AxesHelper(0.5);scene.add(gridMarker);
function show(text,type='offline'){message.textContent=text;badge.textContent=type==='loaded'?'MODEL LOADED':type==='loading'?'LOADING':'MODEL OFFLINE';badge.dataset.state=type}
function resize(){
 if(!renderer||!camera)return;
 const width=Math.max(240,container.clientWidth),height=Math.max(220,container.clientHeight);
 camera.aspect=width/height;camera.updateProjectionMatrix();renderer.setSize(width,height,false);
}
function view(kind='iso'){
 if(!model||!camera)return;
 const box=new THREE.Box3().setFromObject(model),center=box.getCenter(new THREE.Vector3());
 const size=box.getSize(new THREE.Vector3()),dist=Math.max(3,size.length()*0.94);
 const p=kind==='top'?new THREE.Vector3(0,dist,0.001):kind==='front'?new THREE.Vector3(0,size.y*0.22,dist):new THREE.Vector3(dist*0.75,dist*0.62,dist*0.85);
 camera.position.copy(center).add(p);camera.lookAt(center);controls.target.copy(center);controls.update();
}
try{
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
 renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
 renderer.outputColorSpace=THREE.SRGBColorSpace;
 renderer.toneMapping=THREE.ACESFilmicToneMapping;
 renderer.toneMappingExposure=1.2;
 container.appendChild(renderer.domElement);
 camera=new THREE.PerspectiveCamera(42,1,0.015,250);
 controls=new OrbitControls(camera,renderer.domElement);
 controls.enableDamping=true;controls.dampingFactor=0.075;controls.maxPolarAngle=Math.PI*0.93;
 resize();
 const observer=new ResizeObserver(resize);observer.observe(container);
 const animate=()=>{if(disposed)return;frameId=requestAnimationFrame(animate);controls.update();renderer.render(scene,camera)};
 animate();
 show('Importing the original workcell GLB (visual reference only).','loading');
 const response=await fetch('/assets/workcell.glb',{cache:'no-store'});
 if(!response.ok)throw new Error(response.status===404?'GLB not installed in assets/source.':'Model HTTP '+response.status);
 const buffer=await response.arrayBuffer();
 const loader=new GLTFLoader();
 const gltf=await new Promise((resolve,reject)=>loader.parse(buffer,'',resolve,reject));
 model=gltf.scene;scene.add(model);
 const box=new THREE.Box3().setFromObject(model),size=box.getSize(new THREE.Vector3());
 // Imported glTF uses Y-up. The original mesh and robot are never manipulated or animated.
 ground.position.y=box.min.y-0.012;
 gridMarker.position.set(box.min.x,box.min.y,box.min.z);
 controls.minDistance=0.25;controls.maxDistance=Math.max(6,size.length()*5);
 view();
 show('Actual uploaded workcell mesh • static visual asset; no articulated robot binding','loaded');
 document.getElementById('workcell-dimensions').textContent='Scene bounds: '+[size.x,size.y,size.z].map(v=>v.toFixed(2)).join(' × ')+' (unverified units)';
}catch(error){show('3D viewer unavailable: '+error.message);console.error('WELD-X viewer error:',error)}
for(const button of document.querySelectorAll('[data-workcell-view]'))button.addEventListener('click',()=>view(button.dataset.workcellView));
let telemetryAlive=false;
function text(id,value){document.getElementById(id).textContent=value}
async function pollTelemetry(){
 try{
  const response=await fetch('/api/telemetry',{cache:'no-store'});
  if(!response.ok)throw Error('HTTP '+response.status);
  const t=await response.json();
  text('telemetry-source',t.connected?'ROS 2 TOPICS RECEIVED':'ROS 2 NOT CONNECTED');
  text('telemetry-age',t.connected?'Fresh sample · '+t.age_seconds.toFixed(1)+'s old':t.reason||'No live telemetry');
  text('telemetry-joints',String(t.joint_count||0));
  text('telemetry-frames',String(t.tf_count||0));
  const rows=Array.isArray(t.joints)?t.joints.slice(0,10):[];
  telemetry.replaceChildren();
  if(rows.length){for(const j of rows){const el=document.createElement('div');el.className='joint-readout';const label=document.createElement('span');label.textContent=j.name;const val=document.createElement('strong');val.textContent=Number(j.position).toFixed(3)+' rad';el.append(label,val);telemetry.append(el)}}
  else{const el=document.createElement('p');el.className='muted';el.textContent='No received joint states. A rendered mesh is not live robot motion.';telemetry.append(el)}
  telemetryAlive=t.connected;
 }catch(error){
  telemetryAlive=false;text('telemetry-source','BRIDGE UNAVAILABLE');text('telemetry-age',error.message);text('telemetry-joints','0');text('telemetry-frames','0');
 }
}
pollTelemetry();setInterval(pollTelemetry,1000);
window.addEventListener('pagehide',()=>{disposed=true;cancelAnimationFrame(frameId);renderer?.dispose()});
