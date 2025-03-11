import maya.cmds as cmds
import maya.mel as mm
from maya.api.OpenMaya import MMatrix
import re
from . import omUtil as omu
from . import curves as crv
from . import surfaces as srf
from . import meshes as msh
from . import skincluster as skn
from . import shapes as shp
from lib_python.mayaRigComponents.scripts import rdCtl as rdCtl




######## Utils
def mirrorCtlShapes(ctl, axis='x', search='L_', replace='R_', doColor=True):
    '''
    Mirror the given curve (usually a controller) on the specified axis
    :param str     ctl: object one wants to mirror (can be a list of objs)
    :param str    axis: axis on which we want to perform the mirror
    :param str  search: pattern we want to search for
    :param str replace: pattern we want to replace
    '''

    curves = ctl if isinstance(ctl, list) else [ctl]

    # filter the input to check whether it's a transform or a shape
    crv_shapes = []
    for c in curves:
        if cmds.nodeType(c) == 'nurbsCurve':
            crv_shapes.append(c)
            continue
        if cmds.nodeType(c) == 'transform' or cmds.nodeType(c) == 'joint':
            crv_shapes += cmds.listRelatives(c, s=1, ni=1, type='nurbsCurve')

    crv_shapes = list(set(crv_shapes))  # removes duplicates

    for crv_shape in crv_shapes:
        if not search in crv_shape:
            LOG.warning('pattern not found in ' + crv_shape + ', skipping...')
            continue

        crv_transform    = cmds.listRelatives(crv_shape, p=1)[0]
        mirror_shape     = crv_shape.replace(search, replace, 1)
        mirror_transform = cmds.listRelatives(mirror_shape, p=1)[0]

        # make sure the shape doesn't have an input connection
        inConnection = cmds.listConnections(mirror_shape + '.create', s=1, d=0)
        if inConnection:
            LOG.warning('Input connection found on {0}.create, skipping tis object'.format(mirror_shape))
            continue

        # do the mirroring setup
        mtx = cmds.createNode('fourByFourMatrix', ss=1)
        attr = filter(None, [x*y for x, y in zip(['.in00', '.in11', '.in22'],
                                             [axis in x for x in 'xyz'])])[0]
        cmds.setAttr(mtx + attr, -1)

        # mirror in object space
        mirror = cmds.createNode('transformGeometry', ss=1, n='mirror')
        cmds.connectAttr(crv_shape + '.worldSpace', mirror + '.inputGeometry')
        cmds.connectAttr(mtx + '.output', mirror + '.transform')

        # localize (cancel the input transforms)
        inv_rot_ctlShape = cmds.createNode('decomposeMatrix', ss=1)
        cpm = cmds.createNode('composeMatrix', ss=1)
        localize = cmds.createNode('transformGeometry', ss=1)
        cmds.connectAttr(crv_transform + '.worldInverseMatrix', inv_rot_ctlShape + '.inputMatrix')
        cmds.connectAttr(inv_rot_ctlShape + '.outputRotate', cpm + '.inputRotate')
        cmds.connectAttr(mirror + '.outputGeometry', localize + '.inputGeometry')
        cmds.connectAttr(cpm + '.outputMatrix', localize + '.transform')

        # reorient like the mirrored transform
        dcm = cmds.createNode('decomposeMatrix', ss=1)
        mirror_rot = cmds.createNode('composeMatrix', ss=1)
        inv_rot = cmds.createNode('inverseMatrix', ss=1)
        mirror_tg = cmds.createNode('transformGeometry', ss=1)

        cmds.connectAttr(mirror_transform + '.worldInverseMatrix', dcm + '.inputMatrix')
        cmds.connectAttr(dcm + '.outputRotate', mirror_rot + '.inputRotate')
        cmds.connectAttr(mirror_rot + '.outputMatrix', inv_rot + '.inputMatrix')
        cmds.connectAttr(localize + '.outputGeometry', mirror_tg + '.inputGeometry')
        cmds.connectAttr(inv_rot + '.outputMatrix', mirror_tg + '.transform')

        # connect to the dummy curve
        cmds.connectAttr(mirror_tg + '.outputGeometry', mirror_shape + '.create')
        cmds.refresh()
        cmds.disconnectAttr(mirror_tg + '.outputGeometry', mirror_shape + '.create')

        # do the linewidth
        cmds.setAttr(mirror_shape + '.lineWidth', cmds.getAttr(crv_shape + '.lineWidth'))

        # and the color if we want to do it
        if doColor:
            cmds.setAttr(mirror_shape + '.overrideRGBColors', cmds.getAttr(crv_shape + '.overrideRGBColors'))
            cmds.setAttr(mirror_shape + '.overrideColor', cmds.getAttr(crv_shape + '.overrideColor'))
            cmds.setAttr(mirror_shape + '.overrideColorRGB', *cmds.getAttr(crv_shape + '.overrideColorRGB')[0])

        # cleans everything
        cmds.delete(mirror, inv_rot_ctlShape, cpm, localize, dcm, mirror_rot, inv_rot, mirror_tg)
        mirror_tg = cmds.createNode('transformGeometry', ss=1)

        cmds.connectAttr(mirror_transform + '.worldInverseMatrix', dcm + '.inputMatrix')
        cmds.connectAttr(dcm + '.outputRotate', mirror_rot + '.inputRotate')
        cmds.connectAttr(mirror_rot + '.outputMatrix', inv_rot + '.inputMatrix')
        cmds.connectAttr(localize + '.outputGeometry', mirror_tg + '.inputGeometry')
        cmds.connectAttr(inv_rot + '.outputMatrix', mirror_tg + '.transform')

