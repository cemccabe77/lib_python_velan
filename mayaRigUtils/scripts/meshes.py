import maya.cmds as cmds
from . import omUtil as omu


#____ update shape start
def auto_update(source, target):
    '''
    Using switch_shape() to update the orig shape on target
    '''
    if cmds.objectType(omu.get_dag_path(source, shape=True)) == 'mesh':
        if cmds.objectType(omu.get_dag_path(source, shape=True)) == cmds.objectType(omu.get_dag_path(target, shape=True)):
            blend_shape = cmds.blendShape(target, source, tc=True) # check if source and target are the same point count
            if blend_shape:
                cmds.delete(blend_shape)
                # print('switch to shape')
                go_switch_shape(target)
                blend_shape = cmds.blendShape(source, cmds.ls(sl=1)[1], foc=True, o='local', w=(0,1))
                cmds.refresh()
                cmds.delete(cmds.ls(sl=1)[1], ch=True)
                # print('switch back to output')
                go_switch_shape(target)

def switch_shape(node):
    '''
    Get all shape nodes. With this workflow, the first one is the real output mesh, 
    the second is normally the base mesh, and anything after that is history for the base mesh.
    We ignore anything after the second entry.
    '''

    shapes = cmds.listRelatives(node, shapes=True)
    if len(shapes) < 2:
        return False
        raise RuntimeError('Node doesn\'t have at least two shape nodes, nothing to switch:: %s' % str(node))

    shapes = shapes[0:2]
    # Find the current output shape.
    output_shapes = [s for s in shapes if cmds.getAttr(f'{s}.intermediateObject')]
    current_shape = cmds.listRelatives(node, shapes=True)
    if len(output_shapes) != 1:
        return False
        raise RuntimeError(f'Expected only one node to be active: {str(node)}')
        
    for shape in shapes:
        is_output = shape in output_shapes
        cmds.setAttr(f'{shape}.intermediateObject', (not is_output))

    return True

def go_switch_shape(node):
    cmds.undoInfo(openChunk=True, undoName='Switch shape')
    try:
        switch_shape(node)
    finally:            
        cmds.undoInfo(closeChunk=True)

def update_orig_multi(new_mesh, delete=False):
    '''
    Select new mesh objects. New mesh objects should have the 
    same name as the objects in the rig that need to be updated.
    
    new_mesh = ([])  List of mesh objects to be used, to update existing objects.
    delete   = (bol) Delete the new mesh objects after successfull update.
    '''

    fail_mesh = []
    for source in new_mesh:
        if not source.endswith('_mdlUpd'):
            source = cmds.rename(source, source.split('|')[-1]+'_mdlUpd') # long name rename due to duplicate objects
            target = source.split('|')[-1]
        else:
            source = source
            target = source.replace('_mdlUpd', '')


        if len(cmds.ls(target)) == 1: # Make sure only one object name exists in scene

            fail = 0 # Test for same vert, poly, edge count
            eval_target = cmds.polyEvaluate(target, v=1, e=1, f=1)
            eval_source = cmds.polyEvaluate(source, v=1, e=1, f=1)
            for k,v in eval_target.items():
                if v != eval_source.get(k):
                    fail = 1
            
            if fail==0: # Second round of topo checks
                compare = cmds.polyCompare([source, target], e=1, fd=1)  
                if compare != 0:  
                    # MGlobal.displayInfo('geos do NOT match')
                    fail_mesh.append(source.replace('_mdlUpd', ''))
                    cmds.rename(source, source.replace('_mdlUpd', '_FAILED'))
                else:  
                    # MGlobal.displayInfo('geos DO match')
                    go_switch_shape(target)
                    blend_shape = cmds.blendShape(source, target, foc=True, o='local', w=(0,1))
                    cmds.refresh()
                    cmds.delete(target, ch=True)
                    go_switch_shape(target)

                    if delete == True:
                        cmds.delete(source)
                    else:
                        cmds.rename(source, source.replace('_mdlUpd', '')+'_UPDATED')
        else:
            fail_mesh.append(source.replace('_mdlUpd', ''))

    if fail_mesh != []:
        cmds.warning(f'These objects could not be updated >> {fail_mesh}')
