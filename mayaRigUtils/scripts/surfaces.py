import maya.cmds as cmds
from . import omUtil as omu
from . import rigUtils as rigu


def nurb_surf_prep(surface_name=None, create=False):
    '''
    Rebuilds nurbs surface by reperamiterize 0-1.
    Or creates new surface plane with correct peramiterization.

    surface_name = (str) Nurbs surface to rebuild
    create       = (bol) Create new surf with correct build params
    '''
    
    if surface_name:
        if not cmds.objExists(surface_name):
            raise NameError('Specified surface does not exist in the scene')
        else:
            if cmds.listRelatives(surface_name, c=True, type='transform'):
                [cmds.delete(child) for child in cmds.listRelatives(surface_name, c=True, type='transform')]

            cmds.delete(surface_name, ch=True)
            cmds.makeIdentity(surface_name, apply=True, t=1, r=1, s=1, n=0, pn=1)
            prepSrf = cmds.rebuildSurface(surface_name, rt=0, kc=0, fr=0, ch=1, end=1, sv=0, su=0, kr=0, dir=2, kcp=0, 
                                            tol=0.01, dv=3, du=3, rpo=0)[0]
            cmds.ToggleSurfaceOrigin()
            cmds.delete(prepSrf, ch=1)
            cmds.delete(surface_name)
            cmds.rename(prepSrf, surface_name)
            return surface_name

    if create:
        temp_surface = cmds.nurbsPlane(ch=1, d=2, v=1, p=(0, 0, 0), u=5, w=5, ax=(0, 1, 0), lr=0.2)
        cmds.delete(temp_surface[0], ch=True)
        cmds.rename(temp_surface[0], 'RenameMe_gdeSrf')
        cmds.ToggleSurfaceOrigin(temp_surface)
        return temp_surface

def surface_reverse_direction():
    '''
    Swaps nurbs UV direction
    '''

    if cmds.ls(sl=1):
        surface_list = []
        for sel in cmds.ls(sl=1):
            if cmds.objectType(omu.get_dag_path(cmds.ls(sl=1)[0], shape=1)) != 'nurbsSurface':
                raise TypeError(f'Selection is not of type nurbsSurface >> {sel}')
            else:
                surface_list.append(sel)

        for surface in surface_list:
            cmds.reverseSurface(surface, d=3, ch=0, rpo=1)
            cmds.reverseSurface(surface, d=1, ch=0, rpo=1)
        
        cmds.select(surface_list, r=True)

def curve_along_surface(surface_name, open_closed='', uv='v'):
    '''
    Creates curve along center of nurbs surface

    surface_name = (str) Name of nurbs surface
    open_closed  = (str) Determine if the open or closed(periodic)
    uv           = (str) 'u'(0) or 'v'(1) direction along nurbs surface
    '''

    # Detect if nurbs is open or closed shape
    if cmds.getAttr(f'{surface_name}.formU') > 1:
        open_closed='closed'
    else:
        open_closed='open'

    u_or_v_dict = {'u':0, 'v':1}

    # Delete if exists
    if cmds.objExists(f'{surface_name}_srfIso'): 
        cmds.delete(f'{surface_name}_srfIso')
    if cmds.objExists(f'{surface_name}_srfCrv'):
        cmds.delete(f'{surface_name}_srfCrv')

    surface_shape = omu.get_dag_path(surface_name, shape=1)
    surface_iso = cmds.createNode('curveFromSurfaceIso', n=surface_name+'_srfIso', ss=True)
    temp_curve = cmds.curve(d=1, p=[(0, 0, 0), (1, 0, 0)])
    # Using rename to also rename curve shape node
    surface_curve = cmds.rename(temp_curve, surface_name+'_srfCrv')
   
    cmds.connectAttr(f'{surface_shape}.worldSpace[0]', f'{surface_iso}.inputSurface')
    cmds.setAttr(f'{surface_iso}.isoparmValue', 0.5)
    cmds.setAttr(f'{surface_iso}.isoparmDirection', u_or_v_dict[uv])
    cmds.connectAttr(f'{surface_iso}.outputCurve', f'{surface_curve}.create')

    if open_closed == 'open':
        if not cmds.getAttr(f'{surface_curve}.form')==0:
            cmds.closeCurve(surface_curve, caching=True, preserveShape=True, replaceOriginal=True, 
                blendKnotInsertion=False, parameter=0.1)
    else:
        if not cmds.getAttr(f'{surface_curve}.form')==2:
            cmds.closeCurve(surface_curve, caching=True, preserveShape=True, replaceOriginal=True, 
                blendKnotInsertion=False, parameter=0.1)

    cmds.parent(surface_curve, surface_name)

    return surface_curve