def rdCtlSideColor(ctl, priority, margin=1.0):
    '''
    Sets rdCtl color based on world space along X axis
    ctl      = (instance) Class instance of rdCtl
    priority = (int or str) int = Primary or Secondary colors / str = color name.
    margin   = Units to define center X width
    '''
    if priority in [0,1,2]:
        # Get ctl world pos to determine color
        if -margin <= cmds.xform(ctl.topCtl, t=True, q=True, ws=True)[0] <= margin:
            ctl.color='lightYellow'
        elif cmds.xform(ctl.topCtl, t=True, q=True, ws=True)[0] < 0:
            if priority == 0:
                ctl.color='red'
            if priority == 1:
                ctl.color='lightRed'
            if priority == 2:
                ctl.color='pastelRed'

        else:
            if priority == 0:
                ctl.color='blue'
            if priority == 1:
                ctl.color='lightBlue'
            if priority == 2:
                ctl.color='pastelBlue'

    else:
        ctl.color = priority

def rdCtlOnVtx(vtxDic={}, orient=0, margin=1.0, duplicate=0, duplicateEnv=1, duplicateType='pp', duplicateName=None):
    '''
    Creates rdCtl's on selected vertex.

    vtxDic    = ({})    vtxDic[headCut_dorito1.vtx[49852], ctlName] = [orient, ctlShape, ctlSize, ctlColor, ctlSuffix, jntSuffix]
    orient    = (bol)   Orient ctls to surface
    margin    = (float) World space to color ctls
    duplicate = (bol)   Duplicate surface for dorito setup
    duplicateEnv   = (bol) Skin duplicate with ctl jnt's
    duplicateType = (str) pp=pointPosition, bs=blendShape, omim=outMesh_inMesh
    duplicateName = (str) Name to give the duplicate mesh
    '''


    mshNme = list(vtxDic)[0][0].split('.')[0] # Gets obj name from vertex

    ctls = []
    jts  = []
    foll = []
    for vtx, settings in vtxDic.items():
        pos = cmds.xform(vtx[0], q=1, ws=1, t=1)
        ctl = rdCtl.Control(vtx[1], shape=settings[1], size=settings[2], color='yellow', 
                            ctlSuffix=settings[4], jntSuffix=settings[5], match=None, parent=None, jt=True)
        cmds.xform(ctl.grp, ws=1, t=pos)
        fol = msh.constToMshFol(ctl.grp, mshNme, orient=settings[0])

        if settings[0]: # disconnect or result is double rotation
            cmds.disconnectAttr(fol[1][0]+'.rotate', ctl.grp+'.rotate')

        ctls.append(ctl)
        jts.append(ctl.jt)
        foll.append(fol[1])
        rdCtlSideColor(ctl, priority=settings[3], margin=margin)# Set color based on ws
    
    [cmds.setAttr(jnt+'.visibility', 0) for jnt in jts]
    [cmds.setAttr(jnt+'.radius', 0.1) for jnt in jts]

    if duplicate == 1:
        if duplicateName:
            dupMsh = cmds.duplicate(mshNme, n=duplicateName)[0]
            cmds.delete(dupMsh, ch=True)
        else:
            dupMsh = cmds.duplicate(mshNme, n=mshNme+'_dorito')[0]
            cmds.delete(dupMsh, ch=True)

        if duplicateEnv == 1:
            sknCls = cmds.skinCluster([ctl.jt for ctl in ctls], dupMsh, mi=2, bm=0, sm=0, dr=4, wd=0, tsb=1, n=dupMsh+'_doritoSkn')
            sknJts = skn.getSkinClusterInfluences(sknCls[0])
            for ctl in ctls:
                 if ctl.jt in sknJts:
                    jntIdx = skn.getSkinClusterInfluenceIndex(sknCls[0], ctl.jt)
                    cmds.connectAttr(ctl.grp+'.worldInverseMatrix', sknCls[0]+'.bindPreMatrix[{}]'.format(jntIdx))

        if duplicateType == 'pp':
             matchPointPosition(mshNme, dupMsh)
        if duplicateType == 'bs':
            cmds.blendShape(mshNme, dupMsh, n=mshNme+'_rdCtlOnVtx_bs', o='local', w=(0, 1.0))
        if duplicateType == 'omim':
            outMeshInMesh(mshNme, dupMsh)

        
    if duplicate == 1:
        if duplicateEnv == 1:
            return ctls, dupMsh, foll, sknCls
        else:
            return ctls, dupMsh, foll
    else:
        return ctls, foll
    # return ctls

