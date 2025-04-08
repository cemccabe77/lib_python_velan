import maya.cmds as cmds
from maya.api import OpenMaya, OpenMayaAnim
from . import omUtil as omu
import xml.etree.ElementTree as et


def get_skin_clusters(mesh_name):
    """
    Get the skinClusters attached to the specified node.
    mesh_name = (str) Mesh object
    """
    shape_node = omu.get_dag_path(mesh_name, shape=True)
    history = cmds.listHistory(shape_node, pruneDagObjects=True, il=2) or []
    skin = [x for x in history if cmds.nodeType(x) == 'skinCluster']
    if skin:
        return skin[0]

def get_skin_cluster_influences(skin_cluster, full_path=False):
    """Get skin_cluster influences.

    Args:
        skin_cluster (str): skinCluster node
        full_path (bool): If true returns full path, otherwise partial path of
            influence names.

    Return:
        list(str,): influences
    """
    name = "fullPathName" if full_path else "partialPathName"
    skin_cluster_obj = (
        OpenMaya.MSelectionList().add(skin_cluster).getDependNode(0)
    )
    inf_objs = OpenMayaAnim.MFnSkinCluster(
        skin_cluster_obj
    ).influenceObjects()
    influences = [getattr(x, name)() for x in inf_objs]

    return influences

def get_skin_cluster_influence_index(skin_cluster, influence):
    """Get the index of given influence.

    Args:
        skin_cluster (str): skinCluster node
        influence (str): influence object

    Return:
        int: index
    """
    skin_cluster_obj = (
        OpenMaya.MSelectionList().add(skin_cluster).getDependNode(0)
    )
    influence_dag = OpenMaya.MSelectionList().add(influence).getDagPath(0)
    index = int(
        OpenMayaAnim.MFnSkinCluster(
            skin_cluster_obj
        ).indexForInfluenceObject(influence_dag)
    )

    return index

def set_bind_pose(mesh_name=None, set_angle=0, skin_cluster=None):
    '''
    Resets bindpose on all joints connected to skincluster on selected mesh.
    And sets joints prefered angle.
    
    mesh_name     = (str) Get skincluster from mesh
    set_angle = (bol) Set joints current oritentation to preferred angle
    skin_cluster   = ([ ]) list of skinclusters

    '''

    if skin_cluster == None: #Get skinCls from mesh
        skin_cluster = get_skin_clusters(mesh_name)
        if not skin_cluster:
            print(f'Cannot find skinCluster on obj >> {mesh_name}')

    if not isinstance(skin_cluster, list): #if not a list
        skin_cluster = [skin_cluster]

    if len(skin_cluster) != 0:
        for skin in skin_cluster:
            skin_joints = get_skin_cluster_influences(skin_cluster=skin)

            # Delete bindPose
            if cmds.listConnections(skin+'.bindPose'):
                cmds.delete(cmds.listConnections(skin+'.bindPose'))

            # Connect pre bind matrix
            for joint in skin_joints:
                joint_index = get_skin_cluster_influence_index(skin_cluster=skin, influence=joint)
                if set_angle > 0:
                    cmds.joint(joint, e=1, spa=1) # Set preferred angle
                pos = cmds.getAttr(f'{joint}.wim')
                try:
                    cmds.setAttr(f'{skin}.bindPreMatrix[{joint_index}]', pos, type='matrix')
                except:
                    raise IndexError(f'bind_pre_matrix could not be set for joint >> {joint}. \
                                        This action cannot be performed on a "dorito" mesh.')

def export_skin_weights(skin_obj=None):
    '''
    skin_obj = ([]) List of objects
    '''

    if skin_obj:
        skin_obj = skin_obj
    else:
        skin_obj = cmds.ls(sl=1)

    if not skin_obj:
        raise IndexError('No objects specified for weight map export')

    meshes = [x for x in skin_obj if cmds.ls(cmds.listHistory(x, pdo=1), type='skinCluster') 
             and cmds.listRelatives(x, s=1)]

    if not meshes:
        raise IndexError('Specified objects do not contain a skinCluster')

    file_filter = 'directories'
    save_link = cmds.fileDialog2(fm=2, ds=2, ff=file_filter, okc='Select Folder')
    if save_link:
        for mesh in meshes:
            skin = get_skin_clusters(mesh_name=mesh)
            saveFile = mesh + '_skin.xml'
            if cmds.nodeType(cmds.listRelatives(mesh, s=1)[0]) in 'mesh':
                cmds.deformerWeights(saveFile, p = save_link[0], df = skin, ex=1, vc=1)
            if cmds.nodeType(cmds.listRelatives(mesh, s=1)[0]) not in 'mesh':
                cmds.deformerWeights(saveFile, p = save_link[0], df = skin, ex=1)

