import maya.cmds as cmds
from maya import OpenMaya as om
from maya.api.OpenMaya import *
from . import omUtil as omu
from . import rigUtils as rigu


def create_evenly_along_curve(object_type, object_name, count, curve_name, chain=0, joint_axis='xyz', keep_curve=0, 
                                suffix='gde', radius=0.3, lra=True):
    '''
    Evenly space joints along curve (but does not constrain them to curve)

    object_type = (str) Type of item to create along curve('joint' or 'locator')
    object_name = (str) Name for created obj's
    count       = (int) Number of items to create
    curve_name  = (str) Name of curve
    keep_curve  = (bol) Delete curve?
    suffix      = (str) Suffix
    radius      = (float) If joint, set joint radius
    lra         = (bol) If joint, turn on local rotation axis display

    '''
    if cmds.objExists(curve_name):
        if cmds.objectType(omu.get_dag_path(curve_name, shape=True))!='nurbsCurve':
            raise TypeError(f'Curve is not a nurbs curve >> {curve_name}')
    else:
        raise NameError(f'Curve does not exist in the scene >> {curve_name}')

    # Check for existing guides. If found, gets highest numbered
    guide_list = cmds.ls(f'{object_name}*{suffix}')
    if guide_list:
        last_number = guide_list[-1].split('_')[-2]
        start_number = int(last_number)+1
    else:
        start_number = 0

    '''
    # Object_name needs to end with '_' so numbering of new obj's is correct
    if not object_name.endswith('_'):
        object_name = object_name+'_'
    '''

    object_list = []
    curve_shape = omu.get_dag_path(curve_name, shape=1)
    curve_fn = om.MFnNurbsCurve(omu.get_dag_path(curve_name, shape=0))

    if count == 1:
        parameter = curve_fn.findParamFromLength(curve_fn.length() * 0.5)
        point = om.MPoint()
        curve_fn.getPointAtParam(parameter, point)
        if object_type == 'joint':
            num = 0
            jt = cmds.createNode('joint', n=f'{object_name}_{str(num)}_{suffix}')
            cmds.xform(jt,t=[point.x,point.y,point.z])
            object_list.append(jt)
        if object_type == 'locator':
            num = 0
            item = cmds.spaceLocator(n=f'{object_name}_{str(num)}_{suffix}')
            cmds.addAttr(item, at='float', k=True, ci=True, sn='U', max=1.0, min=0.0) # Used in strap.strapRigDorito()
            cmds.addAttr(item, at='float', k=True, ci=True, sn='V', max=1.0, min=0.0) # Used in strap.strapRigDorito()
            tra = cmds.listRelatives(item, p=1)
            cmds.xform(tra,t=[point.x,point.y,point.z])
            object_list.append(item[0])

    else:
        if cmds.getAttr(f'{curve_shape}.form') == 2: # Detects if open or closed curve. 2=Periodic
            spacing = 1.0/(count)
        else:
            spacing = 1.0/(count-1)

        for i in range(count):
            parameter = curve_fn.findParamFromLength(curve_fn.length() * spacing * i)
            point = om.MPoint()
            curve_fn.getPointAtParam(parameter, point)
            if object_type == 'joint':
                num = start_number+i
                jt = cmds.createNode('joint', n=f'{object_name}_{str(num)}_{suffix}')
                cmds.xform(jt,t=[point.x,point.y,point.z])
                object_list.append(jt)

                if chain and i != 0:
                    cmds.parent(jt, object_list[-2])

            if object_type == 'locator':
                num = start_number+i
                item = cmds.spaceLocator(n=f'{object_name}_{str(num)}_{suffix}')
                cmds.addAttr(item, at='float', k=True, ci=True, sn='U', max=1.0, min=0.0) # Used in strap.strapRigDorito()
                cmds.addAttr(item, at='float', k=True, ci=True, sn='V', max=1.0, min=0.0) # Used in strap.strapRigDorito()
                tra = cmds.listRelatives(item, p=1)
                cmds.xform(tra,t=[point.x,point.y,point.z])
                object_list.append(item[0])

    if len(object_list)>0 and object_type=='joint':
        # Orient joint
        for jt in object_list:
            cmds.joint(jt, edit=True, zso=True, sao='yup', oj=joint_axis)
            cmds.setAttr(f'{jt}.radius', radius)
            if lra == True:
                cmds.setAttr(f'{jt}.displayLocalAxis', 1)

    if not keep_curve:
        cmds.delete(curve_name)

    return object_list