def jntOnVtx(jntSuffix):
    if not cmds.ls(sl=True): # Something needs to be selected
        raise TypeError('Make a vertex selection')
    if not cmds.filterExpand(sm=31): # Checks for vertex selection
        raise TypeError('Make a vertex selection')

    vtxLst = cmds.ls(sl=True, flatten=True)
    cmds.select(None)
    mshNme = vtxLst[0].split('.')[0] # Gets obj name from vertex

    traLst = []
    jntLst = []
    grpLst = []
    for vtx in vtxLst:
        vtxNum = re.sub('[^A-Za-z0-9_]', '', vtx.split('.')[-1])+'_' # returns vtx+number
        pos = cmds.xform(vtx, q=1, ws=1, t=1)
        jnt = cmds.createNode('joint', n=mshNme+'_'+vtxNum+jntSuffix, ss=True)
        jntLst.append(jnt)
        cmds.xform(jnt, ws=1, t=pos)
        fol = msh.constToMshFol(jnt, mshNme, orient=True)
        traLst.append(fol[1][0])
        cmds.disconnectAttr(fol[1][0]+'.rotate', jnt+'.rotate') # disconnect or result is double rotation
        folGrp = cmds.createNode('transform', n=mshNme+'_'+vtxNum+'jntOnMsh', ss=True)
        grpLst.append(folGrp)
        cmds.parent(traLst, folGrp)
        parentConstraint(mshNme, folGrp, mo=True)

    return traLst, jntLst, grpLst

def rdCtlPreBindMat(dorLst, jntSuffix=None, bfrSuffix=None):
    '''
    Recives a list of rdCtls and object with rdJts in skincluster, as last selection.

    Looks for skincluster on last selection.
    Gets all joints in selection.
    Makes sure joints are in skincluster.
    Looks for joint bfr.
    Connects bfr worldInversMatrix to skincluster preBindMatrix.

    dorLst = [] Selection of joints and obj with skincluster as last selection

    '''

    sknCls = skn.getSkinClusters(dorLst[-1])
    if not sknCls:
        raise AttributeError('Last selected object does not have a skinCluster')

    sknJts = skn.getSkinClusterInfluences(sknCls)

    # Get all selected joints
    jntLst = []
    for item in dorLst:
        if cmds.objectType(item)=='joint':
            jntLst.append(item)

    # Make sure joints are in skincluster
    for jnt in jntLst:
        if jnt not in sknJts:
            jntLst.remove(jnt)

    # Connect pre bind matrix
    if jntLst != []:
        if 'mGear' in bfrSuffix:
            for jnt in jntLst:
                jntIdx = skn.getSkinClusterInfluenceIndex(sknCls, jnt)
                jntBfr = cmds.listConnections(jnt+'.inv_wm_conn_'+str(jnt), d=True)[0]
                if jntBfr:
                    cmds.connectAttr(jntBfr+'.worldInverseMatrix', sknCls+'.bindPreMatrix[{}]'.format(jntIdx), f=1)
            print('Done')

        else:
            for jnt in jntLst:
                jntIdx = skn.getSkinClusterInfluenceIndex(sknCls, jnt)
                jntBfr = jnt.replace(jntSuffix, bfrSuffix.split(' ')[0]) # Get joint bfr
                if jntBfr:
                    cmds.connectAttr(jntBfr+'.worldInverseMatrix', sknCls+'.bindPreMatrix[{}]'.format(jntIdx), f=1)
            print('Done')
    else:
        raise IndexError('Selected joints are not part of the skinCluster on last selection')
    
