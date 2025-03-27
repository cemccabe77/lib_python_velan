import maya.cmds as cmds
from . import omUtil as omu
from . import rigUtils as rigu


def nurbsSrfPrep(create=False, srfName=None):
    '''
    Rebuilds nurbs surface to reperamiterize 0-1.
    Or creates new one with correct peramiterization.

    srfName = (str) Nurbs surface to rebuild
    create  = (bol) Create new surf with correct build params
    '''

    if create:
        tmpSrf = cmds.nurbsPlane(ch=1, d=2, v=1, p=(0, 0, 0), u=5, w=5, ax=(0, 1, 0), lr=0.2)
        bldSrf = cmds.rename(tmpSrf[0], 'RenameMe_gdeSrf')
        cmds.ToggleSurfaceOrigin(bldSrf)

        return bldSrf

    else:
        if cmds.objExists(srfName):
            if cmds.objectType(omu.getDagPath(srfName, shape=True))!='nurbsSurface':
                raise TypeError('Specified surface is not a nurbs surface')
            else:
                if cmds.listRelatives(srfName, c=True, type='transform'):
                    [cmds.delete(item) for item in cmds.listRelatives(srfName, c=True, type='transform')]
        else:
            raise NameError('Specified surface does not exist in the scene')

        # rebuild surface 0-1
        cmds.setAttr(srfName+'.v', 0)
        prepSrf = cmds.rebuildSurface(srfName, rt=0, kc=0, fr=0, ch=1, end=1, sv=0, su=0, kr=0, dir=2, kcp=0, tol=0.01, dv=3, du=3, rpo=0)[0]
        cmds.ToggleSurfaceOrigin()
        cmds.delete(prepSrf, ch=1)
        cmds.delete(srfName)
        bldSrf = cmds.rename(prepSrf, srfName)

        return bldSrf

def crvAlongSrf(srfName, uv='u'):
    '''
    Creates curve down center of nurbs surface

    srfName = (str) Name of nurbs surface
    uv      = (str) 'u'(0) or 'v'(1) direction along nurbs surface
    '''
    uORv = {'u':0, 'v':1}

    if cmds.objExists(srfName+'_srfIso'): # Delete existing to rebuild
        cmds.delete(srfName+'_srfIso')
    if cmds.objExists(srfName+'_srfCrv'):
        cmds.delete(srfName+'_srfCrv')

    srfShp = omu.getDagPath(srfName, shape=1)
    srfIso = cmds.createNode('curveFromSurfaceIso', n=srfName+'_srfIso', ss=True)
    tmpCrv = cmds.curve( d=1, p=[(0, 0, 0), (1, 0, 0)])
    srfCrv = cmds.rename(tmpCrv, srfName+'_srfCrv') # Using rename to rename crv shape as well
   
    cmds.connectAttr(srfShp+'.worldSpace[0]', srfIso+'.inputSurface')
    cmds.setAttr(srfIso+'.isoparmValue', 0.5)
    cmds.setAttr(srfIso+'.isoparmDirection', uORv[uv])
    cmds.connectAttr(srfIso+'.outputCurve', srfCrv+'.create')
    cmds.parent(srfCrv, srfName)

    return srfCrv