def curve_along_surface_multi(surface_name, rows, open_closed='', uv='v'):
    '''
    Creates several curves along nurbs surface

    surface_name = (str) Name of nurbs surface
    open_closed  = (str) Determine if the open or closed(periodic)
    rows    = (int) Number of curves to create on nurbs surface
    uv      = (str) 'u'(0) or 'v'(1) direction along nurbs surface
    '''

    # Detect if nurbs is open or closed shape
    if cmds.getAttr(f'{surface_name}.formU') > 1:
        open_closed='closed'
    else:
        open_closed='open'

    u_or_v_dict = {'u':0, 'v':1}

    surface_shape = omu.get_dag_path(surface_name, shape=1)
    row_increment = cmds.getAttr(f'{surface_shape}.minMaxRange'+uv.upper())[0][1]/float(rows-1)

    '''
    if cmds.getAttr(f'{surface_shape}.f{uv}') == 2: # Detects if open or closed surface. 2=Periodic
        row_increment = cmds.getAttr(f'{surface_shape}.spans{uv}')/float(rows) # Gets U or V spans for spacing of curves
    else:
        row_increment = cmds.getAttr(f'{surface_shape}.minMaxRange{uv.upper()}')[0][1]/float(rows-1)
    '''

    curves_list = []
    for i in range(rows):
        base_curve = cmds.curve(d=1, p=[(0, 0, 0), (0, 0, 1)])
        # Using rename to also rename curve shape node
        surface_curve = cmds.rename(base_curve, f'{surface_name}_srfCrv_{str(i)}')

        surface_iso_node = cmds.createNode('curveFromSurfaceIso', n=f'{surface_name}_srfIso', ss=True)
        cmds.connectAttr(f'{surface_name}.worldSpace[0]', f'{surface_iso_node}.inputSurface')
        cmds.setAttr(f'{surface_iso_node}.isoparmValue', i*row_increment)
        cmds.setAttr(f'{surface_iso_node}.isoparmDirection', u_or_v_dict[uv])
        cmds.connectAttr(f'{surface_iso_node}.outputCurve', f'{surface_curve}.create')
        curves_list.append(surface_curve)

        if open_closed == 'open':
            if not cmds.getAttr(f'{surface_curve}.form')==0:
                cmds.closeCurve(surface_curve, caching=True, preserveShape=True, replaceOriginal=True, 
                    blendKnotInsertion=False, parameter=0.1)
        else:
            if not cmds.getAttr(f'{surface_curve}.form')==2:
                cmds.closeCurve(surface_curve, caching=True, preserveShape=True, replaceOriginal=True, 
                    blendKnotInsertion=False, parameter=0.1)

        cmds.parent(surface_curve, surface_name)

    return curves_list