def lockUnlockSRT2(objs, attrVis, lock, t=['x','y','z'], r=['x','y','z'], s=['x','y','z']):
    '''
    objs    = ([])  List of object names
    attrVis = (bol) Hide from channel box if false
    lock    = (bol) Lock attr
    s = (bol) Scale
    r = (bol) Rotate
    t = (bol) Translate

    Example:
    rigU.LockUnlockSRT(s=1, r=1, t=1, attrVis=1, lock=0, objs=['locator1'])

    '''
    if type(objs) != list:
        objs = [objs]

    for obj in objs:
        [cmds.setAttr(obj+'.t'+axis.lower(), k=attrVis, l=lock) for axis in t]
        [cmds.setAttr(obj+'.r'+axis.lower(), k=attrVis, l=lock) for axis in r]
        [cmds.setAttr(obj+'.s'+axis.lower(), k=attrVis, l=lock) for axis in s]

def lockUnlockSRT(obj, lock, axisLst=[]):
    [cmds.setAttr(obj+'.'+axis, l=lock) for axis in axisLst]
    # Sublime Fold #

def hideUnhideSRT(obj, attrVis, axisLst=[]):
    [cmds.setAttr(obj+'.'+axis, k=attrVis) for axis in axisLst]

def listHierarchy(source, hierList, loop=0, fullPath=False):
    '''
    Recursive function that lists hierarchy

    source   = ('')  Name of top node
    hierList = ([])  Empty list to populate with hier
    fullPath = (bol) List full paths

    Usage:
        hierarchyList = []
        listHierarchy(source='thigh_l_bind', hierList=hierarchyList)
    '''
    if loop==0:
        hierList.insert(0, source)

    if fullPath == True:
        if cmds.listRelatives(source, c=True):
            for child in cmds.listRelatives(source, c=True, pa=True, f=True):
                hierList.append(child)
                listHierarchy(child, hierList, loop=1)
    else:
        if cmds.listRelatives(source, c=True):
            for child in cmds.listRelatives(source, c=True):
                hierList.append(child)
                listHierarchy(child, hierList, loop=1)

def parentConstraint(parent, child, t=['x','y','z'], r=['x','y','z'], s=['x','y','z'], mo=True):
    '''
    Node based parent constraint.

    parent = (str) Name of parent
    child  = (str) Name of child
    t      = []    List of axis to constrain to translate
    r      = []    List of axis to constrain to rotate
    s      = []    List of axis to constrain to scale
    mo     = (bol) Maintain offset option
    '''

    if type(child) != 'list':
        child = [child]

    for c in child:
        multMat = cmds.createNode('multMatrix', n=parent+'_multMatrix_rigUParCon', ss=True)
        decomp  = cmds.createNode('decomposeMatrix', n=parent+'_matrixDecomp_rigUParCon', ss=True)

        if mo == True:
            offset = cmds.createNode('multMatrix', n=parent+'_offset', ss=True)
            cmds.connectAttr(c+'.worldMatrix[0]', offset+'.matrixIn[0]', f=1)
            cmds.connectAttr(parent+'.worldInverseMatrix[0]', offset+'.matrixIn[1]', f=1)
            # Offset
            cmds.setAttr(multMat+'.matrixIn[0]', cmds.getAttr(offset+'.matrixSum'), type='matrix')
            cmds.connectAttr(parent+'.worldMatrix[0]', multMat+'.matrixIn[1]', f=1)
            cmds.connectAttr(c+'.parentInverseMatrix[0]', multMat+'.matrixIn[2]', f=1)
            cmds.connectAttr(multMat+'.matrixSum', decomp+'.inputMatrix', f=1)
            cmds.delete(offset)
        else:
            cmds.connectAttr(parent+'.worldMatrix[0]', multMat+'.matrixIn[0]', f=1)
            cmds.connectAttr(c+'.parentInverseMatrix[0]', multMat+'.matrixIn[1]', f=1)
            cmds.connectAttr(multMat+'.matrixSum', decomp+'.inputMatrix', f=1)

        [cmds.connectAttr(decomp+'.outputTranslate'+axis.upper(), c+'.translate'+axis.upper(), f=1) for axis in t if axis]
        [cmds.connectAttr(decomp+'.outputRotate'+axis.upper(), c+'.rotate'+axis.upper(), f=1) for axis in r if axis]
        [cmds.connectAttr(decomp+'.outputScale'+axis.upper(), c+'.scale'+axis.upper(), f=1) for axis in s if axis]

        return decomp