def constrain_to_curve(constrained, curve_name):
    '''
    Constrain items to curve (position only)

    constrained = ([])  Items that will be constrained to curve
    curve_name  = (str) Curve to constrain items to
    '''
    if type(constrained) != list:
        constrained = [constrained]

    point_list = []
    for obj in constrained:
        ws_pos = cmds.xform(obj, q=True, ws=True, t=True)
        uParam = get_u_param(ws_pos, curve_name)
        curve_info_node = cmds.createNode('pointOnCurveInfo', n=f'{curve_name}_pocInf', ss=True)
        cmds.connectAttr(f'{curve_name}.worldSpace[0]', f'{curve_info_node}.inputCurve')
        cmds.setAttr(f'{curve_info_node}.parameter', uParam)
        cmds.connectAttr(f'{curve_info_node}.position', f'{obj}.translate')
        point_list.append(curve_info_node)

    return point_list

def constrain_to_curve_parametric(constrained, curve_name, up_type=4, inverse_up=0, inverse_front=0, front_axis=0, 
                        up_axis=2, up_object=None, offset=False, rotate=False):
    '''
    Constrain items to curve by motionPath nodes.
    Objects do not need to be placed on top of curve.
    This function gets closest point on curve to make constraint.

    constrained = ([]) Items that will be constrained to curve
    curve_name  = (str) Curve to constrain items to
    up_type     = (Int) 1=Object, 2=Object Rototation, 3=Vector, 4=Normal
    rotate      = (bol) Constrain rotation
    offset      = (bol) Create offset matrix for constrained objects
    '''

    if cmds.objExists(curve_name):
        if cmds.objectType(omu.get_dag_path(curve_name, shape=True)) != 'nurbsCurve':
            raise TypeError (f'Curve {curve_name} is not a curve')
    else:
        raise NameError(f'Curve {curve_name} does not exist in scene')

    # # If passing a single obj for constraint
    if type(constrained) != list:
        constrained = [constrained]

    path_nodes = []
    for obj in constrained:
        if cmds.listRelatives(obj, p=True):
            object_parent = cmds.listRelatives(obj, p=True)[0]
            cmds.parent(obj, w=True)
        else:
            object_parent=None
            
        # Try to eliminate joint orientations that affect matrix constraint
        if cmds.objectType(obj) == 'joint':
            try:
                cmds.makeIdentity(obj, apply=True, t=0, r=1, s=0, n=0, pn=1)
                for a in ['X', 'Y', 'Z']:
                    if cmds.getAttr(f'{obj}.jointOrient{a}') != 0:
                        cmds.setAttr(f'{obj}.rotate{a}', cmds.getAttr(f'{obj}.jointOrient{a}'))
                        cmds.setAttr(f'{obj}.jointOrient{a}', 0)
            except:
                pass

        pos=cmds.xform(obj, q=True, ws=True, t=True)
        u_param = get_u_param(pos, curve_name)
        print('curve u_param', u_param)
        motion_path = cmds.createNode('motionPath', n=f'{obj}_motPath', ss=True)
        cmds.connectAttr(f'{curve_name}.worldSpace[0]', f'{motion_path}.geometryPath')
        cmds.setAttr(f'{motion_path}.uValue', u_param)

        if up_type in [1, 2]:
            cmds.setAttr(f'{motion_path}.worldUpType', up_type)
            if cmds.objExists(up_object):
                cmds.connectAttr(f'{up_object}.worldMatrix[0]', f'{motion_path}.worldUpMatrix')
            else:
                raise ValueError(f'Object {up_object} does not exist')
        else:
            cmds.setAttr(f'{motion_path}.worldUpType', up_type)

        cmds.setAttr(f'{motion_path}.inverseUp', inverse_up)
        cmds.setAttr(f'{motion_path}.inverseFront', inverse_front)
        cmds.setAttr(f'{motion_path}.frontAxis', front_axis)
        cmds.setAttr(f'{motion_path}.upAxis', up_axis)
        path_nodes.append(motion_path)

        if offset:
            matrix = cmds.createNode('composeMatrix', n=f'{motion_path}_worldMatrix', ss=True)
            cmds.connectAttr(f'{motion_path}.allCoordinates', f'{matrix}.inputTranslate')
            cmds.connectAttr(f'{motion_path}.rotate', f'{matrix}.inputRotate')

            if rotate:
                rigu.parentConstraint(parent=None, child=obj, s=[], mo=True, 
                                    pm=f'{matrix}.outputMatrix')
                if object_parent:
                    cmds.parent(obj, object_parent)

                if cmds.objectType(obj) == 'joint':
                    for a in ['X', 'Y', 'Z']:
                        cmds.setAttr(f'{obj}.jointOrient{a}', 0)
            else:
                rigu.parentConstraint(parent=None, child=obj, r=[], s=[], mo=True, 
                                    pm=f'{matrix}.outputMatrix')
                if object_parent:
                    cmds.parent(obj, object_parent)

        else:
            cmds.connectAttr(f'{motion_path}.allCoordinates', f'{obj}.translate')
            if rotate:
                cmds.connectAttr(f'{motion_path}.rotate', f'{obj}.rotate')
            if object_parent:
                cmds.parent(obj, object_parent)

    return path_nodes