def crvAlongSrfMulti(srfName, rows, uv='v'):
    '''
    Creates several curves along nurbs surface

    srfName = (str) Name of nurbs surface
    rows    = (int) Number of curves to create on nurbs surface
    uv      = (str) 'u'(0) or 'v'(1) direction along nurbs surface
    '''
    uORv = {'u':0, 'v':1}

    if cmds.objExists(srfName):
        srfShp = omu.getDagPath(srfName, shape=True)
        if not cmds.objectType(srfShp) == 'nurbsSurface':
            raise TypeError('Specified surface is not nurbsSurface')
    else:
        raise NameError('Specified surface does not exist in the scene')

    rowInc = cmds.getAttr(srfShp+'.minMaxRange'+uv.upper())[0][1]/float(rows-1)

    # if cmds.getAttr(srfShp+'.f'+uv) == 2: # Detects if open or closed surface. 2=Periodic
    #     rowInc = cmds.getAttr(srfShp+'.spans'+uv)/float(rows) # Gets U or V spans for spacing of curves
    # else:
    #     rowInc = cmds.getAttr(srfShp+'.minMaxRange'+uv.upper())[0][1]/float(rows-1)

    rowCrvs = []
    for i in range(rows):
        bseCrv = cmds.curve(d=1, p=[(0, 0, 0), (0, 0, 1)])
        # print srfName+'_srfCrv_'+str(i)
        srfCrv = cmds.rename(bseCrv, srfName+'_srfCrv_'+str(i))
        # print srfCrv

        srfIsoNde = cmds.createNode('curveFromSurfaceIso', n=srfName+'_srfIso', ss=True)
        cmds.connectAttr(srfName+'.worldSpace[0]', srfIsoNde+'.inputSurface')
        cmds.setAttr(srfIsoNde+'.isoparmValue', i*rowInc)
        cmds.setAttr(srfIsoNde+'.isoparmDirection', uORv[uv])
        cmds.connectAttr(srfIsoNde+'.outputCurve', srfCrv+'.create')
        rowCrvs.append(srfCrv)

    return rowCrvs

def constToSrfFol(obj, srfName, translate=True, rotate=True, offset=False):
    '''
    Constrains objects to closest point on nurbs surface with follicle.
    Follicle follows point positions, not transforms.
   
    obj = (str) Item to be constrained
    srfName = (str) Surface that item will be constrained to
    offset = (bol) Create offset transform for constrained objects
    '''

    # # #check for normalized u,v values
    # rangeU = cmds.getAttr(srfName+'.minMaxRangeV')
    # rangeV = cmds.getAttr(srfName+'.minMaxRangeV')

    # if rangeU and rangeV != [(0.0, 1.0)]:
    #     rebuild = cmds.confirmDialog( title='Rebuild?', message='Nurbs does not have 0,1 param. Rebuild?', button=['Yes','No'], 
    #         defaultButton='Yes', cancelButton='No', dismissString='No' )
    #     if rebuild:
    #         srfName = nurbsSrfPrep(srfName=srfName)

    pntOnSrf = cmds.createNode('closestPointOnSurface', ss=True)
    cmds.connectAttr(srfName+'.worldSpace[0]', pntOnSrf+'.inputSurface') # Connect nurbs surface to pntOnSrfPointOnSurface node
    cmds.connectAttr(obj+'.translate', pntOnSrf+'.inPosition') # get world translate
    cmds.disconnectAttr(obj+'.translate', pntOnSrf+'.inPosition')

    follicle = cmds.createNode("follicle", ss=True)
    follicleTrans = cmds.listRelatives(follicle, type='transform', p=True) # get follicle transform
    cmds.connectAttr(follicle+ ".outRotate", follicleTrans[0] + ".rotate") # follicle shape rot drives follicle transform rot
    cmds.connectAttr(follicle+ ".outTranslate", follicleTrans[0] + ".translate") # follicle shape translate drives follicle transform translate

    cmds.connectAttr(srfName+'.worldInverseMatrix', follicle+'.inputWorldMatrix') # This will negate transforms and allow the follicle to be parented under the surface

    cmds.connectAttr(srfName+'.worldSpace[0]', follicle+'.inputSurface')
    cmds.setAttr(follicle+ ".simulationMethod", 0)
    cmds.setAttr(follicle+'.visibility', 0)

    cmds.connectAttr(pntOnSrf+'.result.parameterU', follicle+'.parameterU')# connecting U,V param to follicle U,V param
    cmds.connectAttr(pntOnSrf+'.result.parameterV', follicle+'.parameterV')

    if translate == True:
        tra = ['x','y','z']
    else:
        tra = []
    if rotate == True:
        rot = ['x','y','z']
    else:
        rot = []

    if offset:
        rigu.parentConstraint(follicleTrans[0], child=obj, t=tra, r=rot, mo=True)
    else:
        rigu.parentConstraint(follicleTrans[0], child=obj, t=tra, r=rot, mo=False)

    cmds.delete(pntOnSrf) # Needs to be deleted