def delParentConstraint(delObj=None):
    '''
    delObj (str) Name of obj to delete constraint from
    '''
    axisLst = ['.tx', '.ty', '.tz', '.rx', '.ry', '.rz', '.sx', '.sy', '.sz']

    if delObj:
        nde = None
        for axis in axisLst:
            if cmds.listConnections(delObj+axis):
                if '_rigUParCon' in cmds.listConnections(delObj+axis)[0]:
                    nde = cmds.listConnections(delObj+axis)[0]
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

def resetSRT(obj, t=['x','y','z'], r=['x','y','z'], s=['x','y','z']):
    [cmds.setAttr(obj+'.t'+axis, 0) for axis in t if axis]
    [cmds.setAttr(obj+'.r'+axis, 0) for axis in r if axis]
    [cmds.setAttr(obj+'.s'+axis, 1) for axis in s if axis]

def directConnectSRT(source, dest, channels=['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']):
    [cmds.connectAttr(source+'.'+axis, dest+'.'+axis, f=1) for axis in channels if axis]

def outMeshInMesh(source, target):
    srcShp = omu.getDagPath(source, shape=True)
    tgtShps = cmds.listRelatives(target, c=True, s=True)
    orig = None
    if tgtShps:
        for s in tgtShps:
            if 'Orig' in s:
                orig = s
        if orig != None:
            tgtShp = orig
        else:
            tgtShp = omu.getDagPath(target, shape=True)

    if srcShp and tgtShp:
        cmds.connectAttr(srcShp+'.outMesh', tgtShp+'.inMesh', f=True)

