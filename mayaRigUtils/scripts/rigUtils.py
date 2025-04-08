import maya.cmds as cmds
import maya.mel as mm
from maya.api.OpenMaya import MMatrix
import re
from . import omUtil as omu
from . import curves as crv
from . import surfaces as srf
from . import meshes as msh
from . import skincluster as skn
from lib_python_velan.mayaRigComponents.scripts import rdCtl as rdCtl



def rdctl_side_color(control, priority, margin=1.0):
    '''
    Sets rdCtl color based on world space on X axis
    control  = (instance) Class instance of rdCtl
    priority = (int or str) int = Primary or Secondary colors / str = color name.
    margin   = Units to define center X width
    '''

    if priority in [0,1,2]:
        # Get control world pos to determine color
        if -margin <= cmds.xform(control.topCtl, t=True, q=True, ws=True)[0] <= margin:
            control.color='lightYellow'
        elif cmds.xform(control.topCtl, t=True, q=True, ws=True)[0] < 0:
            if priority == 0:
                control.color='red'
            if priority == 1:
                control.color='lightRed'
            if priority == 2:
                control.color='pastelRed'

        else:
            if priority == 0:
                control.color='blue'
            if priority == 1:
                control.color='lightBlue'
            if priority == 2:
                control.color='pastelBlue'

    else:
        control.color = priority

def rdctl_on_vtx(vtx_dict={}, orient=0, margin=1.0, duplicate=0, duplicate_skin=1, duplicate_type='pp', 
                duplicate_name=None):
    '''
    Creates rdCtl's on selected vertex.

    vtx_dict  = ({})    vtx_dict[headCut_dorito1.vtx[49852], ctlName] = [orient, ctlShape, ctlSize, ctlColor, 
                        ctlSuffix, jntSuffix]
    orient    = (bol)   Orient ctls to surface
    margin    = (float) World space to color ctls
    duplicate = (bol)   Duplicate surface for dorito setup
    duplicate_skin   = (bol) Skin duplicate with ctl jnt's
    duplicate_type = (str) pp=pointPosition, bs=blendShape, omim=outMesh_inMesh
    duplicate_name = (str) Name to give the duplicate mesh
    '''

    mesh_name = list(vtx_dict)[0][0].split('.')[0] # Gets obj name from vertex

    control_list = []
    joint_list  = []
    follicle_list = []
    
    for vtx, settings in vtx_dict.items():
        pos = cmds.xform(vtx[0], q=1, ws=1, t=1)
        ctl = rdCtl.Control(vtx[1], shape=settings[1], size=settings[2], color='yellow', 
                            ctlSuffix=settings[4], jntSuffix=settings[5], match=None, parent=None, jt=True)
        cmds.xform(ctl.grp, ws=1, t=pos)
        fol = msh.constrain_to_mesh_follicle(constrained=ctl.grp, mesh_name=mesh_name, orient=settings[0])

        if settings[0]: # disconnect or result is double rotation
            cmds.disconnectAttr(fol[1][0]+'.rotate', ctl.grp+'.rotate')

        control_list.append(ctl)
        joint_list.append(ctl.jt)
        follicle_list.append(fol[1])
        rdctl_side_color(control=ctl, priority=settings[3], margin=margin)# Set color based on ws
    
    [cmds.setAttr(f'{jnt}.visibility', 0) for jnt in joint_list]
    [cmds.setAttr(f'{jnt}.radius', 0.1) for jnt in joint_list]

    if duplicate == 1:
        if duplicate_name:
            duplicate_mesh = cmds.duplicate(mesh_name, n=duplicate_name)[0]
            cmds.delete(duplicate_mesh, ch=True)
        else:
            duplicate_mesh = cmds.duplicate(mesh_name, n=f'{mesh_name}_dorito')[0]
            cmds.delete(duplicate_mesh, ch=True)

        if duplicate_skin == 1:
            sknCls = cmds.skinCluster([ctl.jt for ctl in control_list], duplicate_mesh, mi=2, bm=0, sm=0, dr=4, 
                                        wd=0, tsb=1, n=f'{duplicate_mesh}_doritoSkn')
            sknJts = skn.get_skin_cluster_influences(skin_cluster=sknCls[0])
            for ctl in control_list:
                 if ctl.jt in sknJts:
                    jntIdx = skn.get_skin_cluster_influence_index(skin_cluster=sknCls[0], influence=ctl.jt)
                    cmds.connectAttr(f'{ctl.grp}.worldInverseMatrix', f'{sknCls[0]}.bindPreMatrix[{jntIdx}]')

        if duplicate_type == 'pp':
             match_point_position(mesh_name, duplicate_mesh)
        if duplicate_type == 'bs':
            cmds.blendShape(mesh_name, duplicate_mesh, n=f'{mesh_name}_rdctl_on_vtx_bs', o='local', w=(0, 1.0))
        if duplicate_type == 'omim':
            outmesh_inmesh(mesh_name, duplicate_mesh)

        
    if duplicate == 1:
        if duplicate_skin == 1:
            return control_list, duplicate_mesh, follicle_list, sknCls
        else:
            return control_list, duplicate_mesh, follicle_list
    else:
        return control_list, follicle_list

