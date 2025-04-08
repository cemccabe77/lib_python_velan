import maya.cmds as cmds
from . import rdCtl as rdCtl
from lib_python_velan.mayaRigUtils.scripts import omUtil as omu
from lib_python_velan.mayaRigUtils.scripts import rigUtils as rigu
from lib_python_velan.mayaRigUtils.scripts import curves as crv
from lib_python_velan.mayaRigUtils.scripts import skincluster as skn
from lib_python_velan.mayaRigUtils.scripts import surfaces as srf


'''
Builds a strap rig with driver surface, and driven dorito surface.
Ctls in driver surface will drive doritio surface. Which will in turn
drive rig mesh

####################################################
Usage:

import strap

a=strap.Strap()
new_surface = srf.nurbsSrfPrep(n='test_surface', create=True)
a.build_guide(new_surface, rows=1, columns=5, skip_last=0)
a.build_rig(joint_rows=5, joint_columns=9)
####################################################
'''

class Strap(object):
    def __init__(self):
        self.surface_name = ''
        self.dorito_surface = ''
        self.rows = 0
        self.columns = 0
        self.control_group = None
        self.guide_rows = {}

    
    def build_guide(self, surface_name, rows, columns, object_type='locator', suffix='ctlGde'):
        '''
        surface_name  = (str) Nurbs surface to place ctl guides on
        rows          = (int) Number of guide rows to put on surface
        columns       = (int) Number of columns of guides in each row
        object_type   = Type of object to create in rows/columns (joint, locator)
        suffix        = (str) build_rig() looks for objects with suffix of ctlGde
        skip_last     = (bol) Skip last guide to prevent double guides on nurbs edges (closed surface)
        '''
        self.surface_name = surface_name
        self.rows = rows
        self.columns  = columns

        self.strap_rig_layout(self.surface_name, rows, columns, object_type=object_type, suffix=suffix)
        
        # Select nurbs surface so user can run build_rig()
        if cmds.objExists(surface_name):
            cmds.select(surface_name, r=True)

    def build_rig(self, surface_name, joint_rows, joint_columns, ctl_shape='circle',ctl_size=1.5, ctl_color=2, 
                ctl_suffix='', joint_suffix='', make_fk=0, ik_spline=False, ik_spline_count=0, margin=1.0, lra=True):
        '''
        Create rig from build_guide() output, or use current selection.
        Check for nurbs surface guide selection

        surface_name    = (str) nurbs surface that contain guides
        joint_rows      = (int) Number of rows of skin joints
        joint_columns   = (int) Number of columns of skin joints in each row
        skip_last       = (bol) Skip last joint to prevent double joints on nurbs edges (closed surface)
        ik_spline_count = (int) If > 0, create a ik_spline on dorito surface with ik_spline_count of joints
        ik_spline       = (bol) Dorito joints will be built as IK Spline
        lra             = (bol) Display Local Rotation Axis on created joints
        '''


        ctlGde = []
        # Check for rows
        if cmds.listRelatives(surface_name, c=True, type='transform') != None:
            for row in cmds.listRelatives(surface_name, c=True, type='transform'):
                if row.startswith('row'):
                    if cmds.listRelatives(row, c=True, type='transform') != None:
                        # If children are guides
                        self.guide_rows[row] = [gde for gde in cmds.listRelatives(row, c=1, type='transform') if gde.endswith('_ctlGde')]

        if self.guide_rows != {}:
            self.dorito_surface  = self.strap_rig_dorito(surface_name, joint_rows=joint_rows, joint_columns=joint_columns, 
                                                ik_spline=ik_spline, ik_spline_count=ik_spline_count, 
                                                ctl_shape=ctl_shape, ctl_size=ctl_size, ctl_color=ctl_color, 
                                                ctl_suffix=ctl_suffix, joint_suffix=joint_suffix, margin=margin, 
                                                make_fk=make_fk, lra=lra) # returns srfDor[0], ctls
        else:
            raise IndexError('No control guides found on selection')

        return self.dorito_surface


    # ------------------------------------------------------------------------------------------

    def strap_rig_layout(self, surface_name, rows, columns, uv='u', object_type='locator', suffix='ctlGde'):
        '''
        Places objects on nurbs surface to be used for control positions for strapRigDorito()

        surface_name  = (str) Name of surface to place locators on
        rows          = (int) How many rows of object to create
        columns       = (int) How many columns of objects to create in each row
        uv            = (str) 'u'(0) or 'v'(1) direction along nurbs surface
        skip_last     = (bol) A nurbs surface can be in the shape of a cylinder, but still not be closed.
                         skip_last will remove the last row so there are no overlapping ctls.
        '''
        
        if cmds.objExists(surface_name):
            if cmds.objectType(omu.get_dag_path(surface_name, shape=True))!='nurbsSurface':
                raise TypeError('Specified surface is not a nurbs surface')
        else:
            raise NameError(f'Specified surface does not exist in the scene >> {surface_name}')


        cmds.select(None)
        
        ctl_rows = {}
        # Create row curves
        if rows == 1:
            row_curves = [srf.curve_along_surface(surface_name=surface_name, uv=uv)]
        else:
            row_curves = srf.curve_along_surface_multi(surface_name=surface_name, rows=rows, uv=uv)

        # Create guide locators
        for i, curve in enumerate(row_curves):
            transforms = cmds.createNode('transform', n=f'row_{str(i)}_{surface_name}')
            guides = crv.create_evenly_along_curve(object_type=object_type, object_name=f'row_{str(i)}_{surface_name}', 
                                count=columns, curve_name=curve, keep_curve=0, suffix=suffix)
            
            [cmds.parent(guide, transforms) for guide in guides]
            
            ctl_rows[f'row_{str(i)}'] = guides

            [srf.constrain_to_surface_matrix(object_name=guide, surface_name=surface_name) for guide in guides]

            cmds.parent(transforms, surface_name)


        return ctl_rows

    def strap_rig_dorito(self, surface_name, joint_rows, joint_columns, ik_spline, ik_spline_count, ctl_shape, 
                        ctl_size, ctl_color, ctl_suffix, joint_suffix, margin, make_fk, lra, uv='u'):
        '''
        Creates rdCtls.
        Creates the secondary nurbs surface for strap_rig_layout()

        surface_name  = (str) Name of surface to duplicate
        uv       = (str) 'u'(0) or 'v'(1) direction along nurbs surface
        ctl_shape = rdCtl shape
        ctl_size  = rdCtl size
        '''

        name  = surface_name.split('_')[0]

        if cmds.objExists(f'{surface_name}_ctls'):
            control_group = f'{surface_name}_ctls'
        else:
            control_group = cmds.createNode('transform', n=f'{surface_name}_ctls', ss=True)

        all_controls    = []
        all_ctl_joints  = []
        spline_ctl_dict = {}
        surface_shape   = omu.get_dag_path(surface_name, shape=True)

        # Create base surface controls (rdCtl)
        for row_name, guide_list in self.guide_rows.items():
            ctl_joints = []
            controls   = []
            for guide in guide_list:
                # Hide root locators
                cmds.setAttr(f'{guide}.overrideEnabled', 1)
                cmds.setAttr(f'{guide}.overrideDisplayType', 2) # Reference
                locator_shape = omu.get_dag_path(guide, shape=True)
                for axis in ['X', 'Y', 'Z']:
                    cmds.setAttr(f'{locator_shape}.localScale{axis}', 0)

                # Create controls
                guide_number = guide.split('_')[-2]
                ctl = rdCtl.Control(f'{row_name}_{guide_number}', shape=ctl_shape, size=ctl_size, color='yellow', 
                                ctlSuffix=ctl_suffix, jntSuffix=joint_suffix, match=guide, parent=guide, jt=True)
                
                controls.append(ctl)
                ctl_joints.append(ctl.jt)
                all_controls.append(ctl)
                all_ctl_joints.append(ctl.jt)  

                # Set color based on ws
                [rigu.rdctl_side_color(control=ctl, priority=ctl_color, margin=margin) for ctl in controls]

                # Rename guide locators to ctlRef for pre-bind matrix setup option
                cmds.rename(guide, guide.replace('_ctlGde', '_ctlRef'))

            cmds.parent(row_name, control_group)
            cmds.rename(row_name, f'{row_name}_ctls')
            # Hide rdCtl joints, and set radius
            [cmds.setAttr(jnt+'.visibility', 0) for jnt in ctl_joints]
            [cmds.setAttr(jnt+'.radius', 0.5) for jnt in ctl_joints]

            '''
            # Add rdCtl attr tag, used in mGear reconnect vis attrs
            [cmds.addAttr(ctl.topCtl, ci=True, at='bool', sn='rdCtl', min=0, max=1, dv=1) for ctl in controls]
            [cmds.setAttr(f'{ctl.topCtl}.rdCtl', l=True) for ctl in controls]
            '''

            if make_fk == True:
                self.make_fk(controls)

            spline_ctl_dict[row_name] = controls # Need to add attr for ik_spline on rd controls.

        # If more then 0 joint row specified, or IK Spline, create dorito surface
        if joint_rows > 0 or ik_spline == True:
            # Duplicate base nurbs
            dorito_surface = cmds.nurbsPlane(p=(0, 0, 0), ax=(0, 1, 0), w=1, lr=1, d=3, u=1, v=1, ch=1, 
                                            n=f'{surface_name}_dorito')
            cmds.delete(dorito_surface[1])
            cmds.connectAttr(f'{surface_name}.worldSpace[0]', f'{dorito_surface[0]}.create')
            cmds.refresh() # Refresh before disconnect
            cmds.disconnectAttr(f'{surface_name}.worldSpace[0]', f'{dorito_surface[0]}.create')
            dorito_shape = omu.get_dag_path(dorito_surface[0], shape=True)

            # Match point position
            match_point_node = cmds.createNode('transformGeometry', ss=True)
            cmds.connectAttr(f'{surface_name}.worldMatrix[0]', f'{match_point_node}.transform')
            cmds.connectAttr(f'{surface_shape}.worldSpace[0]', f'{match_point_node}.inputGeometry')
            cmds.connectAttr(f'{match_point_node}.outputGeometry', f'{dorito_shape}.create')

            cmds.skinCluster(all_ctl_joints, dorito_surface[0], mi=2, bm=0, sm=0, dr=4, wd=0, tsb=1, 
                            n=f'{surface_name}_dorito_skin')[0]  

            # Drive static kine state 
            dorito_list = all_ctl_joints
            dorito_list.append(dorito_surface[0])
            rigu.rdctl_prebind_matrix (dorito_list=dorito_list, joint_suffix=joint_suffix, buffer_suffix='ctlRef')
            cmds.parent(dorito_surface[0], control_group)
            
        cmds.parent(surface_name, control_group)

        # Create IK Splines (one per row of controls)
        # IK Curves          
        if ik_spline == True:
            spline_rows = len(spline_ctl_dict)
            # Create row curves
            if spline_rows == 1: # One row will be in the center of the srf.
                spline_curves = [srf.curve_along_surface(surface_name=dorito_surface[0], uv=uv)]
            else:
                spline_curves = srf.curve_along_surface_multi(surface_name=dorito_surface[0], rows=spline_rows, 
                                                                    uv=uv)

            # Parent the curves
            if cmds.objExists(f'{surface_name}_ik_spline'):
                spline_group = f'{surface_name}_ik_spline'
            else:
                spline_group = cmds.createNode('transform', n=f'{surface_name}_ik_spline', ss=True)

            cmds.parent(spline_group, control_group)
            [cmds.parent(curve, spline_group) for curve in spline_curves]

            # IK Chain
            for row, controls in spline_ctl_dict.items():
                curve = None
                curve = spline_curves[list(spline_ctl_dict.keys()).index(row)] # get spline curve by key index
                chain = self.ik_spline(rdCtls=controls, curve=curve, ik_spline_count=ik_spline_count, 
                                        joint_suffix=joint_suffix)
                cmds.parent(chain[0][0], spline_group) # ik spline root joint
                cmds.parent(chain[1], spline_group)

            dorito_joints=chain

        else:
            # Create dorito joint grid
            if joint_rows > 0:
                dorito_joints = self.strap_rig_grid(surface_name=dorito_surface[0], joint_suffix=joint_suffix, 
                                                joint_rows=joint_rows, joint_columns=joint_columns, lra=lra)
            else:
                dorito_joints = None

        cmds.select(None)

        if joint_rows > 0 or ik_spline == True:
            return dorito_surface[0], all_controls, control_group, dorito_joints
        else:
            return None, all_controls, control_group

    def strap_rig_grid(self, surface_name, joint_suffix, joint_rows=2, joint_columns=2, uv='u', constraint='matrix', 
                        lra=True):
        '''
        Creates joints rows and columns on nurbs surface.
        '''

        name_split = surface_name.split('_')
        name = '_'.join(name_split[:3])

        all_joints = []
        joint_dict = {}
        if joint_rows == 1:
            surface_curve = srf.curve_along_surface(surface_name=surface_name, uv=uv)
            joints = crv.create_evenly_along_curve(object_type='joint', object_name=f'{name}_dor', count=joint_columns, 
                                                   curve_name=surface_curve, lra=lra, suffix=joint_suffix, radius=0.5)
            joint_dict[surface_curve] = joints
        else:
            surface_curves = srf.curve_along_surface_multi(surface_name=surface_name, rows=joint_rows, uv=uv)
            for i, curve in enumerate(surface_curves):
                joints = crv.create_evenly_along_curve(object_type='joint', object_name=f'{name}_dor', 
                                count=joint_columns, curve_name=curve, lra=lra, suffix=joint_suffix, radius=0.5)
                joint_dict[curve] = joints
                all_joints.append(joints)

        for curve, joints in joint_dict.items():
            [srf.constrain_to_surface_matrix(object_name=joint, surface_name=surface_name) for joint in joints]
            cmds.parent(joints, surface_name)

        return all_joints

    def ik_spline(self, rdCtls, curve, ik_spline_count, joint_suffix):
        
        ik_spline = rigu.ik_spline_on_curve(curve_name=curve, count=ik_spline_count, suffix=joint_suffix)
        
        space_joints = crv.create_evenly_along_curve(object_type='joint', object_name=curve, count=ik_spline_count, 
                                                    curve_name=curve, keep_curve=1, suffix='spacer', lra=False)
        
        path_nodes = crv.constrain_to_curve_parametric(constrained=space_joints, curve_name=curve, up_type=4)
        
        rigu.ik_spline_curve_stretch(name=f'{curve}_spacer', motion_nodes=path_nodes, spline_joints=ik_spline[0], 
                                    attr_object=rdCtls[0].topCtl)
        
        # Hide space joints, ikHandle
        [cmds.setAttr(f'{joint}.drawStyle', 2) for joint in space_joints]
        cmds.parent(space_joints, curve)

        # Advanced twist controls
        ik_handle = ik_spline[1][0]
        cmds.setAttr(f'{ik_handle}.v', 0)
        start_ctl, end_ctl = rdCtls[0], rdCtls[-1] # first and last rdCtl for spline twist.
        cmds.setAttr(f'{ik_handle}.dTwistControlEnable', 1)
        cmds.setAttr(f'{ik_handle}.dWorldUpType', 4)
        cmds.connectAttr(end_ctl.topCtl+'.wm', f'{ik_handle}.dWorldUpMatrixEnd')
        cmds.connectAttr(start_ctl.topCtl+'.wm', f'{ik_handle}.dWorldUpMatrix')


        return [ik_spline[0], ik_handle]

    def make_fk(self, ctls):
        # FK/IK switch
        cmds.addAttr(ctls[0].topCtl, at='bool', k=True, ci=True, sn='FK', dv=1)

        constrain_list = []
        for i, ctl in enumerate(ctls):
            if i != len(ctls)-1: # If not the last ctl
                # Create offset transform
                offset_transform = cmds.createNode('transform', n=ctl.name.replace('_ctl_', '_ctlOff_'), 
                                                p=ctl.topCtl, ss=True)
                # Create hierarchy root
                hier_root = cmds.createNode('transform', n=ctl.name.replace('_ctl_', '_hierarchy_'), 
                                                p=ctl.topCtl, ss=True)
                # Create hierarchy offset
                hier_offset = cmds.createNode('transform', n=ctl.name.replace('_ctl_', '_hierarchyOffset_'), 
                                                p=ctl.topCtl, ss=True)

                # Next locator
                current_locator = cmds.listRelatives(ctls[i].grp, parent=1)[0]
                next_locator = cmds.listRelatives(ctls[i+1].grp, parent=1)[0]
                next_ctl = cmds.xform(ctls[i+1].topCtl, q=1, ws=1, matrix=True)

                # Move hierarchy root to next ctl pos
                cmds.xform(hier_root, ws=1, matrix=next_ctl)
                cmds.parent(hier_root, current_locator)
                cmds.makeIdentity(hier_root, apply=True, t=1, r=1, s=1)
                
                # Move hierarchyOffset to pos of next ctl pos
                cmds.xform(hier_offset, ws=1, matrix=next_ctl)
                cmds.parent(hier_offset, hier_root)
                cmds.makeIdentity(hier_offset, apply=True, t=1, r=1, s=1)

                # Move offset transform to pos of next ctl in chain
                cmds.xform(offset_transform, ws=1, matrix=next_ctl)
                cmds.makeIdentity(offset_transform, apply=True, t=1, r=1, s=1)

                t=['x','y','z']
                r=['x','y','z']
                s=['x','y','z']

                # hier_root drives offset_transform
                [cmds.connectAttr(f'{hier_root}.t{axis}', f'{offset_transform}.t{axis}') for axis in t]
                [cmds.connectAttr(f'{hier_root}.r{axis}', f'{offset_transform}.r{axis}') for axis in r]
                [cmds.connectAttr(f'{hier_root}.s{axis}', f'{offset_transform}.s{axis}') for axis in s]

                # hier_offset drives next bfr in chain
                [cmds.connectAttr(f'{hier_offset}.t{axis}', ctls[i+1].grp+'.t'+axis) for axis in t]
                [cmds.connectAttr(f'{hier_offset}.r{axis}', ctls[i+1].grp+'.r'+axis) for axis in r]
                [cmds.connectAttr(f'{hier_offset}.s{axis}', ctls[i+1].grp+'.s'+axis) for axis in s]

                # Constrain hierarchy offset offset transform
                constrain_list.append(cmds.parentConstraint(offset_transform, hier_offset, mo=True, n=offset_transform+'_parentConstraint'))
                constrain_list.append(cmds.scaleConstraint (offset_transform, hier_offset, mo=True, n=offset_transform+'_scaleConstraint'))

                # Constrain hierarchy root to next locator
                constrain_list.append(cmds.pointConstraint (next_locator, hier_root, mo=True, n=f'{hier_root}_pointConstraint'))
                constrain_list.append(cmds.parentConstraint(next_locator, hier_root, mo=True, st=['x', 'y', 'z'], n=f'{hier_root}_parentConstraint'))

        # Connect FK attr on first ctl to drive FK constraints. 0 returns to IK behavior
        for constraint in constrain_list:
            cmds.connectAttr(ctls[0].topCtl+'.FK', constraint[0]+'.'+cmds.listAttr(constraint)[-1])