def constToSrfMatrix(obj, srfName, translate=True, rotate=True, offset=False, xAxis='u', return_pos=False):
    '''
    Constrains objects to closest point on nurbs surface with matrix

    obj       = (str) Item to be constrained
    srfName   = (str) Surface that item will be constrained to
    translate = (bol) Constrain translation
    rotate    = (bol) Constrain rotation
    offset    = (bol) Create offset transform for constrained objects
    xAxis     = (str) 'u' or 'v' direction of srf to use for joint X vector
    return_pos = (bol) Return closestPointOnSurface node (otherwise delete pos).
                       Manually create decomposeMatrix node and connect
                       'driver obj' worldMatrix through to f'{return_pos}.inPosition'.
                       This will animate constrained obj along surface. Ref: eyelid joint example
    '''

    # #check for normalized u,v values
    # rangeU = cmds.getAttr(srfName+'.minMaxRangeU')
    # rangeV = cmds.getAttr(srfName+'.minMaxRangeV')

    # if rangeU and rangeV != [(0.0, 1.0)]:
    #     rebuild = cmds.confirmDialog( title='Rebuild?', message='Nurbs does not have 0,1 param. Rebuild?', button=['Yes','No'], 
    #         defaultButton='Yes', cancelButton='No', dismissString='No' )
    #     if rebuild == True:
    #         srfName = nurbsSrfPrep(srfName=srfName)


    if cmds.listRelatives(obj, p=True):
        objParent = cmds.listRelatives(obj, p=True)[0]
        cmds.parent(obj, w=True)
    else:
        objParent=None

    if rotate:
        if cmds.objectType(obj) == 'joint':
            try:
                cmds.makeIdentity(obj, apply=True, t=0, r=1, s=0, n=0, pn=1)
                for a in ['X', 'Y', 'Z']:
                    if cmds.getAttr(f'{obj}.jointOrient{a}') != 0:
                        cmds.setAttr(f'{obj}.rotate{a}', cmds.getAttr(f'{obj}.jointOrient{a}'))
                        cmds.setAttr(f'{obj}.jointOrient{a}', 0)
            except:
                pass

    pntOnSrf = cmds.createNode('closestPointOnSurface', n=obj+'pntOnSrf', ss=True)
    posInf = cmds.createNode('pointOnSurfaceInfo', n=obj+'posInf', ss=True)
    posMatrix = cmds.createNode('fourByFourMatrix', n=obj+'posMat', ss=True)

    cmds.connectAttr(srfName+'.worldSpace[0]', pntOnSrf+'.inputSurface')
    cmds.connectAttr(srfName+'.worldSpace[0]', posInf+'.inputSurface')
    cmds.connectAttr(obj+'.translate', pntOnSrf+'.inPosition')
    cmds.connectAttr(pntOnSrf+'.parameterU', posInf+'.parameterU')
    cmds.connectAttr(pntOnSrf+'.parameterV', posInf+'.parameterV')
    if not return_pos:
        cmds.disconnectAttr(pntOnSrf+'.parameterU', posInf+'.parameterU')
        cmds.disconnectAttr(pntOnSrf+'.parameterV', posInf+'.parameterV')
    
    # Pull away from the edge of the nurbs surface
    # Cannot limit this attr minValue, maxValue
    if cmds.getAttr(posInf+'.parameterV') == 0:
        cmds.setAttr(posInf+'.parameterV', 0.001)
    if cmds.getAttr(posInf+'.parameterV') == 1.0999999999999999:
        cmds.setAttr(posInf+'.parameterV', 1.098)
    if cmds.getAttr(posInf+'.parameterU') == 0:
        cmds.setAttr(posInf+'.parameterU', 0.001)
    if cmds.getAttr(posInf+'.parameterU') == 1:
        cmds.setAttr(posInf+'.parameterU', 0.999)

    if xAxis=='u':
        # X vector
        cmds.connectAttr(posInf+'.normalizedTangentUX', posMatrix+'.in00')
        cmds.connectAttr(posInf+'.normalizedTangentUY', posMatrix+'.in01')
        cmds.connectAttr(posInf+'.normalizedTangentUZ', posMatrix+'.in02')
        # Y vector
        cmds.connectAttr(posInf+'.normalizedNormalX', posMatrix+'.in10')
        cmds.connectAttr(posInf+'.normalizedNormalY', posMatrix+'.in11')
        cmds.connectAttr(posInf+'.normalizedNormalZ', posMatrix+'.in12')
        # Z vector
        cmds.connectAttr(posInf+'.normalizedTangentVX', posMatrix+'.in20')
        cmds.connectAttr(posInf+'.normalizedTangentVY', posMatrix+'.in21')
        cmds.connectAttr(posInf+'.normalizedTangentVZ', posMatrix+'.in22')

    if xAxis=='v':
        # X vector
        cmds.connectAttr(posInf+'.normalizedTangentVX', posMatrix+'.in00')
        cmds.connectAttr(posInf+'.normalizedTangentVY', posMatrix+'.in01')
        cmds.connectAttr(posInf+'.normalizedTangentVZ', posMatrix+'.in02')
        # Y vector
        cmds.connectAttr(posInf+'.normalizedNormalX', posMatrix+'.in10')
        cmds.connectAttr(posInf+'.normalizedNormalY', posMatrix+'.in11')
        cmds.connectAttr(posInf+'.normalizedNormalZ', posMatrix+'.in12')
        # Z vector
        cmds.connectAttr(posInf+'.normalizedTangentUX', posMatrix+'.in20')
        cmds.connectAttr(posInf+'.normalizedTangentUY', posMatrix+'.in21')
        cmds.connectAttr(posInf+'.normalizedTangentUZ', posMatrix+'.in22')

    cmds.connectAttr(posInf+'.positionX', posMatrix+'.in30')
    cmds.connectAttr(posInf+'.positionY', posMatrix+'.in31')
    cmds.connectAttr(posInf+'.positionZ', posMatrix+'.in32')

    if translate == True:
        tra = ['x','y','z']
    else:
        tra = []
    if rotate == True:
        rot = ['x','y','z']
    else:
        rot = []

    if offset:
        rigu.parentConstraint(parent=None, child=obj, t=tra, r=rot, s=[], 
                              mo=True, pm=posMatrix+'.output')
        if objParent:
            cmds.parent(obj, objParent)

        if cmds.objectType(obj) == 'joint':
            if rotate:
                for a in ['X', 'Y', 'Z']:
                    cmds.setAttr(f'{obj}.jointOrient{a}', 0)
        if not rotate:
            try:
                cmds.makeIdentity(obj, apply=True, t=0, r=1, s=0, n=0, pn=1)
            except:
                pass
    else:
        rigu.parentConstraint(parent=None, child=obj, t=tra, r=rot, s=[],
                              mo=False, pm=posMatrix+'.output')
        if objParent:
            cmds.parent(obj, objParent)

        if cmds.objectType(obj) == 'joint':
            if rotate:
                for a in ['X', 'Y', 'Z']:
                    cmds.setAttr(f'{obj}.jointOrient{a}', 0)

    
    # Connect U, V if they exist (locator guides)
    if 'U' in cmds.listAttr(obj):
        if cmds.getAttr(posInf+'.parameterU') > 1.0: # I think I'm getting rounding errors creating values above 1.0
            cmds.setAttr(obj+'.U', 1.0)
        else:
            if cmds.getAttr(posInf+'.parameterU') < 0:
                pos = 0
            else:
                pos = cmds.getAttr(posInf+'.parameterU')
            cmds.setAttr(obj+'.U', pos)
        cmds.connectAttr(obj+'.U', posInf+'.parameterU')

    if 'V' in cmds.listAttr(obj):
        if cmds.getAttr(posInf+'.parameterV') > 1.0: # I think I'm getting rounding errors creating values above 1.0
            cmds.setAttr(obj+'.V', 1.0)
        else:
            if cmds.getAttr(posInf+'.parameterV') < 0:
                pos = 0
            else:
                pos = cmds.getAttr(posInf+'.parameterV')
            cmds.setAttr(obj+'.V', pos)
        cmds.connectAttr(obj+'.V', posInf+'.parameterV')


    if return_pos:
        return pntOnSrf, posInf
    else:
        cmds.delete(pntOnSrf)
        return posInf