def joint_on_vtx(joint_suffix):
    if not cmds.ls(sl=True): # Something needs to be selected
        raise TypeError('Make a vertex selection')
    if not cmds.filterExpand(sm=31): # Checks for vertex selection
        raise TypeError('Make a vertex selection')

    vertex_list = cmds.ls(sl=True, flatten=True)
    cmds.select(None)
    mesh_name = vertex_list[0].split('.')[0] # Gets obj name from vertex

    tra_list = []
    joint_list = []
    group_list = []

    for vtx in vertex_list:
        vertex_num = re.sub('[^A-Za-z0-9_]', '', vtx.split('.')[-1])+'_' # returns vtx+number
        pos = cmds.xform(vtx, q=1, ws=1, t=1)
        jnt = cmds.createNode('joint', n=f'{mesh_name}_{vertex_num}_{joint_suffix}', ss=True)
        joint_list.append(jnt)
        cmds.xform(jnt, ws=1, t=pos)
        follicle = msh.constrain_to_mesh_follicle(constrained=jnt, mesh_name=mesh_name, orient=True)
        tra_list.append(follicle[1][0])
        cmds.disconnectAttr(follicle[1][0]+'.rotate', jnt+'.rotate') # disconnect or result is double rotation
        follicle = cmds.createNode('transform', n=f'{mesh_name}_{vertex_num}_jntOnMsh', ss=True)
        group_list.append(follicle)
        cmds.parent(tra_list, follicle)
        parentConstraint(mesh_name, follicle, mo=True)

    return tra_list, joint_list, group_list

def rdctl_prebind_matrix(dorito_list, joint_suffix=None, buffer_suffix=None):
    '''
    Recives a list of rdCtls and object with rdJts in skincluster, as last selection.

    Looks for skincluster on last selection.
    Gets all joints in selection.
    Makes sure joints are in skincluster.
    Looks for joint bfr.
    Connects bfr worldInversMatrix to skincluster preBindMatrix.

    dorito_list = [] Selection of joints and obj with skincluster as last selection

    '''

    skin_cluster = skn.get_skin_clusters(mesh_name=dorito_list[-1])
    if not skin_cluster:
        raise AttributeError('Last selected object does not have a skinCluster')

    skin_joints = skn.get_skin_cluster_influences(skin_cluster=skin_cluster)

    # Get all selected joints
    joint_list = []
    for item in dorito_list:
        if cmds.objectType(item)=='joint':
            joint_list.append(item)

    # Make sure joints are in skincluster
    for joint in joint_list:
        if joint not in skin_joints:
            joint_list.remove(joint)

    # Connect pre bind matrix
    if joint_list != []:
        if 'mGear' in buffer_suffix:
            for joint in joint_list:
                joint_index = skn.get_skin_cluster_influence_index(skin_cluster=skin_cluster, influence=joint)
                joint_buffer = cmds.listConnections(f'{joint}.inv_wm_conn_{str(joint)}', d=True)[0]
                if joint_buffer:
                    cmds.connectAttr(f'{joint_buffer}.worldInverseMatrix', 
                        f'{skin_cluster}.bindPreMatrix[{joint_index}]', f=1)
            print('prebind_matrix connection was made')

        else:
            for joint in joint_list:
                joint_index = skn.get_skin_cluster_influence_index(skin_cluster=skin_cluster, influence=joint)
                joint_buffer = joint.replace(joint_suffix, buffer_suffix.split(' ')[0]) # Get joint bfr
                if joint_buffer:
                    cmds.connectAttr(f'{joint_buffer}.worldInverseMatrix', 
                        f'{skin_cluster}.bindPreMatrix[{joint_index}]', f=1)
            print('prebind_matrix connection was made')
    else:
        raise IndexError('Selected joints are not part of the skinCluster on last selection')
    
