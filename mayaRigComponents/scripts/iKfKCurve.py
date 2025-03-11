import maya.cmds as cmds
from . import rdCtl as rdCtl
from lib_python_velan.mayaRigUtils.scripts import omUtil as omu
from lib_python_velan.mayaRigUtils.scripts import rigUtils as rigU
from lib_python_velan.mayaRigUtils.scripts import curves as crv
from lib_python_velan.mayaRigUtils.scripts import skincluster as skn
from lib_python_velan.mayaRigUtils.scripts import surfaces as srf


'''
import iKfKCurve

a=iKfKCurve.IkFk()
a.buildGuide('wrist_Lt_01', gdeNum=6)

# One or the other
a.buildIkFkRig()
a.buildFkRig()
'''

class IkFk(object):
    def __init__(self):
        # self.crvName  = ''
        self.gdeCrv = ''
        self.gdePos = []
        self.ctlGrp = ''

    
    def buildGuide(self, crvName, gdeNum):
        # self.crvName = crvName
        guide = self.crvToFkGdes(crvName, gdeNum)
        self.gdeCrv = guide[0]
        self.gdePos = self.gdePos+guide[1]


    def buildIkFkRig(self, ctlShape='circle', ctlSize=1.5, ctlColor=2, ctlSuffix='', jntSuffix='', margin=1.0):
        # Create rig from buildGuide() output, or use current selection.
        # Check for curve surface guide selection
        if cmds.ls(sl=1):
            ctlGde = []
            # Make sure its curve surface
            if cmds.objectType(omu.getDagPath(cmds.ls(sl=1)[0], shape=1))=='nurbsCurve':
                # Check for children
                if cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                    # See if children are guides
                    for i in cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                        # Add to gdeList
                        if i.endswith('_ctlGde'):
                            ctlGde.append(i)

                if ctlGde:
                    ctlGde.sort()
                    self.gdePos  = ctlGde
                    self.gdeCrv = cmds.ls(sl=1)[0]
                    self.iKfKfromGdes(self.gdeCrv, self.gdePos, ctlShape=ctlShape, ctlSize=ctlSize, ctlColor=ctlColor, 
                                      margin=margin, ctlSuffix=ctlSuffix, jntSuffix=jntSuffix)
        
        elif self.gdeCrv and self.gdePos:
            self.iKfKfromGdes(self.gdeCrv, self.gdePos, ctlShape=ctlShape, ctlSize=ctlSize, ctlColor=ctlColor, 
                              margin=margin, ctlSuffix=ctlSuffix, jntSuffix=jntSuffix)

        else:
            raise TypeError('No guide curve selected, or no guide curve in scene')

    def buildFkRig(self, ctlShape='circle', ctlSize=1.5, ctlColor=2, ctlSuffix='', jntSuffix='', margin=1.0):
        # Create rig from buildGuide() output, or use current selection.
        # Check for curve surface guide selection
        if cmds.ls(sl=1):
            ctlGde = []
            # Make sure its curve surface
            if cmds.objectType(omu.getDagPath(cmds.ls(sl=1)[0], shape=1))=='nurbsCurve':
                # Check for children
                if cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                    # See if children are guides
                    for i in cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                        # Add to gdeList
                        if i.endswith('_ctlGde'):
                            ctlGde.append(i)

                if ctlGde:
                    ctlGde.sort()
                    self.gdePos  = ctlGde
                    self.gdeCrv = cmds.ls(sl=1)[0]
                    self.fKfromGdes(self.gdeCrv, self.gdePos, ctlShape=ctlShape, ctlSize=ctlSize, ctlColor=ctlColor, margin=margin,
                                    ctlSuffix=ctlSuffix, jntSuffix=jntSuffix)

        elif self.gdeCrv and self.gdePos:
            self.fKfromGdes(self.gdeCrv, self.gdePos, ctlShape=ctlShape, ctlSize=ctlSize, ctlColor=ctlColor, margin=margin,
                            ctlSuffix=ctlSuffix, jntSuffix=jntSuffix)
            
        else:
            raise TypeError('No guide curve selected, or no guide curve in scene')

    # ------------------------------------------------------------------------------------------
    def snap(self, source, target):
        """Move one object to another.

        Args:
            source (str): The name of the maya object we want to move.
            target (str): The name of the maya object we want to move onto.
        """
        position = cmds.xform(target, worldSpace=True, matrix=True, query=True)
        cmds.xform(source, worldSpace=True, matrix=position)
    
    def crvToFkGdes(self, crvName, gdeNum):
        '''
        Creates FK guides along a curve.
        User can define guide position and rotation
        before building either FK, or IK/FK chain system

        crvName = (str) Name of curve to create guide from
        gdeNum  = (int) Number of guides to create on curve
        '''

        # Could be sending a selection as crvName. Convert selection to short name.
        if '|' in crvName:
            crvName = crvName.split('|')[-1]

        # Check for existing guide curve
        if not self.gdeCrv:
            self.gdeCrv = crvName
            # # Duplicate curve to remove transforms, and use as guide
            # newCrv = cmds.duplicate(crvName)
            # cmds.makeIdentity(newCrv[0], apply=True, t=1, r=1, s=1, n=0, pn=1)
            # crvNmeNew = cmds.rename(newCrv, crvName+'_gdeCrv')
            # cmds.delete(crvName)
        # else:
        #     crvNmeNew = self.gdeCrv


        nameSplit = crvName.split('_')
        sysName = '_'.join(nameSplit[:3])
        
        gdePos = crv.createEvenAlongCrv('joint', sysName, gdeNum, crvName, 1, keepCrv=1, suffix='ctlGde')
        # Building as chain, need to orient end joint in ctlPos chain
        rot = cmds.xform(gdePos[-2], q=True, ws=True, ro=True)
        cmds.xform(gdePos[-1], r=True, ro=rot)

        # Unparent from chain so user can orient guides
        [cmds.parent(ctl, crvName) for ctl in gdePos]

        # Define start of curve with yellow joint color
        # Make sure guide curve is not hidden (if created from other hidden crv)
        cmds.setAttr(gdePos[0]+'.overrideEnabled', 1)
        cmds.setAttr(gdePos[0]+'.overrideColor', 17)
        cmds.setAttr(crvName+'.v', 1)
        cmds.select(None)

        return crvName, gdePos

    def iKfKfromGdes(self, crvName, guides, ctlShape='circle', ctlSize=1.5, ctlColor=2, margin=1.0, ctlSuffix='', jntSuffix=''):
        '''
        Creates IK/FK chain system from curve with FKGuide children.(crvToFkGdes)

        crvName   = (str) Name of curve that has FK Guides as children
        ctlShape  = (str) rdCtl shape
        ctlSize   = (float) General rdCtl sizes
        ctlSuffix = (str) Suffix for rdCtl controllers
        jntSuffix = (str) Suffix for rdCtl joints
        '''

        ctlGrp = crvName+'_ctls'
        self.ctlGrp = ctlGrp

        if cmds.objExists(ctlGrp):
            if cmds.listRelatives(ctlGrp, c=True, type='transform'):
                [cmds.delete(item) for item in cmds.listRelatives(ctlGrp, c=True, type='transform')]
        else:
            ctlGrp = cmds.createNode('transform', n=ctlGrp, ss=True)

        # guides to ctls
        fkCtls = self.gdesToRdCtl(guides, ctlShape=ctlShape, ctlSize=ctlSize, ctlColor=ctlColor, 
                                  ctlSuffix=ctlSuffix, jntSuffix=jntSuffix, margin=margin)

        nameSplit = crvName.split('_')
        sysName = '_'.join(nameSplit[:3])+'_'

        if 'gdeCrv' in sysName:
            sysName = self.gdeCrv.replace('_gdeCrv', '_')

        # Root ctl
        ctlPar = rdCtl.Control(sysName+'root', match=fkCtls[0].jt, parent=ctlGrp,
                shape='cube', color='lightYellow', jt=False, size=ctlSize)
        # IK Chain
        ikJts = self.fkToIK(sysName, fkCtls)
        # Orient root grp
        self.snap(fkCtls[0].topCtl, ctlPar.grp)
        # Parent IK jts
        cmds.parent(ikJts[0], ctlPar.topCtl)
        # IK Handle
        ikHdl = cmds.ikHandle(sj=ikJts[0], ee=ikJts[1], p=2)
        cmds.parent(ikHdl[0], ctlPar.grp)
        ikCtl = rdCtl.Control(sysName+'ik', match=ikHdl[0], parent=ctlPar.topCtl,
                shape='diamond', color='lightYellow', jt=False, size=ctlSize*1.5)
        # Orient IK Tip Ctl
        rot = cmds.xform(ctlPar.topCtl, q=True, ws=True, ro=True)
        cmds.xform(ikCtl.grp, r=True, ro=rot)
        # Constrain IK Handel to IK Ctl
        cmds.parent(ikHdl[0], ikCtl.topCtl)
        cmds.setAttr(ikHdl[0]+'.visibility', 0)
        # Parent FK Chain to ikJnt
        cmds.parent(fkCtls[0].grp, ikJts[0])
        # UNparent ikTip Ctl to ctlPar grp
        cmds.parent(ikCtl.grp, ctlPar.grp)
        # Set ctlPar as IK Pole Vector
        cmds.poleVectorConstraint(ctlPar.topCtl, ikHdl[0])
        # Constrain IK Tip to look at root
        cmds.aimConstraint(ctlPar.topCtl, ikCtl.topCtl, weight=1, 
            upVector=(0, 1, 0), mo=0, worldUpType="vector", aimVector=(-1, 0, 0), worldUpVector=(0, 1, 0))
        # Hide guide crv
        cmds.hide(crvName)
        # cmds.rename(crvName, crvName+'_deleteMe')
        cmds.select(None)

    def fKfromGdes(self, crvName, guides, ctlShape='circle', ctlSize=1.5, ctlColor=2, ctlSuffix='', jntSuffix='', margin=1.0):
        '''
        Creates FK chain without IK parent, from fkGuides
        
        crvName  = (str) Name of curve that has FK Guides as children
        ctlShape = (str) rdCtl shape
        ctlSize  = (float) General rdCtl sizes    

        Usage:
        import rigComponents as rigComp

        crvName = 'skirt_Lt_01'
        rigComp.crvToFkGdes(crvName, 6)
        rigComp.fKfromGdes(crvName+'_gdeCrv')
        '''

        ctlGrp = crvName+'_ctls'
        self.ctlGrp = ctlGrp

        if cmds.objExists(ctlGrp):
            if cmds.listRelatives(ctlGrp, c=True, type='transform'):
                [cmds.delete(item) for item in cmds.listRelatives(ctlGrp, c=True, type='transform')]
        else:
            ctlGrp = cmds.createNode('transform', n=ctlGrp, ss=True)

        if cmds.objExists(crvName):
            if cmds.objectType(omu.getDagPath(crvName, shape=True))!='nurbsCurve':
                raise TypeError('Specified object is not a nurbs Curve')
        else:
            raise NameError('Specifired Curve does not exist in the scene')

        nameSplit = crvName.split('_')
        sysName   = '_'.join(nameSplit[:3])+'_'
        parent    = cmds.listRelatives(crvName, p=True)

        fkCtls = self.gdesToRdCtl(guides, ctlShape=ctlShape, ctlSize=ctlSize, ctlColor=ctlColor, 
                                      ctlSuffix=ctlSuffix, jntSuffix=jntSuffix, margin=margin)

        # Root ctl
        ctlPar = rdCtl.Control(sysName+'root', match=fkCtls[0].jt, parent=ctlGrp,
                shape='cube', color='lightYellow', jt=False, size=ctlSize)

        # Orient root grp
        self.snap(fkCtls[0].topCtl, ctlPar.grp)
        # Parent FK Chain to ikJnt
        cmds.parent(fkCtls[0].grp, ctlPar.topCtl)
        # Parent root to guide parent if exists
        if parent:
            cmds.parent(ctlPar.grp, parent[0])
        # Hide guide crv
        cmds.hide(crvName)
        # cmds.rename(crvName, crvName+'_deleteMe')

        return ctlPar.topCtl

    def gdesToRdCtl(self, fkGdes, ctlShape='circle', ctlSize=1.5, ctlColor=2, ctlSuffix='', jntSuffix='', margin=1.0):
        '''
        Converts FK guides into rdCtl fk chain. Sets side color
        
        fkGdes   = ([]) list of FK guides
        ctlShape = (str) rdCtl shape
        ctlSize  = (float) rdCtl size
        '''

        nameSplit = fkGdes[0].split('_')
        sysName = '_'.join(nameSplit[:3])

        fkCtls = []
        fkJts  = []
        for i, jnt in enumerate(fkGdes):
            ctlParent = fkCtls[-1].topCtl if fkCtls else None
            ctl = rdCtl.Control(sysName+'_fk{}'.format(i), match=jnt, parent=ctlParent,
                    shape=ctlShape, color='lightYellow', jt=True, size=ctlSize, ctlSuffix=ctlSuffix, jntSuffix=jntSuffix)
            fkCtls.append(ctl)
            fkJts.append(ctl.jt)

        [rigU.rdCtlSideColor(ctl, ctlColor, margin=margin) for ctl in fkCtls] # Set color based on ws
        [cmds.setAttr(jnt+'.v', 0) for jnt in fkJts]

        cmds.select(None)
        return fkCtls

    def fkToIK(self, ctlName, fkCtls):
        '''
        Creates singe chain IK to parent FK chain to

        ctlName = (str) rdCtl prefix
        fkCtls  = ([])  list of FKCtls to use as start and end of IK chain
                        Comes from gdesToRdCtl
        '''

        jts =[]
        jts.append(cmds.joint(n=ctlName+'ikRoot', p=cmds.xform(fkCtls[0].jt, q=True, ws=True, t=True)))
        jts.append(cmds.joint(n=ctlName+'ikTip', p=cmds.xform(fkCtls[-1].jt, q=True, ws=True, t=True)))

        for jnt in jts:
            cmds.joint(jnt, edit=True, zso=True, sao='zup', oj='xyz')
            cmds.setAttr(jnt+'.drawStyle', 2)

        return jts