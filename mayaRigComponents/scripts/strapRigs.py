import maya.cmds as cmds
from . import strap
from lib_python.mayaRigUtils.scripts import surfaces as srf
from lib_python.mayaRigUtils.scripts import omUtil as omu
from lib_python.mayaRigUtils.scripts import rigUtils as rigu
from . import rdCtl as rdCtl

'''
Functions to create nurbs strap rigs.

'''

def prepSrfDir():
    '''
    Prepares nurbs surface for strap rig
    '''
    if cmds.ls(sl=1):
        srfLst = []
        for sel in cmds.ls(sl=1):
            # Make sure transform is selected
            if cmds.objectType(cmds.ls(sl=1)[0]) != 'transform':
                raise TypeError('Select transform of object, Not shapes or nodes')
            # Make sure selection is nurbsSurface
            if cmds.objectType(omu.getDagPath(cmds.ls(sl=1)[0], shape=1)) != 'nurbsSurface':
                print(cmds.ls(sl=1)[0], '<'*50)
                raise TypeError('Selection is not of type nurbsSurface >> prepSrfDir')
            else:
                # Duplicate surface to remove transforms, and use as guide
                newSrf = cmds.duplicate(sel)
                cmds.makeIdentity(newSrf[0], apply=True, t=1, r=1, s=1, n=0, pn=1)
                cmds.setAttr(sel+'.v', 0)
                cmds.setAttr(newSrf[0]+'.v', 1)
                cmds.delete(sel)
                cnsSrf = cmds.rename(newSrf, sel)
                prepSrf = srf.nurbsSrfPrep(create=0, srfName=cnsSrf)
                srfLst.append(cnsSrf)
        cmds.select(srfLst, r=True)
    else:
        prepSrf = srf.nurbsSrfPrep(create=1)

    return prepSrf

def revSrfDir():
    '''
    Swap direction of nurbs UV
    '''
    if cmds.ls(sl=1):
        srfLst = []
        for sel in cmds.ls(sl=1):
            if cmds.objectType(omu.getDagPath(cmds.ls(sl=1)[0], shape=1)) != 'nurbsSurface':
                print(cmds.ls(sl=1)[0], '<'*50)
                raise TypeError('Selection is not of type nurbsSurface >> revSrfDir()')
            else:
                cmds.reverseSurface(sel, d=3, ch=0, rpo=1)
                cmds.reverseSurface(sel, d=1, ch=0, rpo=1)
                cmds.select(sel)
                srfLst.append(sel)
        cmds.select(srfLst, r=True)


def strapGuide(gdeRow, gdeCol, skpLst):
    '''
    Place guide locators on nurbs surface.
    Locators have U,V attr to adjust placement.

    gdeRow = (int) number of guide rows along nurbs U (red border)
    gdeCol = (int) number of guide columns along nurbs V (green border)
    skpLst = (bol) skip guides on nurbs end V border
    '''
    nrbLst = []
    if cmds.ls(sl=1):
        for sel in cmds.ls(sl=1):
            if cmds.objectType(omu.getDagPath(sel, shape=1)) == 'nurbsSurface':
                nrbLst.append(sel)
            else:
                print(cmds.ls(sl=1)[0], '<'*50)
                raise TypeError('Selection is not of type nurbsSurface >> strapGuide()')
    else:
        raise IndexError('Select a nurbsSurface(s)')

    if nrbLst != []:
        for nrb in nrbLst:
            rigu.lockUnlockSRT2(nrb, 1, 0)
            cmds.makeIdentity(nrb, apply=True, t=True, r=True, s=True)
            cmds.delete(nrb, ch=True)
            strpGde = None
            strpGde = strap.Strap() # Instance strap class to local variable
            strpGde.buildGuide(nrb, gdeRow, gdeCol, skipLast=skpLst)
            strpGde = None
        cmds.select(nrbLst)