def lock_unlock_srt(objs, attrVis, lock, t=['x','y','z'], r=['x','y','z'], s=['x','y','z']):
    '''
    objs    = ([])  List of object names
    attrVis = (bol) Hide from channel box if false
    lock    = (bol) Lock attr
    t = (bol) Translate
    r = (bol) Rotate
    s = (bol) Scale
    '''

    if type(objs) != list:
        objs = [objs]

    for obj in objs:
        [cmds.setAttr(obj+'.t'+axis.lower(), k=attrVis, l=lock) for axis in t]
        [cmds.setAttr(obj+'.r'+axis.lower(), k=attrVis, l=lock) for axis in r]
        [cmds.setAttr(obj+'.s'+axis.lower(), k=attrVis, l=lock) for axis in s]

def hide_unhide_srt(objs, attrVis, t=['x','y','z'], r=['x','y','z'], s=['x','y','z']):
    if type(objs) != list:
        objs = [objs]

    for obj in objs:
        [cmds.setAttr(obj+'.t'+axis.lower(), k=attrVis) for axis in t]
        [cmds.setAttr(obj+'.r'+axis.lower(), k=attrVis) for axis in r]
        [cmds.setAttr(obj+'.s'+axis.lower(), k=attrVis) for axis in s]

def parentConstraint(parent=None, child=None, t=['x','y','z'], r=['x','y','z'], s=['x','y','z'], mo=True, pm=None):
    '''
    Node based parent constraint.

    parent = (str) Name of parent
    child  = (str) Name of child
    t      = []    List of axis to constrain to translate
    r      = []    List of axis to constrain to rotate
    s      = []    List of axis to constrain to scale
    mo     = (bol) Maintain offset option
    pm     = (plug) parent matrix plug (worldMatrix)
    '''

    # Parent can be defined by a parent matrix(pm) plug, instead of a transform
    if parent == None:
        if pm == None:
            raise AttributeError('No parent, or parent matrix (pm) defined')

    if type(child) != 'list':
        child = [child]

    if parent: # parent transform
        for c in child:
            mult_matrix_node = cmds.createNode('multMatrix', n=f'{parent}_multMatrix_rigUParCon', ss=True)
            decomp_node  = cmds.createNode('decomposeMatrix', n=f'{parent}_matrixDecomp_rigUParCon', ss=True)

            if mo == True:
                offset = cmds.createNode('multMatrix', n=f'{parent}_offset', ss=True)
                cmds.connectAttr(f'{c}.worldMatrix[0]', f'{offset}.matrixIn[0]', f=1)
                cmds.connectAttr(f'{parent}.worldInverseMatrix[0]', f'{offset}.matrixIn[1]', f=1)
                # Offset
                cmds.setAttr(f'{mult_matrix_node}.matrixIn[0]', cmds.getAttr(f'{offset}.matrixSum'), type='matrix')
                cmds.connectAttr(f'{parent}.worldMatrix[0]', f'{mult_matrix_node}.matrixIn[1]', f=1)
                cmds.connectAttr(f'{c}.parentInverseMatrix[0]', f'{mult_matrix_node}.matrixIn[2]', f=1)
                cmds.connectAttr(f'{mult_matrix_node}.matrixSum', f'{decomp_node}.inputMatrix', f=1)
                cmds.delete(offset)
            else:
                cmds.connectAttr(f'{parent}.worldMatrix[0]', f'{mult_matrix_node}.matrixIn[0]', f=1)
                cmds.connectAttr(f'{c}.parentInverseMatrix[0]', f'{mult_matrix_node}.matrixIn[1]', f=1)
                cmds.connectAttr(f'{mult_matrix_node}.matrixSum', f'{decomp_node}.inputMatrix', f=1)

            [cmds.connectAttr(f'{decomp_node}.outputTranslate{axis.upper()}', f'{c}.translate{axis.upper()}', f=1) for axis in t if axis]
            [cmds.connectAttr(f'{decomp_node}.outputRotate{axis.upper()}', f'{c}.rotate{axis.upper()}', f=1) for axis in r if axis]
            [cmds.connectAttr(f'{decomp_node}.outputScale{axis.upper()}', f'{c}.scale{axis.upper()}', f=1) for axis in s if axis]

            return decomp_node

    elif pm: # parent worldMatrix plug
        for c in child:
            mult_matrix_node = cmds.createNode('multMatrix', n=f'{c}_multMatrix_pm_rigUParCon', ss=True)
            decomp_node  = cmds.createNode('decomposeMatrix', n=f'{c}_matrixDecomp_pm_rigUParCon', ss=True)

            if mo == True:
                offset = cmds.createNode('multMatrix', n=f'{c}_parent_offset', ss=True)
                cmds.connectAttr(f'{c}.worldMatrix[0]', f'{offset}.matrixIn[0]', f=1)
                
                # convert pm to worldInverseMatrix
                inverse = cmds.createNode('inverseMatrix', n='plug_inverseMatrix', ss=True)
                cmds.connectAttr(pm, inverse+'.inputMatrix')
                cmds.connectAttr(inverse+'.outputMatrix', f'{offset}.matrixIn[1]', f=1)

                # Offset
                cmds.setAttr(f'{mult_matrix_node}.matrixIn[0]', cmds.getAttr(f'{offset}.matrixSum'), type='matrix')
                cmds.connectAttr(pm, f'{mult_matrix_node}.matrixIn[1]', f=1)
                cmds.connectAttr(f'{c}.parentInverseMatrix[0]', f'{mult_matrix_node}.matrixIn[2]', f=1)
                cmds.connectAttr(f'{mult_matrix_node}.matrixSum', f'{decomp_node}.inputMatrix', f=1)
                cmds.delete(offset)
            else:
                cmds.connectAttr(pm, f'{mult_matrix_node}.matrixIn[0]', f=1)
                cmds.connectAttr(f'{c}.parentInverseMatrix[0]', f'{mult_matrix_node}.matrixIn[1]', f=1)
                cmds.connectAttr(f'{mult_matrix_node}.matrixSum', f'{decomp_node}.inputMatrix', f=1)

            [cmds.connectAttr(f'{decomp_node}.outputTranslate{axis.upper()}', f'{c}.translate{axis.upper()}', f=1) for axis in t if axis]
            [cmds.connectAttr(f'{decomp_node}.outputRotate{axis.upper()}', f'{c}.rotate{axis.upper()}', f=1) for axis in r if axis]
            [cmds.connectAttr(f'{decomp_node}.outputScale{axis.upper()}', f'{c}.scale{axis.upper()}', f=1) for axis in s if axis]

            return decomp_node