def constrain_to_curve_nonparametric(constrained, curve_name, up_type=4, inverse_up=0, inverse_front=0, front_axis=0, 
                            up_axis=2, up_object=None, offset=False, rotate=False):
    '''
    Constrain items to curve by motionPath nodes.
    Objects do not need to be placed on top of curve.
    This function gets closest point on curve to make constraint.

    constrained = ([])  Objects that will be constrained to curve
    curve_name  = (str) Curve that objects will be constrained to
    up_type     = (Int) 1=Object, 2=Object Rototation, 3=Vector, 4=Normal
    rotate      = (bol) Constrain rotation
    offset      = (bol) Create offset matrix for constrained objects
    '''

    if cmds.objExists(curve_name):
        if cmds.objectType(omu.get_dag_path(curve_name, shape=True)) != 'nurbsCurve':
            raise TypeError (f'Curve {curve_name} is not a curve')
    else:
        raise NameError(f'Curve {curve_name} does not exist in scene')

    # If passing a single obj for constraint
    if type(constrained) != list:
        constrained = [constrained]

    # Axis dict to allow int or string input arguments
    # To make compatable with simple_sys and velan libraries
    axis_dict = {'X': 0, 'Y': 1, 'Z': 2}
    if isinstance(front_axis, str):
        front_axis = axis_dict[front_axis]
    if isinstance(up_axis, str):
        up_axis = axis_dict[up_axis]

    path_nodes = []
    for obj in constrained:
        if cmds.listRelatives(obj, p=True):
            object_parent = cmds.listRelatives(obj, p=True)[0]
            cmds.parent(obj, w=True)
        else:
            object_parent=None
            
        # Try to eliminate joint orientations that affect matrix constraint
        if cmds.objectType(obj) == 'joint':
            try:
                cmds.makeIdentity(obj, apply=True, t=0, r=1, s=0, n=0, pn=1)
                for a in ['X', 'Y', 'Z']:
                    if cmds.getAttr(f'{obj}jointOrient{a}') != 0:
                        cmds.setAttr(f'{obj}rotate{a}', cmds.getAttr(f'{obj}.jointOrient{a}'))
                        cmds.setAttr(f'{obj}jointOrient{a}', 0)
            except:
                pass

        motion_path = cmds.createNode('motionPath', n=f'{obj}_motionPath', ss=True)
        u_param = get_u_parm_by_length(obj, curve_name)
        print('curve u_param', u_param)
        cmds.connectAttr(f'{curve_name}.ws[0]', f'{motion_path}.geometryPath')
        cmds.setAttr(f'{motion_path}.fractionMode', 1)
        cmds.setAttr(f'{motion_path}.uValue', u_param)

        if up_type in [1, 2]:
            cmds.setAttr(f'{motion_path}.worldUpType', up_type)
            if cmds.objExists(up_object):
                cmds.connectAttr(f'{up_object}.worldMatrix[0]', f'{motion_path}.worldUpMatrix')
            else:
                raise ValueError(f'Object {up_object} does not exist')
        else:
            cmds.setAttr(f'{motion_path}.worldUpType', up_type)

        cmds.setAttr(f'{motion_path}.inverseUp', inverse_up)
        cmds.setAttr(f'{motion_path}.inverseFront', inverse_front)
        cmds.setAttr(f'{motion_path}.frontAxis', front_axis)
        cmds.setAttr(f'{motion_path}.upAxis', up_axis)
        path_nodes.append(motion_path)

        if offset:
            matrix = cmds.createNode('composeMatrix', n=f'{motion_path}_worldMatrix', ss=True)
            cmds.connectAttr(f'{motion_path}.allCoordinates', f'{matrix}.inputTranslate')
            cmds.connectAttr(f'{motion_path}.rotate', f'{matrix}.inputRotate')

            if rotate:
                rigu.parentConstraint(parent=None, child=obj, s=[], mo=True, pm=f'{matrix}.outputMatrix')
                if object_parent:
                    cmds.parent(obj, object_parent)

                if cmds.objectType(obj) == 'joint':
                    for a in ['X', 'Y', 'Z']:
                        cmds.setAttr(f'{obj}.jointOrient{a}', 0)
            else:
                rigu.parentConstraint(parent=None, child=obj, r=[], s=[], mo=True, pm=f'{matrix}.outputMatrix')
                if object_parent:
                    cmds.parent(obj, object_parent)

        else:
            cmds.connectAttr(f'{motion_path}.allCoordinates', f'{obj}.translate')
            if rotate:
                cmds.connectAttr(f'{motion_path}.rotate', f'{obj}.rotate')
            if object_parent:
                cmds.parent(obj, object_parent)

    return path_nodes