def strapRig(globalVars, jntRows, jntColumns, makeFK, ikSpline, ikSplineNum,
    ctlSuffix, jntSuffix, localAxis, skipLast, globSclObj):
    '''
    globalVars  = ([ ]) List of rdCtl settings (margin, ctlSize, ctlShape, ctlColor, ctlSuffix, jntSuffix)
    jntRows     = (int) Number of rows of skin joints
    jntColumns  = (int) Number of columns of skin joints in each row
    makeFK      = (bol) Build rdCtls in FK heirarchy with FK off switch attr
    ikSpline    = (bol) Build additional IK spline down nurbs U
    ikSplineNum = (int) If > 0, create a ikSpline on dorito surface with ikSplineNum of joints
    ctlSuffix   = (str) Suffix to give to rdCtls
    jntSuffix   = (str) Suffix to give to rdCtl jnts
    localAxis   = (bol) Display joint local axis
    skipLast    = (bol) Skip joints on nurbs end V border
    globSclObj  = (str) Object to control global scale (looks for globalScale attr for connection)
    '''
    nrbLst = []
    if cmds.ls(sl=1):
        for sel in cmds.ls(sl=1):
            if cmds.objectType(omu.getDagPath(sel, shape=1)) == 'nurbsSurface':
                nrbLst.append(sel)
            else:
                print(cmds.ls(sl=1)[0], '<'*50)
                raise TypeError('Selection is not of type nurbsSurface >> strapRig()')
    else:
        raise IndexError('Select a nurbsSurface(s)')


    if nrbLst != []:
        for nrb in nrbLst:
            strpGde = None
            strpGde = strap.Strap()
            stpRig = strpGde.buildRig(nrb, jntRows, jntColumns, skipLast=skipLast, ctlShape=globalVars[2], ctlSize=globalVars[1], ctlColor=globalVars[3], 
                                  ctlSuffix=ctlSuffix, jntSuffix=jntSuffix, makeFK=makeFK, ikSpline=ikSpline, ikSplineNum=ikSplineNum, 
                                  margin=globalVars[0], lra=localAxis) # returns srfDor[0], allCtls, ctlGrp, dorJts
            # ctlRef's
            ctlRef = [i for i in cmds.listRelatives(stpRig[2], ad=True, type='transform') if i.endswith('_ctlRef')]# stpRig[2] = strap top group transform
            if cmds.objExists(globSclObj):
                if cmds.attributeQuery('globalScale', node=globSclObj, ex=True):
                    sclAxs = ['.sx', '.sy', '.sz']
                    for ctl in ctlRef:
                        [cmds.connectAttr(globSclObj+'.globalScale', ctl+axis) for axis in sclAxs]

            if jntRows > 0: # dorito joints exist
                dorJts = [jnt for sublist in stpRig[3] for jnt in sublist]
                if cmds.objExists(globSclObj):
                    if cmds.attributeQuery('globalScale', node=globSclObj, ex=True):
                        sclAxs = ['.sx', '.sy', '.sz']
                        for jnt in dorJts:
                            [cmds.connectAttr(globSclObj+'.globalScale', jnt+axis) for axis in sclAxs]

            strpGde = None

        return stpRig

def singleCtl(globalVars, ctlNme, ctlJnt):
    '''
    Creates a single rdCtl

    globalVars = ([ ]) List of rdCtl settings (margin, ctlSize, ctlShape, ctlColor, ctlSuffix, jntSuffix)
    ctlNme     = (str) Name of rdCtl
    ctlJnt     = (bol) Create a joint 
    '''
    ctlRut = cmds.spaceLocator(name=ctlNme+'_ctlRef')[0]
    cmds.setAttr(ctlRut+'.overrideEnabled', 1)
    cmds.setAttr(ctlRut+'.overrideDisplayType', 2) # Reference
    locShp = omu.getDagPath(ctlRut, shape=True)
    for axis in ['X', 'Y', 'Z']:
        cmds.setAttr(locShp+'.localScale'+axis, 0)

    ctl = rdCtl.Control(ctlNme, shape=globalVars[2], color=globalVars[3], size=globalVars[1], jt=ctlJnt, jntSuffix=globalVars[5], ctlSuffix=globalVars[4])
    rigu.rdCtlSideColor(ctl, priority=globalVars[3], margin=globalVars[0])
    cmds.parent(ctl.grp, ctlRut)
    if ctlJnt == True:
        cmds.setAttr(str(ctl.jt)+'.v', 0)
    cmds.addAttr(ctl.topCtl, ci=True, at='bool', sn='rdCtl', min=0, max=1, dv=1)
    cmds.setAttr(ctl.topCtl+'.rdCtl', l=True)
    cmds.select(None)

    return ctl

def singlePatch(globalVars, ctlNme, ctlJnt):
    '''
    Creates a single rdCtl constrained to a nurbs patch

    globalVars = ([ ]) List of rdCtl settings (margin, ctlSize, ctlShape, ctlColor, ctlSuffix, jntSuffix)
    ctlNme     = (str) Name of rdCtl
    ctlJnt     = (bol) Create a joint 
    '''
    tmpSrf = cmds.nurbsPlane(ch=1, d=2, v=1, p=(0, 0, 0), u=1, w=1, ax=(0, 1, 0), lr=1.0)
    bldSrf = cmds.rename(tmpSrf[0], ctlNme)

    ctlRut = cmds.spaceLocator(name=ctlNme+'_ctlRef')[0]
    cmds.setAttr(ctlRut+'.overrideEnabled', 1)
    cmds.setAttr(ctlRut+'.overrideDisplayType', 2) # Reference
    locShp = omu.getDagPath(ctlRut, shape=True)
    for axis in ['X', 'Y', 'Z']:
        cmds.setAttr(locShp+'.localScale'+axis, 0)

    ctl = rdCtl.Control(ctlNme, shape=globalVars[2], color=globalVars[3], size=globalVars[1], jt=ctlJnt, jntSuffix=globalVars[5], ctlSuffix=globalVars[4])
    rigu.rdCtlSideColor(ctl, priority=globalVars[3], margin=globalVars[0])
    cmds.parent(ctl.grp, ctlRut)
    srf.constToSrfMatrix(ctlRut, bldSrf)
    cmds.setAttr(ctl.jt+'.v', 0)
    cmds.addAttr(ctl.topCtl, ci=True, at='bool', sn='rdCtl', min=0, max=1, dv=1)
    cmds.setAttr(ctl.topCtl+'.rdCtl', l=True)
    cmds.select(None)