def delete_parentConstraint(constrained=None):
    '''
    Delete node based parent constraint

    constrained (str) Name of obj to delete constraint from
    '''
    
    axisLst = ['.tx', '.ty', '.tz', '.rx', '.ry', '.rz', '.sx', '.sy', '.sz']

    if constrained:
        nde = None
        for axis in axisLst:
            if cmds.listConnections(constrained+axis):
                if '_rigUParCon' in cmds.listConnections(constrained+axis)[0]:
                    nde = cmds.listConnections(constrained+axis)[0]
        if nde != None:
            cmds.delete(nde)
    else:
        for sel in cmds.ls(sl=1):
            nde = None
            for axis in axisLst:
                if cmds.listConnections(sel+axis):
                    if '_rigUParCon' in cmds.listConnections(sel+axis)[0]:
                        nde = cmds.listConnections(sel+axis)[0]
            if nde != None:
                cmds.delete(nde)

def direct_connect_srt(source, destination, channels=['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']):
    [cmds.connectAttr(f'{source}.{axis}', f'{destination}.{axis}', f=1) for axis in channels if axis]

def outmesh_inmesh(source, target):
    '''
    Works for polymesh only.
    Connect source outMesh to target inMesh
    '''

    source_shape = omu.get_dag_path(source, shape=True)
    target_shapes = cmds.listRelatives(target, c=True, s=True)
    orig = None
    if target_shapes:
        for shape in target_shapes:
            if 'Orig' in shape:
                orig = shape
        if orig != None:
            target_shape = orig
        else:
            target_shape = omu.get_dag_path(target, shape=True)

    if source_shape and target_shape:
        cmds.connectAttr(f'{source_shape}.outMesh', f'{target_shape}.inMesh', f=True)