def matchPointPosition(driver, driven): # WIP
    '''
    Makes one object match another (translation and deformation), of same type and topology.
    Target will match Source. Target can be deformed after the fact.
    '''
    
    if not cmds.objExists(driver):
        raise NameError('Source object does not exist in the scene')
    if not cmds.objExists(driven):
        raise NameError('Target object does not exist in the scene')
    if cmds.objectType(omu.getDagPath(driver, shape=1)) != cmds.objectType(omu.getDagPath(driven, shape=1)):
        raise TypeError('Source and Target are not of the same type')

    srcShp = omu.getDagPath(driver, shape=True)
    tgtShp = omu.getDagPath(driven, shape=True)


    # Polymesh
    if cmds.objectType(omu.getDagPath(driver, shape=1)) == 'mesh':
        cmds.xform(driven, t=(0,0,0))
        matchPnt = cmds.createNode('transformGeometry', ss=True)
        cmds.connectAttr(driver+'.worldMatrix[0]', matchPnt+'.transform')
        cmds.connectAttr(srcShp+'.outMesh', matchPnt+'.inputGeometry')

        if cmds.listConnections(tgtShp+'.inMesh') != None: # We have a deformer
            ndeTyp = cmds.objectType(cmds.listConnections(tgtShp+'.inMesh'))
            if ndeTyp == 'skinCluster':
                nde = cmds.listConnections(tgtShp+'.inMesh')[0]
                shps = cmds.listRelatives(driven, c=True, s=True)
                if shps:
                    orig = None
                    for s in shps:
                        if 'Orig' in s:
                            orig = s
                    if orig:
                        tgtShp = orig

                cmds.connectAttr(matchPnt+'.outputGeometry', tgtShp+'.inMesh', f=1)
                # cmds.connectAttr(matchPnt+'.outputGeometry', nde+'.input[0].inputGeometry', f=1)
            else:
                raise TypeError('Unknown deformer present on shape node. Update rigU.matchPointPosition with new deformer.')
        else:
            cmds.connectAttr(matchPnt+'.outputGeometry', tgtShp+'.inMesh', f=1)


    # Nurbs Surface
    if cmds.objectType(omu.getDagPath(driver, shape=1)) == 'nurbsSurface':
        cmds.xform(driven, t=(0,0,0))
        matchPnt = cmds.createNode('transformGeometry', ss=True)
        cmds.connectAttr(driver+'.worldMatrix[0]', matchPnt+'.transform')
        cmds.connectAttr(srcShp+'.worldSpace[0]', matchPnt+'.inputGeometry')
        
        if cmds.listConnections(tgtShp+'.create') != None: # We have a deformer
            ndeTyp = cmds.objectType(cmds.listConnections(tgtShp+'.create'))
            if ndeTyp == 'skinCluster':
                nde = cmds.listConnections(tgtShp+'.create')[0]
                shps = cmds.listRelatives(driven, c=True, s=True)
                if shps:
                    orig = None
                    for s in shps:
                        if 'Orig' in s:
                            orig = s
                    if orig:
                        tgtShp = orig

                cmds.connectAttr(matchPnt+'.outputGeometry', tgtShp+'.create', f=1)
                # cmds.connectAttr(matchPnt+'.outputGeometry', nde+'.input[0].inputGeometry', f=1)
            else:
                raise TypeError('Unknown deformer present on shape node. Update rigU.matchPointPosition with new deformer.')
        else:
            cmds.connectAttr(matchPnt+'.outputGeometry', tgtShp+'.create', f=1)


    # Nurbs Curve
    if cmds.objectType(omu.getDagPath(driver, shape=1)) == 'nurbsCurve':
        cmds.xform(driven, t=(0,0,0))
        matchPnt = cmds.createNode('transformGeometry', ss=True)
        cmds.connectAttr(driver+'.worldMatrix[0]', matchPnt+'.transform')
        cmds.connectAttr(srcShp+'.worldSpace[0]', matchPnt+'.inputGeometry')

        if cmds.listConnections(tgtShp+'.create') != None: # We have a deformer
            ndeTyp = cmds.objectType(cmds.listConnections(tgtShp+'.create'))
            if ndeTyp == 'skinCluster':
                nde = cmds.listConnections(tgtShp+'.create')[0]
                shps = cmds.listRelatives(driven, c=True, s=True)
                if shps:
                    orig = None
                    for s in shps:
                        if 'Orig' in s:
                            orig = s
                    if orig:
                        tgtShp = orig

                cmds.connectAttr(matchPnt+'.outputGeometry', tgtShp+'.create', f=1)
                # cmds.connectAttr(matchPnt+'.outputGeometry', nde+'.input[0].inputGeometry', f=1)
            else:
                raise TypeError('Unknown deformer present on shape node. Update rigU.matchPointPosition with new deformer.')
        else:
            cmds.connectAttr(matchPnt+'.outputGeometry', tgtShp+'.create', f=1)

def constrainLocatorToNrb():
    '''
    Used for FX locators in the rig. Need to constrain the locators to the rig.
    Easy to create a nurbs surface, and transfer weights to the surface.
    Makes is easy to rebuild if necessary.
    '''
    for i in cmds.ls(sl=1):
        shape = i+'Shape'
        pos = [cmds.getAttr(shape+'.localPositionX'), cmds.getAttr(shape+'.localPositionY'), cmds.getAttr(shape+'.localPositionZ')]
        loc = cmds.spaceLocator(n=i+'_loc', p=(0,0,0))[0]
        surf = cmds.nurbsPlane(ch=1, d=3, v=1, p=pos, u=1, w=0.1, ax=(0, 1, 0), lr=1, n=i+'_drv')[0]
        cmds.xform(loc, t=pos)
        srf.constToSrfMatrix(loc, surf)
        cmds.parent(loc, surf)
        parentConstraint(loc, i, mo=True)