#____ update shape end


def constrain_to_mesh_follicle(constrained, mesh_name, orient=0): #WIP
    '''
    Constrains objects to closest point on mesh surface with follicle
   
    constrained = (str) Item to be constrained
    mesh_name   = (str) Surface that item will be constrained to
    orient      = (bol) Orient constrained to surface normal
    '''

    if cmds.objExists(mesh_name):
        mesh_shape = omu.get_dag_path(mesh_name, shape=1)
        if cmds.objectType(mesh_shape)=='mesh':
            point_on_surface_node = cmds.createNode('closestPointOnMesh', ss=True)

            # Connect nurbs surface to point_on_surface_node
            cmds.connectAttr(f'{mesh_name}.worldMesh[0]', f'{point_on_surface_node}.inMesh') 
            
            # Get world translate
            cmds.connectAttr(f'{constrained}.translate', f'{point_on_surface_node}.inPosition') 
            cmds.disconnectAttr(f'{constrained}.translate', f'{point_on_surface_node}.inPosition')

            follicle = cmds.createNode('follicle', n=f'{constrained[:-4]}_follicleShape', ss=True)
            
            # Get follicle transform
            follicle_transform = cmds.listRelatives(follicle, type='transform', p=True)

            # Follicle shape translate drives follicle transform translate
            cmds.connectAttr(f'{follicle}.outTranslate', f'{follicle_transform[0]}.translate')
            
            # Follicle shape rot drives follicle transform rot'
            cmds.connectAttr(f'{follicle}.outRotate', f'{follicle_transform[0]}.rotate')

            if orient:
                # Orient constrained to follicle
                cmds.connectAttr(f'{follicle_transform[0]}.rotate', f'{constrained}.rotate')


            # This will negate transforms and allow the follicle to be parented under the surface
            '''
            cmds.connectAttr(mesh_shape+'.worldMatrix', follicle+'.inputWorldMatrix')
            '''


            cmds.connectAttr(f'{mesh_shape}.worldMesh[0]', f'{follicle}.inputMesh')
            cmds.setAttr(f'{follicle}.simulationMethod', 0)
            cmds.setAttr(f'{follicle}.visibility', 0)

            # Connecting U,V param to follicle U,V param
            cmds.connectAttr(f'{point_on_surface_node}.result.parameterU', f'{follicle}.parameterU')
            cmds.connectAttr(f'{point_on_surface_node}.result.parameterV', f'{follicle}.parameterV')

            cmds.parent(constrained, follicle_transform[0])
            cmds.delete(point_on_surface_node) # Needs to be deleted

            return follicle, follicle_transform

def delete_unused_shapes_mesh():
    '''
    Removes all unused shape nodes in the scene
    '''

    all_meshes = []
    dead_intermediates = []
    all_meshes = cmds.ls(type="mesh")
    if all_meshes != {}:
        for mesh in all_meshes:
            if cmds.getAttr(f'{mesh}.io'): #intermediateObject
                if not cmds.listConnections(mesh):
                    dead_intermediates.append(mesh)

    if dead_intermediates != []:
        for intermediate in dead_intermediates:
            cmds.delete(intermediate)
        print(f'Deleted {str(len(dead_intermediates))} shape nodes')

    else:
        print('No unused shapes found')

def copy_vertex_position():
    # get the mesh vertex position
    selection = cmds.ls(sl=True)
    # get the dag path
    selection_list = om.MSelectionList()
    selection_list.add(selection[0])
    dag_path = selection_list.get_dag_path(0)
    # creating Mfn Mesh
    mfn_mesh = om.MFnMesh(dag_path)
    points = mfn_mesh.getPoints()

    return points

def paste_vertex_position(points):
    # set the mesh vertex position
    selection = cmds.ls(sl=True)
    # get the dag path
    selection_list = om.MSelectionList()
    selection_list.add(selection[0])
    dag_path = selection_list.get_dag_path(0)
    # creating Mfn Mesh
    mfn_mesh = om.MFnMesh(dag_path)
    mfn_mesh.setPoints(points)