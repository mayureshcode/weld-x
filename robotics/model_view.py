"""Read-only robot visualization contract, derived from the actual runtime URDF."""
def model_view(cell):
    def vector(element,field,default):return list(map(float,element.get(field,default).split())) if element is not None else list(map(float,default.split()))
    links=[]
    for link in cell.urdf.findall('link'):
        visual=link.find('visual')
        if visual is None:continue
        mesh=visual.find('geometry/mesh');cylinder=visual.find('geometry/cylinder');item={'name':link.get('name'),'xyz':vector(visual.find('origin'),'xyz','0 0 0'),'rpy':vector(visual.find('origin'),'rpy','0 0 0')}
        if mesh is not None:item['mesh']='/assets/visual/'+mesh.get('filename').rsplit('/',1)[-1]
        elif cylinder is not None:item['cylinder']={'radius':float(cylinder.get('radius')),'length':float(cylinder.get('length'))}
        else:continue
        links.append(item)
    joints=[]
    for j in cell.urdf.findall('joint'):
        joints.append({'name':j.get('name'),'parent':j.find('parent').get('link'),'child':j.find('child').get('link'),'type':j.get('type'),'xyz':vector(j.find('origin'),'xyz','0 0 0'),'rpy':vector(j.find('origin'),'rpy','0 0 0'),'axis':vector(j.find('axis'),'xyz','0 0 1')})
    return {'links':links,'joints':joints,'length_unit':'m','source':'exact generated runtime URDF','robot_model_status':'provisional physical fidelity'}

def scene_evidence(adapter,config,evaluation,source='',scenario_id=''):
    """Read-only FK of exact cached plans and recorded scenario transforms.

    This never plans, mutates the simulator, measures a real TCP, or grants authority.
    """
    import numpy as np
    from scipy.spatial.transform import Rotation
    from .perturbation import perturb
    cached=adapter.plans.get(config.digest())
    if not cached or not evaluation or cached[0]!=evaluation.nominal.trajectory_id:
        return {'config_hash':config.digest(),'segments':[], 'scenario_preview':None,
            'reason':'No exact matching nominal trajectory is cached; nothing is fabricated.'}
    identity,segments=cached
    cache=getattr(adapter,'_scene_view_cache',{})
    if identity not in cache:
        rb=Rotation.from_euler('z',config.base.yaw_rad)
        paths=[]
        for name,t,info in segments:
            positions=[]
            for p in t.points:
                fk=adapter.cell.fk(dict(zip(t.joint_names,p.positions)))
                positions.append((rb.apply(fk[:3,3])+[config.base.x_m,config.base.y_m,config.base_height_m]).tolist())
            paths.append({'id':name,'world_tcp_points_m':positions,
                'time_s':[p.time_from_start.sec+p.time_from_start.nanosec*1e-9 for p in t.points]})
        cache[identity]=paths;adapter._scene_view_cache=cache
    preview=None
    trials=[t for t in evaluation.robustness.trials if t.scenario.source==source]
    selected=next((t for t in trials if t.scenario.id==scenario_id),None)
    if selected is None and trials:selected=next((t for t in trials if t.outcome.value=='fail'),trials[0])
    if selected:
        perturbed=perturb(config,selected.scenario);worst=None;maximum=-1.
        rb=Rotation.from_euler('z',config.base.yaw_rad);rp=Rotation.from_euler('z',perturbed.base.yaw_rad)
        rw=Rotation.from_euler('xyz',[config.workpiece.roll_rad,config.workpiece.pitch_rad,config.workpiece.yaw_rad])
        rwp=Rotation.from_euler('xyz',[perturbed.workpiece.roll_rad,perturbed.workpiece.pitch_rad,perturbed.workpiece.yaw_rad])
        for name,t,info in segments:
            if not name.endswith(':weld'):continue
            for p in t.points:
                fk=adapter.cell.fk(dict(zip(t.joint_names,p.positions)))
                nominal=rb.apply(fk[:3,3])+[config.base.x_m,config.base.y_m,config.base_height_m]
                local=rw.inv().apply(nominal-[config.workpiece.x_m,config.workpiece.y_m,config.workpiece.z_m])
                target=rwp.apply(local)+[perturbed.workpiece.x_m,perturbed.workpiece.y_m,perturbed.workpiece.z_m]
                actual=rp.apply(fk[:3,3]+fk[:3,:3]@np.array(selected.scenario.model[:3]))+[perturbed.base.x_m,perturbed.base.y_m,perturbed.base_height_m]
                delta=actual-target;size=float(np.linalg.norm(delta))
                if size>maximum:
                    maximum=size;worst={'segment':name,'target_world_m':target.tolist(),'predicted_actual_world_m':actual.tolist(),'delta_m':delta.tolist(),'norm_m':size}
        preview={'scenario':selected.scenario.__dict__,'outcome':selected.outcome.value,'evidence_kind':selected.evidence_kind,
            'base':perturbed.base.model_dump(),'fixture':perturbed.fixture.model_dump(),'workpiece':perturbed.workpiece.model_dump(),
            'worst_planned_residual':worst,'scope':'Predicted rigid-transform consequence of the selected recorded scenario; NOT measured TCP, compensation, or a simulator placement change.'}
    return {'config_hash':config.digest(),'trajectory_id':identity,'segments':cache[identity],
        'scenario_preview':preview,'scope':'Exact cached MoveIt trajectory FK in world metres, not executed feedback or interpolated feasibility.'}