def match_point_position(driver, driven):
    '''
    Matches driven to drivers transforms and point position
    '''
    
    if cmds.objectType(omu.get_dag_path(driver, shape=1)) != cmds.objectType(omu.get_dag_path(driven, shape=1)):
        raise TypeError('Source and Target are not of the same type')

    source_shape = omu.get_dag_path(driver, shape=True)
    target_shape = omu.get_dag_path(driven, shape=True)


    # Polymesh
    if cmds.objectType(omu.get_dag_path(driver, shape=1)) == 'mesh':
        cmds.xform(driven, t=(0,0,0))
        transform_geo_node = cmds.createNode('transformGeometry', ss=True)
        cmds.connectAttr(f'{driver}.worldMatrix[0]', f'{transform_geo_node}.transform')
        cmds.connectAttr(f'{source_shape}.outMesh', f'{transform_geo_node}.inputGeometry')

        if cmds.listConnections(f'{target_shape}.inMesh') != None: # We have a deformer
            node_type = cmds.objectType(cmds.listConnections(f'{target_shape}.inMesh'))
            if node_type in ['skinCluster', 'blendShape']:
                shapes = cmds.listRelatives(driven, c=True, s=True)
                if shapes:
                    orig = None
                    for shape in shapes:
                        if 'Orig' in shape:
                            orig = shape
                    if orig:
                        target_shape = orig

                cmds.connectAttr(f'{transform_geo_node}.outputGeometry', f'{target_shape}.inMesh', f=1)
            else:
                raise TypeError('Unknown deformer present on shape node. Update rigU.match_point_position with new deformer.')
        else:
            cmds.connectAttr(f'{transform_geo_node}.outputGeometry', f'{target_shape}.inMesh', f=1)


    # Nurbs Surface
    if cmds.objectType(omu.get_dag_path(driver, shape=1)) == 'nurbsSurface':
        cmds.xform(driven, t=(0,0,0))
        transform_geo_node = cmds.createNode('transformGeometry', ss=True)
        cmds.connectAttr(f'{driver}.worldMatrix[0]', f'{transform_geo_node}.transform')
        cmds.connectAttr(f'{source_shape}.worldSpace[0]', f'{transform_geo_node}.inputGeometry')
        
        if cmds.listConnections(f'{target_shape}.create') != None: # We have a deformer
            node_type = cmds.objectType(cmds.listConnections(f'{target_shape}.create'))
            if node_type in ['skinCluster', 'blendShape']:
                shapes = cmds.listRelatives(driven, c=True, s=True)
                if shapes:
                    orig = None
                    for shape in shapes:
                        if 'Orig' in shape:
                            orig = shape
                    if orig:
                        target_shape = orig

                cmds.connectAttr(f'{transform_geo_node}.outputGeometry', f'{target_shape}.create', f=1)
            else:
                raise TypeError('Unknown deformer present on shape node. Update rigU.match_point_position with new deformer.')
        else:
            cmds.connectAttr(f'{transform_geo_node}.outputGeometry', f'{target_shape}.create', f=1)


    # Nurbs Curve
    if cmds.objectType(omu.get_dag_path(driver, shape=1)) == 'nurbsCurve':
        cmds.xform(driven, t=(0,0,0))
        transform_geo_node = cmds.createNode('transformGeometry', ss=True)
        cmds.connectAttr(f'{driver}.worldMatrix[0]', f'{transform_geo_node}.transform')
        cmds.connectAttr(f'{source_shape}.worldSpace[0]', f'{transform_geo_node}.inputGeometry')

        if cmds.listConnections(f'{target_shape}.create') != None: # We have a deformer
            node_type = cmds.objectType(cmds.listConnections(target_shape+'.create'))
            if node_type in ['skinCluster', 'blendShape']:
                shapes = cmds.listRelatives(driven, c=True, s=True)
                if shapes:
                    orig = None
                    for shape in shapes:
                        if 'Orig' in shape:
                            orig = shape
                    if orig:
                        target_shape = orig

                cmds.connectAttr(f'{transform_geo_node}.outputGeometry', f'{target_shape}.create', f=1)
            else:
                raise TypeError('Unknown deformer present on shape node. Update rigU.match_point_position with new deformer.')
        else:
            cmds.connectAttr(f'{transform_geo_node}.outputGeometry', f'{target_shape}.create', f=1)