def constrain_to_surface_follicle(object_name, surface_name, translate=True, rotate=True, 
                                world_space=True, offset=False, return_pos=False, driver_obj=None):
    '''
    Constrains objects to closest point on nurbs surface by follicle.

   
    object_name  = (str) Item to be constrained
    surface_name = (str) Surface that item will be constrained to
    translate    = (bol) Constrain object translation
    rotate       = (bol) Constrain object rotation
    world_space  = (bol) Use constrained objects ws for closest point on surface
    offset       = (bol) Create offset matrix for constrained objects
    return_pos   = (bol) Return closestPointOnSurface node, to animate the constraint
    driver_obj   = (str) Use driver_object world position to animate constrained object over surface,
                        (When return_pos = True)
    '''

    '''
    # #Check for normalized u,v values
    rangeU = cmds.getAttr(surface_name+'.minMaxRangeV')
    rangeV = cmds.getAttr(surface_name+'.minMaxRangeV')

    if rangeU and rangeV != [(0.0, 1.0)]:
        rebuild = cmds.confirmDialog( title='Rebuild?', message='Nurbs does not have 0,1 param. Rebuild?', 
            button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
        if rebuild:
            surface_name = nurbsSrfPrep(surface_name=surface_name)
    '''


    if cmds.listRelatives(object_name, p=True):
        object_parent = cmds.listRelatives(object_name, p=True)[0]
        cmds.parent(object_name, w=True)
    else:
        object_parent = None

    if rotate:
        if cmds.objectType(object_name) == 'joint':
            try:
                cmds.makeIdentity(object_name, apply=True, t=0, r=1, s=0, n=0, pn=1)
                for a in ['X', 'Y', 'Z']:
                    if cmds.getAttr(f'{object_name}.jointOrient{a}') != 0:
                        cmds.setAttr(f'{object_name}.rotate{a}', cmds.getAttr(f'{object_name}.jointOrient{a}'))
                        cmds.setAttr(f'{object_name}.jointOrient{a}', 0)
            except:
                pass

    pos_node = cmds.createNode('closestPointOnSurface', ss=True)
    # Connect nurbs surface to pntOnSrfPointOnSurface node
    cmds.connectAttr(f'{surface_name}.worldSpace[0]', f'{pos_node}.inputSurface')
    
    # Get world translation
    if world_space:
        decomp_node = cmds.createNode('decomposeMatrix', n=f'{object_name}_world_pos', ss=True)
        cmds.connectAttr(f'{object_name}.worldMatrix[0]', f'{decomp_node}.inputMatrix')
        cmds.connectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')
    else:
        cmds.connectAttr(f'{object_name}.translate', f'{pos_node}.inPosition')
    

    follicle = cmds.createNode("follicle", ss=True)
    # Get follicle transform
    follicle_transform = cmds.listRelatives(follicle, type='transform', p=True)
    # Follicle shape rotation drives follicle transform rotation
    cmds.connectAttr(f'{follicle}.outRotate', f'{follicle_transform[0]}.rotate')
    # Follicle shape translation drives follicle transform translation
    cmds.connectAttr(f'{follicle}.outTranslate', f'{follicle_transform[0]}.translate') 
    # This will negate transforms and allow the follicle to be parented under the surface
    cmds.connectAttr(f'{surface_name}.worldInverseMatrix', f'{follicle}.inputWorldMatrix') 

    cmds.connectAttr(f'{surface_name}.worldSpace[0]', f'{follicle}.inputSurface')
    cmds.setAttr(f'{follicle}.simulationMethod', 0)
    cmds.setAttr(f'{follicle}.visibility', 0)
    # Connecting U,V param to follicle U,V param
    cmds.connectAttr(f'{pos_node}.result.parameterU', f'{follicle}.parameterU')
    cmds.connectAttr(f'{pos_node}.result.parameterV', f'{follicle}.parameterV')

    if not return_pos:
        if world_space:
            cmds.disconnectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')
            cmds.disconnectAttr(f'{pos_node}.result.parameterU', f'{follicle}.parameterU')
            cmds.disconnectAttr(f'{pos_node}.result.parameterV', f'{follicle}.parameterV')
        else: 
            cmds.disconnectAttr(f'{object_name}.translate', f'{pos_node}.inPosition')
            cmds.disconnectAttr(f'{pos_node}.result.parameterU', f'{follicle}.parameterU')
            cmds.disconnectAttr(f'{pos_node}.result.parameterV', f'{follicle}.parameterV')

    if driver_obj:
        if world_space:
            cmds.disconnectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')
        else:
            cmds.disconnectAttr(f'{object_name}.outputTranslate', f'{pos_node}.inPosition')
        decomp_node = cmds.createNode('decomposeMatrix', n=f'{driver_obj}_world_pos', ss=True)
        cmds.connectAttr(f'{driver_obj}.worldMatrix[0]', f'{decomp_node}.inputMatrix')
        cmds.connectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')

    if translate == True:
        tra = ['x','y','z']
    else:
        tra = []
    if rotate == True:
        rot = ['x','y','z']
    else:
        rot = []

    if offset:
        rigu.parentConstraint(parent=follicle_transform[0], child=object_name, t=tra, r=rot, s=[], mo=True)
        if object_parent:
            cmds.parent(object_name, object_parent)

        if cmds.objectType(object_name) == 'joint':
            if rotate:
                for a in ['X', 'Y', 'Z']:
                    cmds.setAttr(f'{object_name}.jointOrient{a}', 0)
        if not rotate:
            try:
                cmds.makeIdentity(object_name, apply=True, t=0, r=1, s=0, n=0, pn=1)
            except:
                pass
    else:
        rigu.parentConstraint(parent=follicle_transform[0], child=object_name, t=tra, r=rot, s=[], mo=False)
        if object_parent:
            cmds.parent(object_name, object_parent)

        if cmds.objectType(object_name) == 'joint':
            if rotate:
                for a in ['X', 'Y', 'Z']:
                    cmds.setAttr(f'{object_name}.jointOrient{a}', 0)


    if return_pos:
        return pos_node
    else:
        cmds.delete(pos_node, decomp_node)

