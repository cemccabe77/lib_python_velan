import maya.cmds as cmds
from maya import OpenMaya as om
from maya.api.OpenMaya import *
from . import omUtil as omu


def createEvenAlongCrv(objType, objName, count, crvName, chain=0, jntAxis='xyz', keepCrv=0, suffix='gde', radius=0.3, lra=True):
    '''
    Evenly space joints along curve (but does not constrain them to curve)

    objType = (str) Type of item to create along curve('joint' or 'locator')
    objName = (str) Name for created obj's
    count   = (int) Number of items to create
    crvName = (str) Name of curve
    keepCrv = (bol) Delete curve?
    suffix  = (str) Suffix
    radius  = (float) If joint, set joint radius
    lra     = (bol) If joint, turn on local rotation axis display

    '''
    if cmds.objExists(crvName):
        if cmds.objectType(omu.getDagPath(crvName, shape=True))!='nurbsCurve':
            raise TypeError('Curve is not a nurbs curve')
    else:
        raise NameError('Curve does not exist in the scene')

    # Check for existing guides. Gets highest numbered
    gdeList = cmds.ls(objName+'*'+suffix)
    if gdeList:
        lastNum = gdeList[-1].split('_')[-2]
        startNum = int(lastNum)+1
    else:
        startNum = 0

    # objName needs to end with '_' so numbering of new obj's is correct
    if not objName.endswith('_'):
        objName = objName+'_'

    objList = []
    crvShp = omu.getDagPath(crvName, shape=1)


    crvFn = om.MFnNurbsCurve(omu.getDagPath(crvName, shape=0))

    if count == 1:
        parameter = crvFn.findParamFromLength(crvFn.length() * 0.5)
        point = om.MPoint()
        crvFn.getPointAtParam(parameter, point)
        if objType == 'joint':
            num = 0
            jt = cmds.createNode('joint', n=objName+str(num)+'_'+suffix)
            cmds.xform(jt,t=[point.x,point.y,point.z])
            objList.append(jt)
        if objType == 'locator':
            num = 0
            item = cmds.spaceLocator(n=objName+str(num)+'_'+suffix)
            cmds.addAttr(item, at='float', k=True, ci=True, sn='U', max=1.0, min=0.0) # Used in strap.strapRigDorito()
            cmds.addAttr(item, at='float', k=True, ci=True, sn='V', max=1.0, min=0.0) # Used in strap.strapRigDorito()
            itemTra = cmds.listRelatives(item, p=1)
            cmds.xform(itemTra,t=[point.x,point.y,point.z])
            objList.append(item[0])

    else:
        if cmds.getAttr(crvShp+'.form') == 2: # Detects if open or closed curve. 2=Periodic
            spacing = 1.0/(count)
        else:
            spacing = 1.0/(count-1)

        for i in range(count):
            parameter = crvFn.findParamFromLength(crvFn.length() * spacing * i)
            point = om.MPoint()
            crvFn.getPointAtParam(parameter, point)
            if objType == 'joint':
                num = startNum+i
                jt = cmds.createNode('joint', n=objName+str(num)+'_'+suffix)
                cmds.xform(jt,t=[point.x,point.y,point.z])
                objList.append(jt)

                if chain and i != 0:
                    cmds.parent(jt, objList[-2])

            if objType == 'locator':
                num = startNum+i
                item = cmds.spaceLocator(n=objName+str(num)+'_'+suffix)
                cmds.addAttr(item, at='float', k=True, ci=True, sn='U', max=1.0, min=0.0) # Used in strap.strapRigDorito()
                cmds.addAttr(item, at='float', k=True, ci=True, sn='V', max=1.0, min=0.0) # Used in strap.strapRigDorito()
                itemTra = cmds.listRelatives(item, p=1)
                cmds.xform(itemTra,t=[point.x,point.y,point.z])
                objList.append(item[0])

    if len(objList)>0 and objType=='joint':
        # Orient joint
        for jt in objList:
            cmds.joint(jt, edit=True, zso=True, sao='yup', oj=jntAxis)
            cmds.setAttr(jt+'.radius', radius)
            if lra == True:
                cmds.setAttr(jt+'.displayLocalAxis', 1)

    if not keepCrv:
        cmds.delete(crvName)

    return objList

