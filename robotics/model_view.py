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