def import_skin_weights(xml=None):
    '''
    Imports skinWeights from xml. Creates skinCluster on obj if it does not exist.

    xml = (list) List of xml skin files to import
    '''

    if not xml:
        xml = cmds.fileDialog2(fileMode=4, fileFilter='*.xml', okc='Import File(s)')
    if xml:
        for skin_file in xml:
            weight_file = skin_file.split('/')[-1]
            weight_path = skin_file[:-len(weight_file)] # Set path arg for cmds.deformerWeights()
            skin_file_xml = None
            skin_file_xml = et.parse(skin_file)
            skin_mesh = weight_file.split('_skin.xml')[0]
            
            # root = skin_file_xml.getroot()
            influences = []
            for element in skin_file_xml.findall('weights'):
                jnt = element.get('source')
                influences.append(jnt)
            
            # Make sure objects exists
            skin_influences = []
            for jnt in influences:
                if cmds.objExists(jnt):
                    skin_influences.append(jnt)

            if cmds.objExists(skin_mesh) and skin_influences != []:
                # Check for existing skinCluster
                if get_skin_clusters(mesh_name=skin_mesh):
                    skin_cluster = get_skin_clusters(mesh_name=skin_mesh)
                    current_influence = get_skin_cluster_influences(skin_cluster=skin_cluster)
                    
                    # add any missing joints to current skinCluster
                    cluster_joints = [joint for joint in skin_influences if joint not in current_influence]
                    if cluster_joints:
                        cmds.skinCluster(skin_cluster, e=1, ai=cluster_joints , lw=1, wt=0)
                    
                    # load skin weights
                    cmds.deformerWeights(weight_file, path=weight_path, im=1, df=skin_cluster, m='index')
                    [cmds.setAttr(f'{infs}.liw', 0) for infs in cmds.skinCluster(skin_cluster, q=1, inf=1)]
                    cmds.skinPercent(skin_cluster, skin_mesh, nrm=1)
                else:
                    skin = cmds.skinCluster(skin_mesh, skin_influences, tsb=1)[0]
                    cmds.deformerWeights(weight_file, path=weight_path, im=1, df=skin, m='index')
                    cmds.skinPercent(skin, skin_mesh, nrm=1)
            else:
                cmds.warning(f'Skin object does not exist in the scene >> {skin_mesh}')

def transfer_weights(object_list=[], remove=False):
    '''
    object_list = ([]) List of object, source first.
    remove = (bol) Remove unused influences

    If no object_list, then selection based. 
    Target first. Multiple targets allowed.
    Nurbs surfaces and curves are supported.
    '''

    if object_list == []:
        if len(cmds.ls(sl=1))<2:
            raise IndexError('Select source, then target')
        else:
            source, target = cmds.ls(sl=1)[0], cmds.ls(sl=1)[1:]#(multiple targets)
    else:
        source, target = object_list[0], object_list[1:]


    for tgt in target:
        src_skn = None
        tgt_skn = None
        src_skn = get_skin_clusters(mesh_name=source)
        tgt_skn = get_skin_clusters(mesh_name=tgt)
        tgt_typ = cmds.objectType(omu.get_dag_path(tgt, shape=True))

        if tgt_typ == 'nurbsSurface':
            if src_skn and tgt_skn:
                cmds.copySkinWeights(sourceSkin=src_skn, destinationSkin=tgt_skn, noMirror=True, 
                                         surfaceAssociation="closestPoint", 
                                         influenceAssociation=["oneToOne", "name", "label", "closestJoint"])
            else:
                if src_skn and not tgt_skn:
                    jts = get_skin_cluster_influences(skin_cluster=src_skn)
                    cmds.select(jts, r=True) # cmds.skinCluster kept adding joint heirarchy. Using select instead.
                    cmds.select(tgt, add=True)
                    tgt_skn = cmds.skinCluster(tgt, jts, tsb=True)[0]
                    cmds.copySkinWeights(sourceSkin=src_skn, destinationSkin=tgt_skn, noMirror=True, 
                                         surfaceAssociation="closestPoint", 
                                         influenceAssociation=["oneToOne", "name", "label", "closestJoint"])


        elif tgt_typ == 'mesh':
            if src_skn and tgt_skn:
                cmds.copySkinWeights(ss=src_skn, ds=tgt_skn, noMirror=True, sa='closestPoint', ia=['closestJoint', 'oneToOne'])
            else:
                if src_skn and not tgt_skn:
                    jts = get_skin_cluster_influences(skin_cluster=src_skn)
                    cmds.select(jts, r=True) # cmds.skinCluster kept adding joint heirarchy. Using select instead.
                    cmds.select(tgt, add=True)
                    tgt_skn = cmds.skinCluster(tgt, jts, tsb=True)[0]
                    cmds.copySkinWeights(ss=src_skn, ds=tgt_skn, noMirror=True, sa='closestPoint', ia=['closestJoint', 'oneToOne'])


        elif tgt_typ == 'nurbsCurve':
            if src_skn and tgt_skn:
                cmds.copySkinWeights(sourceSkin=src_skn, destinationSkin=tgt_skn, noMirror=True, 
                                         surfaceAssociation="closestPoint", 
                                         influenceAssociation=["oneToOne", "name", "label", "closestJoint"])
            else:
                if src_skn and not tgt_skn:
                    jts = get_skin_cluster_influences(skin_cluster=src_skn)
                    cmds.select(jts, r=True) # cmds.skinCluster kept adding joint heirarchy. Using select instead.
                    cmds.select(tgt, add=True)
                    tgt_skn = cmds.skinCluster(tgt, jts, tsb=True)[0]
                    cmds.copySkinWeights(sourceSkin=src_skn, destinationSkin=tgt_skn, noMirror=True, 
                                         surfaceAssociation="closestPoint", 
                                         influenceAssociation=["oneToOne", "name", "label", "closestJoint"])
        if remove:
            remove_unused_influences(skin_cluster=tgt_skn)

    cmds.select(target[-1], r=True)

def remove_unused_influences(skin_cluster):
    influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
    used_influences = cmds.skinCluster(skin_cluster, q=True, weightedInfluence=True)

    remove_influences = []
    for inf in influences:        
        if inf not in used_influences:
            remove_influences.append(inf)

    if remove_influences != []:
        for inf in remove_influences:
            cmds.skinCluster(skin_cluster, e=True, ri=inf)