def consToCrv(consTo, crvName):
    '''
    Constrain items to curve (position only)

    ConsTo  = (list) Items that will be constrained to curve
    crvName = (str) Curve to constrain items to
    '''
    if type(consTo) != list:
        consTo = [consTo]

    pocList = []
    for i in consTo:
        pos=cmds.xform(i, q=True, ws=True, t=True)
        uParam = getUParam(pos, crvName)
        crvInfNde = cmds.createNode('pointOnCurveInfo', n=crvName+'_pocInf', ss=True)
        cmds.connectAttr(crvName+'.worldSpace[0]', crvInfNde+'.inputCurve')
        cmds.setAttr(crvInfNde+'.parameter', uParam)
        cmds.connectAttr(crvInfNde+'.position', i+'.translate')
        pocList.append(crvInfNde)

    return pocList

def consToCrvParametric(consTo, crv, translate=True, rotate=True, upType=4, inverseUp=0, inverseFront=0, frontAxis=0, upAxis=2, upObj=None):
    '''
    Constrain items to curve by motionPath nodes.
    Objects do not need to be placed on top of curve.
    This function gets closest point on curve to make constraint.

    ConsTo     = ([]) Items that will be constrained to curve
    crv        = (str) Curve to constrain items to
    upType     = (Int) 1=Object, 2=Object Rototation, 3=Vector, 4=Normal
    '''

    # Check crv exists and is a nurbsCurve
    if cmds.objExists(crv):
        if cmds.objectType(omu.getDagPath(crv, shape=True)) != 'nurbsCurve':
            raise TypeError ('Curve object is not a curve')
    else:
        raise NameError('Curve object does not exist in scene')

    # # If passing a single obj for constraint
    if type(consTo) != list:
        consTo = [consTo]

    pthNodes = []
    for obj in consTo:
        pos=cmds.xform(obj, q=True, ws=True, t=True)
        uParam = getUParam(pos, crv)
        motPth = cmds.createNode('motionPath', n=obj+'_motPath', ss=True)
        cmds.connectAttr(crv+'.worldSpace[0]', motPth+'.geometryPath')
        if translate == True:
            cmds.connectAttr(motPth+'.allCoordinates', obj+'.translate')
        if rotate == True:
            cmds.connectAttr(motPth+'.rotate', obj+'.rotate')
        cmds.setAttr(motPth+'.uValue', uParam)

        if upType in [1, 2]:
            cmds.setAttr(motPth+'.worldUpType', upType)
            if cmds.objExists(upObj):
                cmds.connectAttr(upObj+'.worldMatrix[0]', motPth+'.worldUpMatrix')
            else:
                raise ValueError('Object {} does not exist'.format(upObj))
        else:
            cmds.setAttr(motPth+'.worldUpType', upType)

        cmds.setAttr(motPth+'.inverseUp', inverseUp)
        cmds.setAttr(motPth+'.inverseFront', inverseFront)
        cmds.setAttr(motPth+'.frontAxis', frontAxis)
        cmds.setAttr(motPth+'.upAxis', upAxis)

        pthNodes.append(motPth)

    return pthNodes

