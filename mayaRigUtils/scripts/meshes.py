import maya.cmds as cmds
from . import omUtil as omu

#_____________________________________________________
#Switch Shape, to update Orig shape and keep deformers
def autoUpdate(source, target):
    '''
    Using switchShape() to update the orig shape on target
    '''
    if cmds.objectType(omu.getDagPath(source, shape=True)) == 'mesh':
        if cmds.objectType(omu.getDagPath(source, shape=True)) == cmds.objectType(omu.getDagPath(target, shape=True)):
            bndShp = cmds.blendShape(target, source, tc=True) # check if source and target are the same point count
            if bndShp:
                cmds.delete(bndShp)
                print('switch to shape')
                goSwitchShape(target)
                bndShp = cmds.blendShape(source, cmds.ls(sl=1)[1], foc=True, o='local', w=(0,1))
                cmds.refresh()
                cmds.delete(cmds.ls(sl=1)[1], ch=True)
                print('switch back to output')
                goSwitchShape(target)

def switchShape(node):
    # Get all shape nodes.  With this workflow, the first one is the real output mesh, the second is normally the base mesh,
    # and anything after that is history for the base mesh.  We ignore anything after the second entry.
    shapes = cmds.listRelatives(node, shapes=True)
    # shapes = node.getShapes()
    if len(shapes) < 2:
        return False
        raise RuntimeError('Node doesn\'t have at least two shape nodes, nothing to switch:: %s' % str(node))
    

    shapes = shapes[0:2]
    # Find the current output shape.
    output_shapes = [s for s in shapes if cmds.getAttr(f'{s}.intermediateObject')]
    current_shape = cmds.listRelatives(node, shapes=True)
    if len(output_shapes) != 1:
        return False
        raise RuntimeError('Expected only one node to be active: %s' % str(node))
        
    for shape in shapes:
        is_output = shape in output_shapes
        cmds.setAttr(f'{shape}.intermediateObject', (not is_output))
        # shape.attr('intermediateObject').set(not is_output)
        if is_output == True:
            print(shape)
    return True

def goSwitchShape(node):
    cmds.undoInfo(openChunk=True, undoName='Switch shape')
    try:
        switchShape(node)
    finally:            
        cmds.undoInfo(closeChunk=True)

def updateOrigMulti(newMsh, delete=False):
    '''
    Select new mesh objects. New mesh objects should have the 
    same name as the objects in the rig that need to be updated.
    
    newMsh = ([])  List of mesh objects to be used, to update existing objects.
    delete = (bol) Delete the new mesh objects after successfull update.
    '''

    failMsh = []
    for src in newMsh:
        if not src.endswith('_mdlUpd'):
            source = cmds.rename(src, src.split('|')[-1]+'_mdlUpd') # longname rename due to duplicate objects
            target = src.split('|')[-1]
        else:
            source = src
            target = src.replace('_mdlUpd', '')


        if len(cmds.ls(target)) == 1: # Make sure only one object name exists in scene

            fail = 0 # Test for same vert, poly, edge count
            evalT = cmds.polyEvaluate(target, v=1, e=1, f=1)
            evalS = cmds.polyEvaluate(source, v=1, e=1, f=1)
            for k,v in evalT.items():
                if v != evalS.get(k):
                    fail = 1
                    # print('Not even close, moving on')
            
            if fail==0: # Second round of topo checks
                comp = cmds.polyCompare([source, target],e=1, fd=1)  
                if comp != 0:  
                    # MGlobal.displayInfo('geos do NOT match')
                    failMsh.append(source.replace('_mdlUpd', ''))
                    cmds.rename(source, source.replace('_mdlUpd', '_FAILED'))
                else:  
                    # MGlobal.displayInfo('geos DO match')
                    goSwitchShape(target)
                    bndShp = cmds.blendShape(source, target, foc=True, o='local', w=(0,1))
                    cmds.refresh()
                    cmds.delete(target, ch=True)
                    goSwitchShape(target)

                    if delete == True:
                        cmds.delete(source)
                    else:
                        cmds.rename(source, source.replace('_mdlUpd', '')+'_UPDATED')
        else:
            failMsh.append(source.replace('_mdlUpd', ''))

    if failMsh != []:
        cmds.warning('These objects could not be updated')
        print(failMsh)
    else:
        print('All objects were updated without error')
        