######## Strap rigs
def ikSplineOnCrv(crvName, ikNum, suffix='jntSuffix'):
    # IK chain with last joint hack fix
    ikJts = crv.createEvenAlongCrv('joint', crvName.replace('_srfCrv', ''), ikNum, crvName, chain=1, keepCrv=1, suffix='spljnt')
    last = cmds.duplicate(ikJts[-1], n=crvName.replace('_srfCrv', '')+'_{}_twistHelperHack'.format(len(ikJts)))[0]
    cmds.parent(last, ikJts[-1], r=0)
    cmds.joint(ikJts[-1], zso=1, ch=1, e=1, oj='xyz', sao='yup')
    # One more joint to orient the 'last' joint hack fix
    lastOri = cmds.duplicate(last, n='lastOrient')
    cmds.parent(lastOri, last)
    cmds.joint(last, zso=1, ch=1, e=1, oj='xyz', sao='yup')
    cmds.delete(lastOri)
    cmds.setAttr(last+'.tx', cmds.getAttr(ikJts[-1]+'.tx')/4)
    ikJts.append(last)

    ikHdl   = cmds.ikHandle(solver='ikSplineSolver', startJoint=ikJts[0], endEffector=last, 
            rootTwistMode=0, n=crvName.replace('_srfCrv', '')+'_ikSpline', createCurve=0, curve=crvName, simplifyCurve=False, 
            rootOnCurve=True, parentCurve=False)

    return ikJts, ikHdl

def ikSplineCrvStretch(sysName, motPthNdes, jts, paramJts, ctlAttr):
    '''
    Uses joints, that are constrained to a curve by consToCrvParametric(),
    to drive position along curve for spline joints. Giving anim the option
    to turn off Maintain Length for the ik spline.
    Currently used in ikSplineOnSrf()        

    sysName    = (str) System name to give new nodes created herein
    motPthNdes = ([])  List of param joint mp nodes from createEvenAlongCrv()
    jts        = ([])  List of spline joints from ikSplineOnCrv()
    paramJts   = ([])  List of param joints from createEvenAlongCrv()
    ctlAttr    = ([])  Rig root ctl that will receive the Maintain Length attr
    '''

    if not cmds.objExists(ctlAttr):
        raise NameError('ctlAttr obj does not exist in the scene')
    else:
        cmds.addAttr(ctlAttr, at='bool', k=True, ci=True, sn='MaintainLength', dv=1)

    for i, nde in enumerate(motPthNdes[:-1]):
        distBet = cmds.createNode('distanceBetween', n=sysName+'_ikDistBet_'+str(i), ss=True)
        distZero = cmds.createNode('floatMath', n=sysName+'_ikDistZero_'+str(i), ss=True)
        distDiff = cmds.createNode('floatMath', n=sysName+'_ikDistDiff_'+str(i), ss=True)
        rigScale = cmds.createNode('floatMath', n=sysName+'_rigScale'+str(i), ss=True)
        cmds.connectAttr(motPthNdes[i]+'.allCoordinates', distBet+'.point1')
        cmds.connectAttr(motPthNdes[i+1]+'.allCoordinates', distBet+'.point2')
        cmds.setAttr(rigScale+'.operation', 3) # Divide
        cmds.setAttr(distZero+'.operation', 1) # Subtract
        cmds.setAttr(distDiff+'.operation', 1) # Subtract
        cmds.setAttr(distZero+'.floatA', cmds.getAttr(distBet+'.distance'))
        cmds.connectAttr(distBet+'.distance', rigScale+'.floatA')
        cmds.connectAttr(rigScale+'.outFloat', distZero+'.floatB')
        cmds.setAttr(distDiff+'.floatA', cmds.getAttr(distBet+'.distance'))
        cmds.connectAttr(distZero+'.outFloat', distDiff+'.floatB')
        # Maintain length tx
        lengthCond = cmds.createNode('condition', n=sysName+'_lengthCond_'+str(i), ss=True)
        cmds.connectAttr(ctlAttr+'.MaintainLength', lengthCond+'.firstTerm')
        cmds.setAttr(lengthCond+'.secondTerm', 1)
        cmds.connectAttr(distDiff+'.outFloat', lengthCond+'.colorIfFalseR')
        cmds.setAttr(lengthCond+'.colorIfTrueR', cmds.getAttr(distBet+'.distance'))
        cmds.connectAttr(lengthCond+'.outColorR', jts[i+1]+'.translateX')