def get_u_param(ws_pos, curve_name):
    '''
    Get closest point on curve from supplied world space

    ws_pos     = [Position] cmds.xform(obj, q=True, ws=True, t=True)
    curve_name = (str) = Curve name
    '''
    
    point = om.MPoint(*ws_pos)
    curveFn = om.MFnNurbsCurve(omu.get_dag_path(curve_name, shape=0))
    paramUtill=om.MScriptUtil()
    paramPtr=paramUtill.asDoublePtr()
    isOnCurve = curveFn.isPointOnCurve(point)
    
    if isOnCurve == True:
        curveFn.getParamAtPoint(point, paramPtr, 0.001, om.MSpace.kObject )
    else:
        point = curveFn.closestPoint(point, paramPtr, 0.001, om.MSpace.kObject)
        curveFn.getParamAtPoint(point, paramPtr, 0.001, om.MSpace.kObject )
    
    param = paramUtill.getDouble(paramPtr)

    return param

def get_u_parm_by_length(obj, curve_name):
    '''
    Gets UParam on curve_name by getting position on curve, arc 'length' value (Non-Parametric UParam)
    
    obj = (str) Object to retrieve closest point from
    curve_name = (str) Curve to query
    '''
   
    '''
    # OM (Seems to have difficulty finding closest point and fails when to close to end of curve)
    
    fn = MFnNurbsCurve(MGlobal.getSelectionListByName(curve_name).get_dag_path(0))_, u = fn.closestPoint(MPoint(cmds.xform(obj, q=1, ws=1, t=1)))
    u_param = fn.findLengthFromParam(u) / fn.length()
    '''
   
    # By Nodes
    object_pos = cmds.createNode('decomposeMatrix', n='objWorldSpace', ss=True)
    pnt_on_crv_node = cmds.createNode('nearestPointOnCurve', n='pocInfo', ss=True)
    arc_length_node = cmds.createNode('curveInfo', n='arcLen', ss=True)
    pos_length_node = cmds.createNode('arcLengthDimension', n='posInfo', ss=True)
    val_remap_node = cmds.createNode('remapValue', n='posUVal', ss=True)

    cmds.connectAttr(f'{curve_name}.ws[0]', f'{pnt_on_crv_node}.inputCurve')
    cmds.connectAttr(f'{curve_name}.ws[0]', f'{pos_length_node}.nurbsGeometry')
    cmds.connectAttr(f'{curve_name}.ws[0]', f'{arc_length_node}.inputCurve')
    cmds.connectAttr(f'{obj}.wm[0]', f'{object_pos}.imat')
    cmds.connectAttr(f'{object_pos}.outputTranslate', f'{pnt_on_crv_node}.inPosition')
    cmds.connectAttr(f'{pnt_on_crv_node}.parameter', f'{pos_length_node}.uParamValue')
    cmds.connectAttr(f'{pos_length_node}.arcLength', f'{val_remap_node}.inputValue')
    cmds.connectAttr(f'{arc_length_node}.arcLength', f'{val_remap_node}.inputMax')

    u_param = cmds.getAttr(f'{val_remap_node}.outValue')

    cmds.delete(object_pos, pnt_on_crv_node, arc_length_node, val_remap_node)
    cmds.delete(cmds.listRelatives(pos_length_node, p=True)) # Result: ['arcLengthDimension1']
   
    return u_param