#_____________________________________________________
#Tools
def constToMshFol(obj, mshName, orient=0): #WIP
    '''
    Constrains objects to closest point on mesh surface with follicle
   
    obj     = (str) Item to be constrained
    mshName = (str) Surface that item will be constrained to
    '''

    if cmds.objExists(mshName):
        mshShp = omu.getDagPath(mshName, shape=1)
        if cmds.objectType(mshShp)=='mesh':
            pntOnSrf = cmds.createNode('closestPointOnMesh', ss=True)
            cmds.connectAttr(mshName+'.worldMesh[0]', pntOnSrf+'.inMesh') # Connect nurbs surface to pntOnSrfPointOnSurface node

            cmds.connectAttr(obj+'.translate', pntOnSrf+'.inPosition') # get world translate
            cmds.disconnectAttr(obj+'.translate', pntOnSrf+'.inPosition')

            follicle = cmds.createNode('follicle', n=obj[:-4]+'_follicleShape', ss=True)
            follicleTrans = cmds.listRelatives(follicle, type='transform', p=True) # get follicle transform

            cmds.connectAttr(follicle+'.outTranslate', follicleTrans[0]+'.translate') # follicle shape translate drives follicle transform translate
            cmds.connectAttr(follicle+'.outRotate', follicleTrans[0]+'.rotate') # follicle shape rot drives follicle transform rot'

            if orient:
                # Orient obj to follicle
                cmds.connectAttr(follicleTrans[0]+'.rotate', obj+'.rotate')

            # cmds.connectAttr(mshShp+'.worldMatrix', follicle+'.inputWorldMatrix') # This will negate transforms and allow the follicle to be parented under the surface

            cmds.connectAttr(mshShp+'.worldMesh[0]', follicle+'.inputMesh')
            cmds.setAttr(follicle+'.simulationMethod', 0)
            cmds.setAttr(follicle+'.visibility', 0)

            cmds.connectAttr(pntOnSrf+'.result.parameterU', follicle+'.parameterU')# connecting U,V param to follicle U,V param
            cmds.connectAttr(pntOnSrf+'.result.parameterV', follicle+'.parameterV')

            cmds.parent(obj, follicleTrans[0])
            cmds.delete(pntOnSrf) # Needs to be deleted

            return follicle, follicleTrans

def smoothEdges(node):
    '''
    Uses switchShape to 'switch' to orig shape,
    if selection has deformer history.
    Then smooth edges.
    '''
    cmds.undoInfo(openChunk=True, undoName='Switch shape')
    try:
        if switchShape(node) == True: # switch to orig
            cmds.polySoftEdge(ch=False, a=180)
            switchShape(node) # need to switch back from orig shape
        else:
            cmds.polySoftEdge(ch=False, a=180)
    finally:            
        cmds.undoInfo(closeChunk=True)

def deleteUnusedShapesMsh():
    '''
    Removes all unused shape nodes in the scene
    '''
    allMeshes = []
    deadIntermediates = []
    allMeshes = cmds.ls(type="mesh") # List all shape nodes
    if allMeshes != {}:
        for mesh in allMeshes:
            if cmds.getAttr(mesh+'.io'): #intermediateObject
                if not cmds.listConnections(mesh):
                    deadIntermediates.append(mesh)

    if deadIntermediates != []:
        for io in deadIntermediates:
            cmds.delete(io)
        print('*** deleted '+str(len(deadIntermediates))+' shape nodes ***')

    else:
        print('*** No unused shapes found ***')

def copyVertexPosition():
    # get the mesh vertex position
    sel = cmds.ls(sl=True)
    # get the dag path
    selection_list = om.MSelectionList ()
    selection_list.add(sel[0])
    dag_path = selection_list.getDagPath (0)
    # creating Mfn Mesh
    mfn_mesh = om.MFnMesh(dag_path)
    points = mfn_mesh.getPoints()

    return points

def pasteVertexPosition(points):
    # set the mesh vertex position
    sel = cmds.ls(sl=True)
    # get the dag path
    selection_list = om.MSelectionList ()
    selection_list.add(sel[0])
    dag_path = selection_list.getDagPath (0)
    # creating Mfn Mesh
    mfn_mesh = om.MFnMesh(dag_path)
    mfn_mesh.setPoints(points)