def constrain_to_surface_matrix(object_name, surface_name, translate=True, rotate=True, offset=False, x_axis='v', 
                    world_space=True, return_pos=False, driver_obj=None):
    '''
    Constrains objects to closest point on nurbs surface by matrix

    object_name  = (str) Item to be constrained
    surface_name = (str) Surface that item will be constrained to
    translate    = (bol) Constrain translation
    rotate       = (bol) Constrain rotation
    offset       = (bol) Create offset transform for constrained objects
    x_axis        = (str) 'u' or 'v' direction of srf to use for joint X vector
    world_space  = (bol) Use constrained objects ws for closest point on surface
    return_pos   = (bol) Return closestPointOnSurface node, to animate the constraint
    driver_obj   = (str) Use driver_object world position to animate constrained object over surface,
                        (When return_pos = True)
    '''


    '''
    #check for normalized u,v values
    rangeU = cmds.getAttr(surface_name+'.minMaxRangeU')
    rangeV = cmds.getAttr(surface_name+'.minMaxRangeV')

    if rangeU and rangeV != [(0.0, 1.0)]:
        rebuild = cmds.confirmDialog( title='Rebuild?', message='Nurbs does not have 0,1 param. Rebuild?', 
                                    button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
        if rebuild == True:
            surface_name = nurbsSrfPrep(surface_name=surface_name)
    '''

    if cmds.listRelatives(object_name, p=True):
        objParent = cmds.listRelatives(object_name, p=True)[0]
        cmds.parent(object_name, w=True)
    else:
        objParent=None

    if rotate:
        if cmds.objectType(object_name) == 'joint':
            try:
                cmds.makeIdentity(object_name, apply=True, t=0, r=1, s=0, n=0, pn=1)
                for a in ['X', 'Y', 'Z']:
                    if cmds.getAttr(f'{object_name}.jointOrient{a}') != 0:
                        cmds.setAttr(f'{object_name}.rotate{a}', cmds.getAttr(f'{object_name}.jointOrient{a}'))
                        cmds.setAttr(f'{object_name}.jointOrient{a}', 0)
            except:
                pass

    pos_node = cmds.createNode('closestPointOnSurface', n=f'{object_name}pos_node', ss=True)
    pos_info_node = cmds.createNode('pointOnSurfaceInfo', n=f'{object_name}pos_info_node', ss=True)
    pos_matrix_node = cmds.createNode('fourByFourMatrix', n=f'{object_name}posMat', ss=True)

    cmds.connectAttr(f'{surface_name}.worldSpace[0]', f'{pos_node}.inputSurface')
    cmds.connectAttr(f'{surface_name}.worldSpace[0]', f'{pos_info_node}.inputSurface')
    cmds.connectAttr(f'{pos_node}.parameterU', f'{pos_info_node}.parameterU')
    cmds.connectAttr(f'{pos_node}.parameterV', f'{pos_info_node}.parameterV')
    

    # Get world translation
    if world_space:
        decomp_node = cmds.createNode('decomposeMatrix', n=f'{object_name}_world_pos', ss=True)
        cmds.connectAttr(f'{object_name}.worldMatrix[0]', f'{decomp_node}.inputMatrix')
        cmds.connectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')
    else:
        cmds.connectAttr(f'{object_name}.translate', f'{pos_node}.inPosition')

    
    if not return_pos:
        if world_space:
            cmds.disconnectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')
            cmds.disconnectAttr(f'{pos_node}.parameterU', f'{pos_info_node}.parameterU')
            cmds.disconnectAttr(f'{pos_node}.parameterV', f'{pos_info_node}.parameterV')
        else:
            cmds.disconnectAttr(f'{object_name}.outputTranslate', f'{pos_node}.inPosition')
            cmds.disconnectAttr(f'{pos_node}.parameterU', f'{pos_info_node}.parameterU')
            cmds.disconnectAttr(f'{pos_node}.parameterV', f'{pos_info_node}.parameterV')

    if driver_obj:
        if world_space:
            cmds.disconnectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')
        else:
            cmds.disconnectAttr(f'{object_name}.outputTranslate', f'{pos_node}.inPosition')
        decomp_node = cmds.createNode('decomposeMatrix', n=f'{driver_obj}_world_pos', ss=True)
        cmds.connectAttr(f'{driver_obj}.worldMatrix[0]', f'{decomp_node}.inputMatrix')
        cmds.connectAttr(f'{decomp_node}.outputTranslate', f'{pos_node}.inPosition')


    # Pull away from the edge of the nurbs surface
    # Cannot limit this attr minValue, maxValue
    if cmds.getAttr(f'{pos_info_node}.parameterV') == 0:
        cmds.setAttr(f'{pos_info_node}.parameterV', 0.001)
    if cmds.getAttr(f'{pos_info_node}.parameterV') == 1.0999999999999999:
        cmds.setAttr(f'{pos_info_node}.parameterV', 1.098)
    if cmds.getAttr(f'{pos_info_node}.parameterU') == 0:
        cmds.setAttr(f'{pos_info_node}.parameterU', 0.001)
    if cmds.getAttr(f'{pos_info_node}.parameterU') == 1:
        cmds.setAttr(f'{pos_info_node}.parameterU', 0.999)

    if x_axis=='u':
        # X vector
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentUX', f'{pos_matrix_node}.in00')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentUY', f'{pos_matrix_node}.in01')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentUZ', f'{pos_matrix_node}.in02')
        # Y vector
        cmds.connectAttr(f'{pos_info_node}.normalizedNormalX', f'{pos_matrix_node}.in10')
        cmds.connectAttr(f'{pos_info_node}.normalizedNormalY', f'{pos_matrix_node}.in11')
        cmds.connectAttr(f'{pos_info_node}.normalizedNormalZ', f'{pos_matrix_node}.in12')
        # Z vector
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentVX', f'{pos_matrix_node}.in20')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentVY', f'{pos_matrix_node}.in21')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentVZ', f'{pos_matrix_node}.in22')

    if x_axis=='v':
        # X vector
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentVX', f'{pos_matrix_node}.in00')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentVY', f'{pos_matrix_node}.in01')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentVZ', f'{pos_matrix_node}.in02')
        # Y vector
        cmds.connectAttr(f'{pos_info_node}.normalizedNormalX', f'{pos_matrix_node}.in10')
        cmds.connectAttr(f'{pos_info_node}.normalizedNormalY', f'{pos_matrix_node}.in11')
        cmds.connectAttr(f'{pos_info_node}.normalizedNormalZ', f'{pos_matrix_node}.in12')
        # Z vector
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentUX', f'{pos_matrix_node}.in20')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentUY', f'{pos_matrix_node}.in21')
        cmds.connectAttr(f'{pos_info_node}.normalizedTangentUZ', f'{pos_matrix_node}.in22')

    cmds.connectAttr(f'{pos_info_node}.positionX', f'{pos_matrix_node}.in30')
    cmds.connectAttr(f'{pos_info_node}.positionY', f'{pos_matrix_node}.in31')
    cmds.connectAttr(f'{pos_info_node}.positionZ', f'{pos_matrix_node}.in32')

    if translate == True:
        tra = ['x','y','z']
    else:
        tra = []
    if rotate == True:
        rot = ['x','y','z']
    else:
        rot = []

    if offset:
        rigu.parentConstraint(parent=None, child=object_name, t=tra, r=rot, s=[], 
                              mo=True, pm=f'{pos_matrix_node}.output')
        if objParent:
            cmds.parent(object_name, objParent)

        if cmds.objectType(object_name) == 'joint':
            if rotate:
                for a in ['X', 'Y', 'Z']:
                    cmds.setAttr(f'{object_name}.jointOrient{a}', 0)
        if not rotate:
            try:
                cmds.makeIdentity(object_name, apply=True, t=0, r=1, s=0, n=0, pn=1)
            except:
                pass
    else:
        rigu.parentConstraint(parent=None, child=object_name, t=tra, r=rot, s=[],
                              mo=False, pm=f'{pos_matrix_node}.output')
        if objParent:
            cmds.parent(object_name, objParent)

        if cmds.objectType(object_name) == 'joint':
            if rotate:
                for a in ['X', 'Y', 'Z']:
                    cmds.setAttr(f'{object_name}.jointOrient{a}', 0)

    
    # Connect U, V if they exist (locator guides)
    if 'U' in cmds.listAttr(object_name):
        if cmds.getAttr(f'{pos_info_node}.parameterU') > 1.0: # I think I'm getting rounding errors creating values above 1.0
            cmds.setAttr(f'{object_name}.U', 1.0)
        else:
            if cmds.getAttr(pos_info_node+'.parameterU') < 0:
                pos = 0
            else:
                pos = cmds.getAttr(f'{pos_info_node}.parameterU')
            cmds.setAttr(f'{object_name}.U', pos)
        cmds.connectAttr(f'{object_name}.U', f'{pos_info_node}.parameterU')

    if 'V' in cmds.listAttr(object_name):
        if cmds.getAttr(f'{pos_info_node}.parameterV') > 1.0: # I think I'm getting rounding errors creating values above 1.0
            cmds.setAttr(f'{object_name}.V', 1.0)
        else:
            if cmds.getAttr(f'{pos_info_node}.parameterV') < 0:
                pos = 0
            else:
                pos = cmds.getAttr(f'{pos_info_node}.parameterV')
            cmds.setAttr(f'{object_name}.V', pos)
        cmds.connectAttr(f'{object_name}.V', f'{pos_info_node}.parameterV')


    if return_pos:
        return pos_node, pos_info_node
    else:
        cmds.delete(pos_node)
        return pos_info_node