def consToCrvNonParametric(consTo, crv, upType=4, inverseUp=0, inverseFront=0, frontAxis=0, upAxis=2, upObj=None):
    '''
    Constrain items to curve by motionPath nodes.
    Objects do not need to be placed on top of curve.
    This function gets closest point on curve to make constraint.

    consTo = ([])  Objects that will be constrained to curve
    crv    = (str) Curve that objects will be constrained to
    upType = (Int) 1=Object, 2=Object Rototation, 3=Vector, 4=Normal
    '''

    # Check crv exists and is a nurbsCurve
    if cmds.objExists(crv):
        if cmds.objectType(omu.getDagPath(crv, shape=True)) != 'nurbsCurve':
            raise TypeError ('Curve object is not a curve')
    else:
        raise NameError('Curve object does not exist in scene')

    # If passing a single obj for constraint
    if type(consTo) != list:
        consTo = [consTo]

    pthNodes = []
    for obj in consTo:
        motPth = cmds.createNode('motionPath', n=obj+'_motionPath', ss=True)
        uParam = getUParamByLength(obj, crv)
        print(uParam)
        cmds.connectAttr(crv+'.ws[0]', motPth+'.geometryPath')
        cmds.connectAttr(motPth+'.allCoordinates', obj+'.translate')
        cmds.connectAttr(motPth+'.rotate', obj+'.rotate')
        cmds.setAttr(motPth+'.fractionMode', 1)
        cmds.setAttr(motPth+'.uValue', uParam)

        if upType in [1, 2]:
            cmds.setAttr(motPth+'.worldUpType', upType)
            if cmds.objExists(upObj):
                cmds.connectAttr(upObj+'.worldMatrix[0]', motPth+'.worldUpMatrix')
            else:
                raise ValueError('Object {} does not exist'.format(upObj))
        else:
            cmds.setAttr(motPth+'.worldUpType', upType)

        cmds.setAttr(motPth+'.inverseUp', inverseUp)
        cmds.setAttr(motPth+'.inverseFront', inverseFront)
        cmds.setAttr(motPth+'.frontAxis', frontAxis)
        cmds.setAttr(motPth+'.upAxis', upAxis)

        pthNodes.append(motPth)

    return pthNodes

def getUParam(pnt, crv):
    '''
    Get point on curve
    crv = (str) = Curve name
    '''
    point = om.MPoint(*pnt)

    curveFn = om.MFnNurbsCurve(omu.getDagPath(crv, shape=0))
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

def getUParamByLength(obj, crv):
    '''
    Gets UParam on crv by getting position on curve, arc 'length' value (Non-Parametric UParam)
    obj = (str) Object to retrieve closest point from
    crv = (str) Curve to query
    '''
   
    '''
    # OM (Seems to have difficulty finding closest point and fails, when to close to end of curve)
    fn = MFnNurbsCurve(MGlobal.getSelectionListByName(crv).getDagPath(0))
    _, u = fn.closestPoint(MPoint(cmds.xform(obj, q=1, ws=1, t=1)))
    uParam = fn.findLengthFromParam(u) / fn.length()
    '''
   
    # By Nodes
    objPos = cmds.createNode('decomposeMatrix', n='objWorldSpace', ss=True)
    pocInf = cmds.createNode('nearestPointOnCurve', n='pocInfo', ss=True)
    arcLen = cmds.createNode('curveInfo', n='arcLen', ss=True)
    posLen = cmds.createNode('arcLengthDimension', n='posInfo', ss=True)
    uValue = cmds.createNode('remapValue', n='posUVal', ss=True)

    cmds.connectAttr(crv+'.ws[0]', pocInf+'.inputCurve')
    cmds.connectAttr(crv+'.ws[0]', posLen+'.nurbsGeometry')
    cmds.connectAttr(crv+'.ws[0]', arcLen+'.inputCurve')
    cmds.connectAttr(obj+'.wm[0]', objPos+'.imat')
    cmds.connectAttr(objPos+'.outputTranslate', pocInf+'.inPosition')
    cmds.connectAttr(pocInf+'.parameter', posLen+'.uParamValue')
    cmds.connectAttr(posLen+'.arcLength', uValue+'.inputValue')
    cmds.connectAttr(arcLen+'.arcLength', uValue+'.inputMax')

    uParam = cmds.getAttr(uValue+'.outValue')

    cmds.delete(objPos, pocInf, arcLen, uValue)
    posPar = cmds.listRelatives(posLen, p=True)
    cmds.delete(posPar)
   
    return uParam