######## Strap rigs
def ik_spline_on_curve(curve_name, count, suffix='jntSuffix'):
    '''
    curve_name = (str)
    count  = (int) Number of joints to build ik_spline
    suffix = (str)
    '''

    # IK chain with last joint hack fix
    ik_joint_list = crv.create_evenly_along_curve(object_type='joint', object_name=curve_name.replace('_srfCrv', ''), 
                    count=count, curve_name=curve_name, chain=1, keep_curve=1, suffix='splinejnt')
    last_ik_joint = cmds.duplicate(ik_joint_list[-1], 
                    n=curve_name.replace('_srfCrv', '')+'_{}_twistHelperHack'.format(len(ik_joint_list)))[0]
    cmds.parent(last_ik_joint, ik_joint_list[-1], r=0)
    cmds.joint(ik_joint_list[-1], zso=1, ch=1, e=1, oj='xyz', sao='yup')
    
    # One more joint to orient the 'last' joint hack fix
    last_ik_joint_orient = cmds.duplicate(last_ik_joint, n='lastOrient')
    cmds.parent(last_ik_joint_orient, last_ik_joint)
    cmds.joint(last_ik_joint, zso=1, ch=1, e=1, oj='xyz', sao='yup')
    cmds.delete(last_ik_joint_orient)
    cmds.setAttr(f'{last_ik_joint}.tx', cmds.getAttr(f'{ik_joint_list[-1]}.tx')/4)
    ik_joint_list.append(last_ik_joint)

    ikHdl = cmds.ikHandle(solver='ikSplineSolver', startJoint=ik_joint_list[0], endEffector=last_ik_joint, 
            rootTwistMode=0, n=curve_name.replace('_srfCrv', '')+'_ikSpline', createCurve=0, curve=curve_name, 
            simplifyCurve=False, rootOnCurve=True, parentCurve=False)

    return ik_joint_list, ikHdl

def ik_spline_curve_stretch(name, motion_nodes, spline_joints, attr_object):
    '''
    Uses joints, that are constrained to a curve by constrain_to_curve_parametric(),
    to drive position along curve for spline joints. Giving anim the option
    to turn off Maintain Length for the ik spline.

    name          = (str) Name to give new nodes created herein
    motion_nodes  = ([])  List of param joint motionPath nodes from create_evenly_along_curve()
    spline_joints = ([])  List of spline joints from ik_spline_on_curve()
    attr_object  = ([])  object that will receive the 'Maintain Length' attribute
    '''

    if not cmds.objExists(attr_object):
        raise NameError('attr_object obj does not exist in the scene')
    else:
        cmds.addAttr(attr_object, at='bool', k=True, ci=True, sn='MaintainLength', dv=1)

    for i, nde in enumerate(motion_nodes[:-1]):
        distBet = cmds.createNode('distanceBetween', n=f'{name}_ikDistBet_'+str(i), ss=True)
        distZero = cmds.createNode('floatMath', n=f'{name}_ikDistZero_'+str(i), ss=True)
        distDiff = cmds.createNode('floatMath', n=f'{name}_ikDistDiff_'+str(i), ss=True)
        rigScale = cmds.createNode('floatMath', n=f'{name}_rigScale'+str(i), ss=True)
        cmds.connectAttr(f'{motion_nodes[i]}.allCoordinates', f'{distBet}.point1')
        cmds.connectAttr(f'{motion_nodes[i+1]}.allCoordinates', f'{distBet}.point2')
        cmds.setAttr(f'{rigScale}.operation', 3) # divide
        cmds.setAttr(f'{distZero}.operation', 1) # subtract
        cmds.setAttr(f'{distDiff}.operation', 1) # subtract
        cmds.setAttr(f'{distZero}.floatA', cmds.getAttr(f'{distBet}.distance'))
        cmds.connectAttr(f'{distBet}.distance', f'{rigScale}.floatA')
        cmds.connectAttr(f'{rigScale}.outFloat', f'{distZero}.floatB')
        cmds.setAttr(f'{distDiff}.floatA', cmds.getAttr(f'{distBet}.distance'))
        cmds.connectAttr(f'{distZero}.outFloat', f'{distDiff}.floatB')
        # Maintain length tx
        lengthCond = cmds.createNode('condition', n=f'{name}_lengthCond_'+str(i), ss=True)
        cmds.connectAttr(f'{attr_object}.MaintainLength', f'{lengthCond}.firstTerm')
        cmds.setAttr(f'{lengthCond}.secondTerm', 1)
        cmds.connectAttr(f'{distDiff}.outFloat', f'{lengthCond}.colorIfFalseR')
        cmds.setAttr(f'{lengthCond}.colorIfTrueR', cmds.getAttr(f'{distBet}.distance'))
        cmds.connectAttr(f'{lengthCond}.outColorR', f'{spline_joints[i+1]}.translateX')

