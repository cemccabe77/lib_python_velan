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
a.build_guide('wrist_Lt_01', guide_count=6)

# One or the other
a.buildIkFkRig()
a.buildFkRig()
'''

class IkFk(object):
    def __init__(self):
        self.guide_curve = ''
        self.guide_pos = []
        self.ctl_group = ''

    
    def build_guide(self, curve_name, guide_count):
        '''
        Creates FK guides along a curve.
        User can define guide position and rotation
        before building either FK, or IK/FK chain system

        curve_name  = (str) Name of curve to create guide from
        guide_count = (int) Number of guides to create on curve
        '''

        # Could be sending a selection as curve_name. Convert selection to short name.
        if '|' in curve_name:
            curve_name = curve_name.split('|')[-1]

        # Check for existing guide curve
        if not self.guide_curve:
            self.guide_curve = curve_name

        name_split = curve_name.split('_')
        name = '_'.join(name_split[:3])
        guide_pos = crv.create_evenly_along_curve(object_type='joint', object_name=name, count=guide_count, 
                            curve_name=curve_name, chain=1, keep_curve=1, suffix='ctl_guide')
        
        # Building as chain, need to orient end joint in ctlPos chain
        rot = cmds.xform(guide_pos[-2], q=True, ws=True, ro=True)
        cmds.xform(guide_pos[-1], r=True, ro=rot)

        # Unparent from chain so user can orient guides
        [cmds.parent(ctl, curve_name) for ctl in guide_pos]

        # Define start of curve with yellow joint color
        # Make sure guide curve is not hidden (if created from other hidden crv)
        cmds.setAttr(f'{guide_pos[0]}.overrideEnabled', 1)
        cmds.setAttr(f'{guide_pos[0]}.overrideColor', 17)
        cmds.setAttr(f'{curve_name}.v', 1)
        cmds.select(None)

        self.guide_curve = curve_name
        self.guide_pos = guide_pos+guide_pos

        return curve_name, guide_pos

    def build_ik_fk_rig(self, ctl_shape='circle', ctl_size=1.5, ctl_color=2, ctl_suffix='', joint_suffix='', margin=1.0):
        '''
        Create rig from build_guide() output, or use current selection.
        '''       

        # Check for curve surface guide selection
        if cmds.ls(sl=1):
            ctl_guide = []
            # Make sure its curve surface
            if cmds.objectType(omu.get_dag_path(cmds.ls(sl=1)[0], shape=1))=='nurbsCurve':
                # Check for children
                if cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                    # See if children are guides
                    for i in cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                        # Add to gdeList
                        if i.endswith('_ctl_guide'):
                            ctl_guide.append(i)

                if ctl_guide:
                    ctl_guide.sort()
                    self.guide_pos = ctl_guide
                    self.guide_curve = cmds.ls(sl=1)[0]
                    self.guides_to_ik_fk(curve_name=self.guide_curve, guides=self.guide_pos, ctl_shape=ctl_shape, 
                        ctl_size=ctl_size, ctl_color=ctl_color, margin=margin, ctl_suffix=ctl_suffix, 
                        joint_suffix=joint_suffix)
        
        elif self.guide_curve and self.guide_pos:
            self.guides_to_ik_fk(curve_name=self.guide_curve, guides=self.guide_pos, ctl_shape=ctl_shape, 
                ctl_size=ctl_size, ctl_color=ctl_color, margin=margin, ctl_suffix=ctl_suffix, 
                joint_suffix=joint_suffix)

        else:
            raise TypeError('No guide curve selected, or no guide curve in scene')

    def build_fk_rig(self, ctl_shape='circle', ctl_size=1.5, ctl_color=2, ctl_suffix='', joint_suffix='', margin=1.0):
        '''
        Create rig from build_guide() output, or use current selection.
        '''        

        # Check for curve surface guide selection
        if cmds.ls(sl=1):
            ctl_guide = []
            # Make sure its curve surface
            if cmds.objectType(omu.get_dag_path(cmds.ls(sl=1)[0], shape=1))=='nurbsCurve':
                # Check for children
                if cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                    # See if children are guides
                    for i in cmds.listRelatives(cmds.ls(sl=1)[0], c=1, type='transform'):
                        # Add to gdeList
                        if i.endswith('_ctl_guide'):
                            ctl_guide.append(i)

                if ctl_guide:
                    ctl_guide.sort()
                    self.guide_pos = ctl_guide
                    self.guide_curve = cmds.ls(sl=1)[0]
                    self.guides_to_fk(self.guide_curve, self.guide_pos, ctl_shape=ctl_shape, ctl_size=ctl_size, ctl_color=ctl_color, margin=margin,
                                    ctl_suffix=ctl_suffix, joint_suffix=joint_suffix)

        elif self.guide_curve and self.guide_pos:
            self.guides_to_fk(self.guide_curve, self.guide_pos, ctl_shape=ctl_shape, ctl_size=ctl_size, ctl_color=ctl_color, margin=margin,
                            ctl_suffix=ctl_suffix, joint_suffix=joint_suffix)
            
        else:
            raise TypeError('No guide curve selected, or no guide curve in scene')

    # ------------------------------------------------------------------------------------------
    def snap(self, source, target):
        '''
        Move one object to another.
        '''

        position = cmds.xform(target, worldSpace=True, matrix=True, query=True)
        cmds.xform(source, worldSpace=True, matrix=position)
    
    def curve_to_fk_guides(self, curve_name, guide_count):
        '''
        Creates FK guides along a curve.
        User can define guide position and rotation
        before building either FK, or IK/FK chain system

        curve_name = (str) Name of curve to create guide from
        guide_count = (int) Number of guides to create on curve
        '''

        # Could be sending a selection as curve_name. Convert selection to short name.
        if '|' in curve_name:
            curve_name = curve_name.split('|')[-1]

        # Check for existing guide curve
        if not self.guide_curve:
            self.guide_curve = curve_name

        name_split = curve_name.split('_')
        name = '_'.join(name_split[:3])
        guide_pos = crv.create_evenly_along_curve(object_type='joint', object_name=name, count=guide_count, 
                            curve_name=curve_name, chain=1, keep_curve=1, suffix='ctl_guide')
        
        # Building as chain, need to orient end joint in ctlPos chain
        rot = cmds.xform(guide_pos[-2], q=True, ws=True, ro=True)
        cmds.xform(guide_pos[-1], r=True, ro=rot)

        # Unparent from chain so user can orient guides
        [cmds.parent(ctl, curve_name) for ctl in guide_pos]

        # Define start of curve with yellow joint color
        # Make sure guide curve is not hidden (if created from other hidden crv)
        cmds.setAttr(f'{guide_pos[0]}.overrideEnabled', 1)
        cmds.setAttr(f'{guide_pos[0]}.overrideColor', 17)
        cmds.setAttr(f'{curve_name}.v', 1)
        cmds.select(None)

        return curve_name, guide_pos

    def guides_to_ik_fk(self, curve_name, guides, ctl_shape='circle', ctl_size=1.5, ctl_color=2, margin=1.0, ctl_suffix='', joint_suffix=''):
        '''
        Creates IK/FK chain system from curve with FKGuide children.(curve_to_fk_guides)

        curve_name   = (str) Name of curve that has FK Guides as children
        ctl_shape  = (str) rdCtl shape
        ctl_size   = (float) General rdCtl sizes
        ctl_suffix = (str) Suffix for rdCtl controllers
        joint_suffix = (str) Suffix for rdCtl joints
        '''

        ctl_group = curve_name+'_ctls'
        self.ctl_group = ctl_group

        if cmds.objExists(ctl_group):
            if cmds.listRelatives(ctl_group, c=True, type='transform'):
                [cmds.delete(item) for item in cmds.listRelatives(ctl_group, c=True, type='transform')]
        else:
            ctl_group = cmds.createNode('transform', n=ctl_group, ss=True)

        # Guides to ctls
        fk_ctls = self.guides_to_rdctl(guides=guides, ctl_shape=ctl_shape, ctl_size=ctl_size, ctl_color=ctl_color, 
                                  ctl_suffix=ctl_suffix, joint_suffix=joint_suffix, margin=margin)

        name_split = curve_name.split('_')
        name = '_'.join(name_split[:3])+'_'

        if 'gdeCrv' in name:
            name = self.guide_curve.replace('_gdeCrv', '_')

        # Root ctl
        ctl_parent = rdCtl.Control(f'{name}root', match=fk_ctls[0].jt, parent=ctl_group,
                shape='cube', color='lightYellow', jt=False, size=ctl_size)
        
        # IK Chain
        ikJts = self.fk_to_ik(ctl_name=name, fk_ctls=fk_ctls)
        
        # Orient root grp
        self.snap(fk_ctls[0].topCtl, ctl_parent.grp)
        
        # Parent IK jts
        cmds.parent(ikJts[0], ctl_parent.topCtl)
        
        # IK Handle
        ikHdl = cmds.ikHandle(sj=ikJts[0], ee=ikJts[1], p=2)
        cmds.parent(ikHdl[0], ctl_parent.grp)
        ik_ctl = rdCtl.Control(name+'ik', match=ikHdl[0], parent=ctl_parent.topCtl,
                shape='diamond', color='lightYellow', jt=False, size=ctl_size*1.5)
        
        # Orient IK Tip Ctl
        rot = cmds.xform(ctl_parent.topCtl, q=True, ws=True, ro=True)
        cmds.xform(ik_ctl.grp, r=True, ro=rot)
        
        # Constrain IK Handle to IK Ctl
        cmds.parent(ikHdl[0], ik_ctl.topCtl)
        cmds.setAttr(f'{ikHdl[0]}.visibility', 0)
        
        # Parent FK Chain to ikJnt
        cmds.parent(fk_ctls[0].grp, ikJts[0])
        
        # Unparent ikTip Ctl to ctl_parent grp
        cmds.parent(ik_ctl.grp, ctl_parent.grp)
        
        # Set ctl_parent as IK Pole Vector
        cmds.poleVectorConstraint(ctl_parent.topCtl, ikHdl[0])
        
        # Constrain IK Tip to look at root
        cmds.aimConstraint(ctl_parent.topCtl, ik_ctl.topCtl, weight=1, upVector=(0, 1, 0), mo=0, worldUpType="vector", 
                            aimVector=(-1, 0, 0), worldUpVector=(0, 1, 0))
        # Hide guide crv
        cmds.hide(curve_name)
        cmds.select(None)

    def guides_to_fk(self, curve_name, guides, ctl_shape='circle', ctl_size=1.5, ctl_color=2, ctl_suffix='', 
                    joint_suffix='', margin=1.0):
        '''
        Creates FK chain without IK parent, from fkGuides
        
        curve_name  = (str) Name of curve that has FK Guides as children
        ctl_shape = (str) rdCtl shape
        ctl_size  = (float) General rdCtl sizes    
        '''

        ctl_group = curve_name+'_ctls'
        self.ctl_group = ctl_group

        if cmds.objExists(ctl_group):
            if cmds.listRelatives(ctl_group, c=True, type='transform'):
                [cmds.delete(item) for item in cmds.listRelatives(ctl_group, c=True, type='transform')]
        else:
            ctl_group = cmds.createNode('transform', n=ctl_group, ss=True)

        if cmds.objExists(curve_name):
            if cmds.objectType(omu.get_dag_path(curve_name, shape=True))!='nurbsCurve':
                raise TypeError('Specified object is not a nurbs Curve')
        else:
            raise NameError('Specifired Curve does not exist in the scene')

        name_split = curve_name.split('_')
        name   = '_'.join(name_split[:3])+'_'
        parent    = cmds.listRelatives(curve_name, p=True)

        fk_ctls = self.guides_to_rdctl(guides=guides, ctl_shape=ctl_shape, ctl_size=ctl_size, ctl_color=ctl_color, 
                                      ctl_suffix=ctl_suffix, joint_suffix=joint_suffix, margin=margin)
        # Root ctl
        ctl_parent = rdCtl.Control(name+'root', match=fk_ctls[0].jt, parent=ctl_group,
                shape='cube', color='lightYellow', jt=False, size=ctl_size)

        # Orient root grp
        self.snap(fk_ctls[0].topCtl, ctl_parent.grp)
        
        # Parent FK Chain to ikJnt
        cmds.parent(fk_ctls[0].grp, ctl_parent.topCtl)
        
        # Parent root to guide parent if exists
        if parent:
            cmds.parent(ctl_parent.grp, parent[0])
        
        # Hide guide crv
        cmds.hide(curve_name)

        return ctl_parent.topCtl

    def guides_to_rdctl(self, guides, ctl_shape='circle', ctl_size=1.5, ctl_color=2, ctl_suffix='', joint_suffix='', margin=1.0):
        '''
        Converts FK guides into rdCtl fk chain. Sets side color
        
        guides    = ([]) list of FK guides
        ctl_shape = (str) rdCtl shape
        ctl_size  = (float) rdCtl size
        '''

        name_split = guides[0].split('_')
        name = '_'.join(name_split[:3])

        fk_ctls = []
        fk_joints = []
        for i, joint in enumerate(guides):
            ctlParent = fk_ctls[-1].topCtl if fk_ctls else None
            ctl = rdCtl.Control(f'{name}_fk{i}', match=joint, parent=ctlParent,
                    shape=ctl_shape, color='lightYellow', jt=True, size=ctl_size, ctlSuffix=ctl_suffix, 
                    jntSuffix=joint_suffix)
            fk_ctls.append(ctl)
            fk_joints.append(ctl.jt)

        [rigU.rdctl_side_color(control=ctl, priority=ctl_color, margin=margin) for ctl in fk_ctls] # Set color based on ws
        [cmds.setAttr(joint+'.v', 0) for joint in fk_joints]

        cmds.select(None)

        return fk_ctls

    def fk_to_ik(self, ctl_name, fk_ctls):
        '''
        Creates singe chain IK to parent FK chain to

        ctl_name = (str) rdCtl prefix
        fk_ctls  = ([])  list of fk_ctls to use as start and end of IK chain
                        Comes from guides_to_rdctl
        '''

        joints =[]
        joints.append(cmds.joint(n=f'{ctl_name}ikRoot', p=cmds.xform(fk_ctls[0].jt, q=True, ws=True, t=True)))
        joints.append(cmds.joint(n=f'{ctl_name}ikTip', p=cmds.xform(fk_ctls[-1].jt, q=True, ws=True, t=True)))

        for joint in joints:
            cmds.joint(joint, edit=True, zso=True, sao='zup', oj='xyz')
            cmds.setAttr(joint+'.drawStyle', 2)

        return joints