def crvFromJtChain(root, crvName, d=3):
    '''
    root    = (str) Root joint of joint chain
    d       = (int) Curve Degree
    crvName = (str) Name of output curve
    '''
    joints = posFromJtChain(root)
    newCrv = cmds.curve(d=d, p=joints)
    cmds.rename(newCrv, crvName)

def posFromJtChain(root):
    '''
    Gets position of each joint in joint chain.
    Used in crvFromJtChain to create curve from joint chain.
   
    root = (str) Root of joint chain
    '''
    # raise DeprecationWarning
    pos = [cmds.xform(root, q=True, t=True, ws=True)]
    children = cmds.listRelatives(root, c=True) or []
    for child in children:
        pos.extend(posFromJtChain(child))
    return pos

def queryCVCount(crvName):
    '''
    Gives the number of CV's
    number of CVs = degree + spans.
    '''
    degs = cmds.getAttr( crvName+'.degree' )
    spans = cmds.getAttr( crvName+'.spans' )
    cvs = degs+spans
    return cvs

def numCVs(crvName):
    return int(cmds.getAttr (crvName+'.degree'))+ (cmds.getAttr (crvName+'.spans'))

def updateOrigShapeCrv(source, target):
    '''
    Updates target curve shape with source curve shape.
    '''
    deleteUnusedShapesCrv()

    for obj in [source, target]:
        if cmds.objectType(omu.getDagPath(obj, shape=1)) != 'nurbsCurve':
            print(obj, '<'*50)
            raise TypeError('Object is not of type nurbsSurface')

    targetShapes = cmds.listRelatives(target, c=1, s=1)
    if len(targetShapes) > 1:
        for shape in targetShapes:
            if 'Orig' in shape:
                targetShape = shape
    else:
        targetShape = targetShapes[0]

    sourceShape = cmds.listRelatives(source, c=1, s=1)
    if len(sourceShape) > 1:
        for shape in sourceShape:
            if 'Orig' in shape:
                sourceShape = shape
    else:
        sourceShape = sourceShape[0]

    if targetShape and sourceShape:
        cmds.connectAttr(sourceShape+'.worldSpace[0]', targetShape+'.create')
        cmds.refresh()
        cmds.disconnectAttr(sourceShape+'.worldSpace[0]', targetShape+'.create')

def deleteUnusedShapesCrv():
    '''
    Removes all unused shape nodes in the scene
    '''
    allMeshes = cmds.ls(type="mesh") # List all shape nodes
    deadIntermediates = []
    for mesh in allMeshes:
        if cmds.getAttr(mesh+'.io'): #intermediateObject
            if not cmds.listConnections(mesh):
                deadIntermediates.append(mesh)

    if deadIntermediates:
        for io in deadIntermediates:
            cmds.delete(io)

def splitCurves(reduceCrv=0):
    '''
    Splits curve shapes into new curves
    crvName = (sel) current selection
    '''
    if cmds.ls(sl=1):
        crvName = cmds.ls(sl=1)[0]
        if cmds.objectType(omu.getDagPath(crvName, shape=True)) == 'nurbsCurve':
            cmds.parent(crvName, w=True)

            shps = []
            shps = cmds.listRelatives(crvName, type='shape')
            if shps != []:
                par = cmds.createNode('transform', n='splitCurves', ss=True)
                newShp = []
                for shp in shps[1:]:
                    tra = cmds.createNode('transform', n=shp+'top', ss=True)
                    cmds.parent(shp, tra, s=True)
                    child = cmds.listRelatives(tra, c=True)[0]
                    cmds.parent(child, par, s=True)
                    cmds.delete(tra)
                    newShp.append(child)

                cmds.parent(crvName, par)
                newShp.append(crvName)
                cmds.select(None)

            if reduceCrv > 0:
                [cmds.delete(shp) for shp in newShp[::2]]
                [newShp.remove(shp) for shp in newShp[::2]]

                if reduceCrv > 1: # reduce again
                    [cmds.delete(shp) for shp in newShp[::2]]
        else:
            raise TypeError('Current selection is not of type "nurbsCurve"')