def single_control(global_variables, name, ctl_joint):
    '''
    Creates a single rdCtl

    global_variables = ([ ]) List of rdCtl settings (margin, ctlSize, ctlShape, ctlColor, ctlSuffix, jntSuffix)
    name       = (str) Name to give rdCtl
    ctl_joint  = (bol) Create a joint 
    '''

    ctl_root = cmds.spaceLocator(name=name+'_ctlRef')[0]
    cmds.setAttr(ctl_root+'.overrideEnabled', 1)
    cmds.setAttr(ctl_root+'.overrideDisplayType', 2) # Reference
    loc_shape = omu.get_dag_path(ctl_root, shape=True)
    for axis in ['X', 'Y', 'Z']:
        cmds.setAttr(loc_shape+'.localScale'+axis, 0)

    ctl = rdCtl.Control(name, shape=global_variables[2], color=global_variables[3], size=global_variables[1], jt=ctl_joint, jntSuffix=global_variables[5], ctlSuffix=global_variables[4])
    rdctl_side_color(control=ctl, priority=global_variables[3], margin=global_variables[0])
    cmds.parent(ctl.grp, ctl_root)
    if ctl_joint == True:
        cmds.setAttr(str(ctl.jt)+'.v', 0)
    cmds.addAttr(ctl.topCtl, ci=True, at='bool', sn='rdCtl', min=0, max=1, dv=1)
    cmds.setAttr(ctl.topCtl+'.rdCtl', l=True)
    cmds.select(None)

    return ctl

def single_patch(global_variables, name, ctl_joint):
    '''
    Creates a single rdCtl constrained to a nurbs patch

    global_variables = ([ ]) List of rdCtl settings (margin, ctlSize, ctlShape, ctlColor, ctlSuffix, jntSuffix)
    name       = (str) Name to give rdCtl
    ctl_joint  = (bol) Create a joint 
    '''

    temp_surface  = cmds.nurbsPlane(ch=1, d=2, v=1, p=(0, 0, 0), u=1, w=1, ax=(0, 1, 0), lr=1.0)
    build_surface = cmds.rename(temp_surface[0], name) # Using rename to also rename shape node

    ctl_root = cmds.spaceLocator(name=name+'_ctlRef')[0]
    cmds.setAttr(f'{ctl_root}.overrideEnabled', 1)
    cmds.setAttr(f'{ctl_root}.overrideDisplayType', 2) # Reference
    loc_shape = omu.get_dag_path(ctl_root, shape=True)
    for axis in ['X', 'Y', 'Z']:
        cmds.setAttr(loc_shape+'.localScale'+axis, 0)

    ctl = rdCtl.Control(name, shape=global_variables[2], color=global_variables[3], size=global_variables[1], jt=ctl_joint, 
                        jntSuffix=global_variables[5], ctlSuffix=global_variables[4])

    rdctl_side_color(control=ctl, priority=global_variables[3], margin=global_variables[0])
    cmds.parent(ctl.grp, ctl_root)
    srf.constrain_to_surface_matrix(ctl_root, build_surface)
    cmds.setAttr(ctl.jt+'.v', 0)
    cmds.addAttr(ctl.topCtl, ci=True, at='bool', sn='rdCtl', min=0, max=1, dv=1)
    cmds.setAttr(ctl.topCtl+'.rdCtl', l=True)
    cmds.select(None)