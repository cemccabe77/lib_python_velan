import maya.cmds as cmds
from . import rdCtl as rdCtl
from lib_python_velan.mayaRigUtils.scripts import omUtil as omu
from lib_python_velan.mayaRigUtils.scripts import rigUtils as rigu
from lib_python_velan.mayaRigUtils.scripts import curves as crv
from lib_python_velan.mayaRigUtils.scripts import skincluster as skn
from lib_python_velan.mayaRigUtils.scripts import surfaces as srf
from collections import OrderedDict


'''
Builds a strap rig with driver surface, and driven dorito surface.
Ctls in driver surface will drive doritio surface. Which will in turn
drive rig mesh

####################################################
Usage:
import rigComponents as rigComp;reload(rigComp)
import strap;reload(strap)

a=strap.Strap()
newSrf = srf.nurbsSrfPrep(cmds.ls(sl=1)[0])
a.buildGuide(newSrf, rows=1, columns=5, skipLast=0)
a.buildRig(jntRows=5, jntColumns=9)
####################################################


'''

class Strap(object):
    def __init__(self):
        self.srfName  = ''
        self.dorSrf   = ''
        self.rows     = 0
        self.columns  = 0
        self.skipLast = 0
        self.ctlGrp   = None
        self.gdeRows  = OrderedDict()

    
    def buildGuide(self, srfName, rows, columns, objType='locator', suffix='ctlGde', skipLast=0, constrain=1):
        '''
        srfName  = (str) Nurbs surface to place ctl guides on
        rows     = (int) Number of guide rows to put on surface
        columns  = (int) Number of columns of guides in each row
        skipLast = (bol) Skip last guide to prevent double guides on nurbs edges (closed surface)
        '''
        self.srfName  = srfName
        self.rows     = rows
        self.columns  = columns
        self.skipLast = skipLast

        self.strapRigLayout(self.srfName, rows, columns, objType=objType, suffix=suffix, 
                                            skipLast=skipLast, constrain=constrain)

        if cmds.objExists(srfName):
            cmds.select(srfName)


    def buildRig(self, srfName, jntRows, jntColumns, skipLast, ctlShape='circle', ctlSize=1.5, ctlColor=2, ctlSuffix='', jntSuffix='', makeFK=0, ikSpline=False, ikSplineNum=0, margin=1.0, lra=True):
        '''
        Create rig from buildGuide() output, or use current selection.
        Check for nurbs surface guide selection

        srfName     = (str) nurbs surface that contain guides
        jntRows     = (int) Number of rows of skin joints
        jntColumns  = (int) Number of columns of skin joints in each row
        ikSplineNum = (int) If > 0, create a ikSpline on dorito surface with ikSplineNum of joints
        lra         = (bol) True == display Local Rotation Axis
        '''


        ctlGde = []
        # Check for rows
        if cmds.listRelatives(srfName, c=1, type='transform') != None:
            for row in cmds.listRelatives(srfName, c=1, type='transform'):
                if row.startswith('row'):
                    if cmds.listRelatives(row, c=1, type='transform') != None:
                        # See if children are guides
                        self.gdeRows[row] = [gde for gde in cmds.listRelatives(row, c=1, type='transform') if gde.endswith('_ctlGde')]
                        # [ctlGde.append(gde) for gde in cmds.listRelatives(i, c=1, type='transform') if gde.endswith('_ctlGde')]

            if self.gdeRows == {}:
                raise IndexError('No control guides found on selection')


            self.dorSrf  = self.strapRigDorito(srfName, jntRows=jntRows, jntColumns=jntColumns, skipLast=skipLast, ikSpline=ikSpline, ikSplineNum=ikSplineNum, ctlShape=ctlShape, ctlSize=ctlSize, 
                           ctlColor=ctlColor, ctlSuffix=ctlSuffix, jntSuffix=jntSuffix, margin=margin, makeFK=makeFK, lra=lra) # return srfDor[0], ctls, or 'blank', ctls
        # simpleSys
        return self.dorSrf

        
    # ------------------------------------------------------------------------------------------
    def snap(self, source, target):
        """Move one object to another.
        Args:
            source (str): The name of the maya object we want to move.
            target (str): The name of the maya object we want to move onto.
        """
        position = cmds.xform(target, worldSpace=True, matrix=True, query=True)
        cmds.xform(source, worldSpace=True, matrix=position)

    def strapRigLayout(self, srfName, rows, columns, uv='u', objType='locator', suffix='ctlGde', skipLast=0, constrain=1):
        '''
        Places objects on nurbs surface to be used for control positions for strapRigDorito()

        srfName  = (str) Name of surface to place locators on
        columns  = (int) How many objects to create
        uv       = (str) 'u'(0) or 'v'(1) direction along nurbs surface
        skipLast = (bol) A nurbs surface can be in the shape of a cylinder, but still not be closed.
                         SkipLast will remove the last row so there are no overlapping ctls.
        '''
        
        if cmds.objExists(srfName):
            if cmds.objectType(omu.getDagPath(srfName, shape=True))!='nurbsSurface':
                raise TypeError('Specified surface is not a nurbs surface')
        else:
            raise NameError('Specified surface does not exist in the scene')

        cmds.select(None)
        ctlRows = {}

        # Create row curves
        if rows == 1: # One row will be in the center of the srf.
            rowCrvs = [srf.crvAlongSrf(srfName, uv)]
        else:
            if skipLast == True:
                rows = rows+1
                rowCrvs = srf.crvAlongSrfMulti(srfName, rows, uv)
                cmds.delete(rowCrvs[-1])
                rowCrvs.pop()
            else:
                rowCrvs = srf.crvAlongSrfMulti(srfName, rows, uv)

        # Create guide locators
        for i, curve in enumerate(rowCrvs):
            rowTra = cmds.createNode('transform', n='row'+str(i)+'_'+srfName)
            guides = crv.createEvenAlongCrv(objType, 'row'+str(i)+'_'+srfName, columns, curve, chain=0, keepCrv=0, suffix=suffix)
            [cmds.parent(g, rowTra) for g in guides]
            ctlRows['row'+str(i)] = guides

            if constrain==1:
                [srf.constToSrfMatrix(g, srfName) for g in guides]

            cmds.parent(rowTra, srfName)


        return ctlRows

    def strapRigDorito(self, srfName, jntRows, jntColumns, skipLast, ikSpline, ikSplineNum, ctlShape, ctlSize, ctlColor, ctlSuffix, jntSuffix, margin, makeFK, lra, uv='u'):
        '''
        Creates rdCtls.
        Creates the secondary nurbs surface for strapRigLayout()

        srfName  = (str) Name of surface to duplicate
        uv       = (str) 'u'(0) or 'v'(1) direction along nurbs surface
        ctlShape = rdCtl shape
        ctlSize  = rdCtl size
        '''

        sysName  = srfName.split('_')[0]

        if not cmds.objExists(srfName+'_ctls'):
            ctlGrp = cmds.createNode('transform', n=srfName+'_ctls', ss=True)
        else:
            ctlGrp = srfName+'_ctls'

        allCtls   = []
        allCtlJts = []
        splineCtlDict = OrderedDict()
        srfShp    = omu.getDagPath(srfName, shape=True)

        for rowName, gdeList in self.gdeRows.items():
            ctlJts = []
            ctls   = []
            for gde in gdeList:
            # Hide root locators
                cmds.setAttr(gde+'.overrideEnabled', 1)
                cmds.setAttr(gde+'.overrideDisplayType', 2) # Reference
                locShp = omu.getDagPath(gde, shape=True)
                for axis in ['X', 'Y', 'Z']:
                    cmds.setAttr(locShp+'.localScale'+axis, 0)

                # Create ctrls
                gdeNum = gde.split('_')[-2]
                ctl = rdCtl.Control(rowName+'_'+gdeNum, shape=ctlShape, size=ctlSize, color='yellow', 
                                    ctlSuffix=ctlSuffix, jntSuffix=jntSuffix, match=gde, parent=gde, jt=True)
                ctls.append(ctl)
                ctlJts.append(ctl.jt)

                allCtls.append(ctl)
                allCtlJts.append(ctl.jt)

                [rigu.rdCtlSideColor(ctl, priority=ctlColor, margin=margin) for ctl in ctls] # Set color based on ws

                # Rename guide locators to ctlRef
                cmds.rename(gde, gde.replace('_ctlGde', '_ctlRef'))

            cmds.parent(rowName, ctlGrp)
            cmds.rename(rowName, rowName+'_ctls')
            # Hide rdCtl joints, and set radius
            [cmds.setAttr(jnt+'.visibility', 0) for jnt in ctlJts]
            [cmds.setAttr(jnt+'.radius', 0.1) for jnt in ctlJts]

            # Add rdCtl attr tag, used in mGear reconnect vis attrs
            [cmds.addAttr(ctl.topCtl, ci=True, at='bool', sn='rdCtl', min=0, max=1, dv=1) for ctl in ctls]
            [cmds.setAttr(ctl.topCtl+'.rdCtl', l=True) for ctl in ctls]

            if makeFK==1:
                self.makeFK(ctls)

            splineCtlDict[rowName] = ctls # Need to add attr for ikSpline on rd ctls.

        # If more then 0 joint row specified, or IK Spline, create dorito surface
        if jntRows > 0 or ikSpline == True:
            # Duplicate base nurbs
            srfDor = cmds.nurbsPlane(p=(0, 0, 0), ax=(0, 1, 0), w=1, lr=1, d=3, u=1, v=1, ch=1, n=srfName+'_dorito')
            cmds.delete(srfDor[1])
            cmds.connectAttr(srfName+'.worldSpace[0]', srfDor[0]+'.create')
            cmds.refresh() # Refresh before disconnect
            cmds.disconnectAttr(srfName+'.worldSpace[0]', srfDor[0]+'.create')
            dorShp = omu.getDagPath(srfDor[0], shape=True)

            # Match point position
            matchPnt = cmds.createNode('transformGeometry', ss=True)
            cmds.connectAttr(srfName+'.worldMatrix[0]', matchPnt+'.transform')
            cmds.connectAttr(srfShp+'.worldSpace[0]', matchPnt+'.inputGeometry')
            cmds.connectAttr(matchPnt+'.outputGeometry', dorShp+'.create')

            # SkinCluster
            sknCls = cmds.skinCluster(allCtlJts, srfDor[0], mi=2, bm=0, sm=0, dr=4, wd=0, tsb=1, n=srfName+'_doritoSkn')[0]

            # Drive static kine state
            dorLst = allCtlJts
            dorLst.append(srfDor[0])
            rigu.rdCtlPreBindMat(dorLst, jntSuffix=jntSuffix, bfrSuffix='ctlRef')
            cmds.parent(srfDor[0], ctlGrp)
            
        cmds.parent(srfName, ctlGrp)

        # Create dorito jnt grid
        if jntRows > 0:
            dorJts = self.strapRigGrid(srfDor[0], jntSuffix, jntRows, jntColumns, skipLast=skipLast, lra=lra)
        else:
            dorJts = None

        # Create IK Splines (one per row of ctls)
        # IK Curves          
        if ikSpline == True:
            splineRows = len(splineCtlDict)
            # Create row curves
            if splineRows == 1: # One row will be in the center of the srf.
                splCurves = [srf.crvAlongSrf(srfDor[0], uv)]
            else:
                if skipLast == True:
                    splineRows = splineRows+1
                    splCurves = srf.crvAlongSrfMulti(srfDor[0], splineRows, uv)
                    cmds.delete(splCurves[-1])
                    splCurves.pop()
                else:
                    splCurves = srf.crvAlongSrfMulti(srfDor[0], splineRows, uv)

            # Parent the curves
            if not cmds.objExists(srfName+'_ikSpline'):
                splGrp = cmds.createNode('transform', n=srfName+'_ikSpline', ss=True)
            else:
                splGrp = srfName+'_ikSpline'

            cmds.parent(splGrp, ctlGrp)
            [cmds.parent(c, splGrp) for c in splCurves]

            # IK Chain
            for row, ctls in splineCtlDict.items():
                curve = None
                curve = splCurves[list(splineCtlDict.keys()).index(row)] # get spline curve by key index
                chain = self.ikSpline(ctls, curve, ikSplineNum, jntSuffix)
                cmds.parent(chain[0][0], splGrp) # ik spline root joint
                cmds.parent(chain[1], splGrp)

        cmds.select(None)

        if jntRows > 0 or ikSpline == True:
            return srfDor[0], allCtls, ctlGrp, dorJts
        else:
            return 'blank', allCtls, ctlGrp

    def strapRigGrid(self, srfName, jntSuffix, jntRows=2, jntColumns=2, uv='u', constraint='matrix', skipLast=False, lra=True):
        '''
        Creates joints rows and columns on nurbs surface. Used for bind

        srfName    = (str) Name of nurbs surface
        jntRows    = (int) Number of joint rows
        jntColumns = (int) Number of joints in each row
        uv         = (str) 'u'(0) or 'v'(1) direction along nurbs surface
        constraint = (str) 'follicle' or 'matrix'
        keepCrv    = (bol) Keep curve used in createEvenAlongCrv?
        skipLast   = (bol) A nurbs surface can be in the shape of a cylinder, but still not be closed.
                           SkipLast will remove the last row so there are no overlapping joints.
        lra        = (bol) If joint, turn on local rotation axis display
       
        '''

        nameSplit = srfName.split('_')
        sysName = '_'.join(nameSplit[:3])

        allJts = []
        jntDict = {}
        if jntRows==1:
            srfCrv = srf.crvAlongSrf(srfName, uv)
            jnts = crv.createEvenAlongCrv('joint', sysName+'_dor', jntColumns, srfCrv, lra=lra, suffix=jntSuffix, radius=0.5)
            jntDict[srfCrv] = jnts

        else:
            if skipLast:
                jntRows = jntRows+1
                srfCrv  = srf.crvAlongSrfMulti(srfName, jntRows, uv)
                cmds.delete(srfCrv[-1])
                srfCrv.pop()
            else:
                srfCrv  = srf.crvAlongSrfMulti(srfName, jntRows, uv)

            for i, curve in enumerate(srfCrv):
                jnts = crv.createEvenAlongCrv('joint', sysName+'_dor', jntColumns, curve, lra=lra, suffix=jntSuffix, radius=0.5)
                jntDict[curve] = jnts
                allJts.append(jnts)

        for k, v in jntDict.items():
            [srf.constToSrfMatrix(obj, srfName) for obj in v]
            cmds.parent(v, srfName)

        return allJts

    def ikSpline(self, rdCtls, curve, ikSplineNum, jntSuffix):
        ikSpne = rigu.ikSplineOnCrv(curve, ikNum=ikSplineNum, suffix=jntSuffix)
        spcJts = crv.createEvenAlongCrv('joint', curve, ikSplineNum, curve, keepCrv=1, suffix='spacer', lra=False)
        mpthNd = crv.consToCrvParametric(spcJts, curve, upType=4)
        rigu.ikSplineCrvStretch(curve+'_spacer', mpthNd, ikSpne[0], spcJts, rdCtls[0].topCtl)
        # Hide spc joints, ikHandle
        [cmds.setAttr(jnt+'.drawStyle', 2) for jnt in spcJts]
        
        cmds.parent(spcJts, curve)

        # Advanced twist controls
        ikHdl = ikSpne[1][0]
        cmds.setAttr(ikHdl+'.v', 0)
        startCtl, endCtl = rdCtls[0], rdCtls[-1] # first and last rdCtl for spline twist.
        cmds.setAttr(ikHdl+'.dTwistControlEnable', 1)
        cmds.setAttr(ikHdl+'.dWorldUpType', 4)
        cmds.connectAttr(endCtl.topCtl+'.wm', ikHdl+'.dWorldUpMatrixEnd')
        cmds.connectAttr(startCtl.topCtl+'.wm', ikHdl+'.dWorldUpMatrix')


        return [ikSpne[0], ikHdl]

    def makeFK(self, ctls):
        # FK/IK switch
        cmds.addAttr(ctls[0].topCtl, at='bool', k=True, ci=True, sn='FK', dv=1)

        cnsLst = []
        for i, ctl in enumerate(ctls):
            if i != len(ctls)-1: # If not the last ctl
                # Create offset transform
                offTra = cmds.createNode('transform', n=ctl.name.replace('_ctl_', '_ctlOff_'), p=ctl.topCtl, ss=True)
                # Create hierarchy root
                hirRut = cmds.createNode('transform', n=ctl.name.replace('_ctl_', '_hierarchy_'), p=ctl.topCtl, ss=True)
                # Create hierarchyOffset
                hirOff = cmds.createNode('transform', n=ctl.name.replace('_ctl_', '_hierarchyOffset_'), p=ctl.topCtl, ss=True)

                # Next locator
                curLoc = cmds.listRelatives(ctls[i].grp, parent=1)[0]
                nxtLoc = cmds.listRelatives(ctls[i+1].grp, parent=1)[0]
                nxtCtl = cmds.xform(ctls[i+1].topCtl, q=1, ws=1, matrix=True)

                # Move hierarchy root to next ctl pos
                cmds.xform(hirRut, ws=1, matrix=nxtCtl)
                cmds.parent(hirRut, curLoc)
                cmds.makeIdentity(hirRut, apply=True, t=1, r=1, s=1)
                
                # Move hierarchyOffset to pos of next ctl pos
                cmds.xform(hirOff, ws=1, matrix=nxtCtl)
                cmds.parent(hirOff, hirRut)
                cmds.makeIdentity(hirOff, apply=True, t=1, r=1, s=1)

                # Move offset transform to pos of next ctl in chain
                cmds.xform(offTra, ws=1, matrix=nxtCtl)
                cmds.makeIdentity(offTra, apply=True, t=1, r=1, s=1)

                t=['x','y','z']
                r=['x','y','z']
                s=['x','y','z']

                # hirRut drives offTra
                [cmds.connectAttr(hirRut+'.t'+axis, offTra+'.t'+axis) for axis in t]
                [cmds.connectAttr(hirRut+'.r'+axis, offTra+'.r'+axis) for axis in r]
                [cmds.connectAttr(hirRut+'.s'+axis, offTra+'.s'+axis) for axis in s]

                # hirOff drives next bfr in chain
                [cmds.connectAttr(hirOff+'.t'+axis, ctls[i+1].grp+'.t'+axis) for axis in t]
                [cmds.connectAttr(hirOff+'.r'+axis, ctls[i+1].grp+'.r'+axis) for axis in r]
                [cmds.connectAttr(hirOff+'.s'+axis, ctls[i+1].grp+'.s'+axis) for axis in s]

                # Constrain hierarchy offset offset transform
                cnsLst.append(cmds.parentConstraint(offTra, hirOff, mo=True, n=offTra+'_parentConstraint'))
                cnsLst.append(cmds.scaleConstraint (offTra, hirOff, mo=True, n=offTra+'_scaleConstraint'))

                # Constrain hierarchy root to next locator
                cnsLst.append(cmds.pointConstraint (nxtLoc, hirRut, mo=True, n=hirRut+'_pointConstraint'))
                cnsLst.append(cmds.parentConstraint(nxtLoc, hirRut, mo=True, st=['x', 'y', 'z'], n=hirRut+'_parentConstraint'))

        # Connect FK attr on first ctl to drive FK constraints. 0 returns to IK behavior
        for const in cnsLst:
            cmds.connectAttr(ctls[0].topCtl+'.FK', const[0]+'.'+cmds.listAttr(const)[-1])