def curve_from_joint_chain(root, curve_name, degree=3):
    '''
    root       = (str) Root joint of joint chain
    degree     = (int) Curve Degree
    curve_name = (str) Name of output curve
    '''

    joints = pos_from_joint_chain(root)
    new_curve = cmds.curve(d=degree, p=joints)
    cmds.rename(new_curve, curve_name)

def pos_from_joint_chain(root):
    '''
    Gets position of each joint in joint chain.
    Used in curve_from_joint_chain to create curve from joint chain.
   
    root = (str) Root of joint chain
    '''

    position = [cmds.xform(root, q=True, t=True, ws=True)]
    children = cmds.listRelatives(root, c=True) or []
    for child in children:
        position.extend(pos_from_joint_chain(child))
    return position

def query_cv_count(curve_name):
    '''
    Gives the number of cv's
    Number of cv's = degree + spans.
    '''

    degree = cmds.getAttr( f'{curve_name}.degree' )
    spans = cmds.getAttr( f'{curve_name}.spans' )
    cv = degree+spans
    return cv

def number_of_cv(curve_name):
    return int(cmds.getAttr (f'{curve_name}.degree')) + (cmds.getAttr (f'{curve_name}.spans'))

def update_shape_crv(source, target):
    '''
    Updates target curve shape with source curve shape.
    '''

    delete_unused_shapes_curve()

    for obj in [source, target]:
        if cmds.objectType(omu.get_dag_path(obj, shape=1)) != 'nurbsCurve':
            raise TypeError('Object is not of type nurbsSurface >> f{obj}')

    target_shapes = cmds.listRelatives(target, c=1, s=1)
    if len(target_shapes) > 1:
        for shape in target_shapes:
            if 'Orig' in shape:
                target_shape = shape
    else:
        target_shape = target_shapes[0]

    source_shapes = cmds.listRelatives(source, c=1, s=1)
    if len(source_shapes) > 1:
        for shape in source_shapes:
            if 'Orig' in shape:
                source_shape = shape
    else:
        source_shape = source_shapes[0]

    if target_shape and source_shape:
        cmds.connectAttr(f'{source_shape}.worldSpace[0]', f'{target_shape}.create')
        cmds.refresh()
        cmds.disconnectAttr(f'{source_shape}.worldSpace[0]', f'{target_shape}.create')

def delete_unused_shapes_curve():
    '''
    Removes all unused shape nodes in the scene
    '''
    all_curves = cmds.ls(type='nurbsCurve')
    dead_intermediates = []
    for crv in all_curves:
        if cmds.getAttr(f'{crv}.io'): #intermediateObject
            if not cmds.listConnections(crv):
                dead_intermediates.append(crv)

    if dead_intermediates:
        for io in dead_intermediates:
            cmds.delete(io)