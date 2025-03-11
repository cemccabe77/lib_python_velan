import maya.cmds as cmds
from maya.api import OpenMaya, OpenMayaAnim
from . import omUtil as omu
import xml.etree.ElementTree as et


def getSkinClusters(mshName):
    """
    Get the skinClusters attached to the specified node.
    mshName = (str) Mesh object
    """
    shpNde = omu.getDagPath(mshName, shape=True)
    history = cmds.listHistory(shpNde, pruneDagObjects=True, il=2) or []
    skin = [x for x in history if cmds.nodeType(x) == 'skinCluster']
    if skin:
        return skin[0]

def getSkinClusterInfluences(skin_cluster, full_path=False):
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

def getSkinClusterInfluenceIndex(skin_cluster, influence):
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

def setBindPose(mesh=None, setAngle=0, sknCls=None):
    '''
    Resets bindpose on all joints connected to skincluster on selected mesh.
    And sets joints prefered angle.
    
    mesh     = (str) Get skincluster from mesh
    setAngle = (bol) Set joints current oritentation to preferred angle
    sknCls   = ([ ]) list of skinclusters

    '''

    if sknCls == None: #Get skinCls from mesh
        sknCls = getSkinClusters(mesh)
        if not sknCls:
            print('Cannot find skinCluster on obj >> ' + mesh)

    if not isinstance(sknCls, list): #if not a list
        sknCls = [sknCls]

    if len(sknCls) != 0:
        for skn in sknCls:
            sknJts = getSkinClusterInfluences(skn)

            # Delete bindPose
            if cmds.listConnections(skn+'.bindPose'):
                cmds.delete(cmds.listConnections(skn+'.bindPose'))

            # Connect pre bind matrix
            for jnt in sknJts:
                jntIdx = getSkinClusterInfluenceIndex(skn, jnt)
                if setAngle > 0:
                    cmds.joint(jnt, e=1, spa=1) # Set preferred angle
                pos = cmds.getAttr(jnt+'.wim')
                cmds.setAttr(skn+'.bindPreMatrix[{}]'.format(jntIdx), pos, type='matrix')

def exportSkinWeights(skinObj=None):
    '''
    skinObj = ([]) List of objects
    '''
    if skinObj:
        skinObj = skinObj
    else:
        skinObj = cmds.ls(sl=1)

    if not skinObj:
        raise IndexError('No objects specified for weight map export')

    meshes = [x for x in skinObj if cmds.ls(cmds.listHistory(x, pdo=1), type='skinCluster') 
             and cmds.listRelatives(x, s=1)]

    if not meshes:
        raise IndexError('Specified objects do not contain a skinCluster')

    fileFilter = 'directories'
    saveLink = cmds.fileDialog2(fm=2, ds=2, ff=fileFilter, okc='Select Folder')
    if saveLink:
        for mesh in meshes:
            skin = getSkinClusters(mesh)
            saveFile = mesh + '_skin.xml'
            if cmds.nodeType(cmds.listRelatives(mesh, s=1)[0]) in 'mesh':
                cmds.deformerWeights(saveFile, p = saveLink[0], df = skin, ex=1, vc=1)
            if cmds.nodeType(cmds.listRelatives(mesh, s=1)[0]) not in 'mesh':
                cmds.deformerWeights(saveFile, p = saveLink[0], df = skin, ex=1)

def importSkinWeights(xmls=None):
    '''
    Imports skinWeights from xml. Creates skinCluster on obj if it does not exist.

    xmls = (list) List of xml skin files to import
    '''

    if not xmls:
        xmls = cmds.fileDialog2(fileMode=4, fileFilter='*.xml', okc='Import File(s)')
    if xmls:
        for skinFile in xmls:
            weightFile  = skinFile.split('/')[-1]
            wPath = skinFile[:-len(weightFile)] # Set path arg for cmds.deformerWeights()
            skinFileXML = None
            skinFileXML = et.parse(skinFile)
            sknMsh      = weightFile.split('_skin.xml')[0]
            
            # root        = skinFileXML.getroot()
            influences = []
            for elem in skinFileXML.findall('weights'):
                jnt = elem.get('source')
                influences.append(jnt)
            # Make sure objects exists
            sknInfl = []
            for jnt in influences:
                if cmds.objExists(jnt):
                    sknInfl.append(jnt)

            if cmds.objExists(sknMsh) and sknInfl != []:
                # Check for existing skinCluster
                if getSkinClusters(sknMsh):
                    currSkin = getSkinClusters(sknMsh)
                    currInfl = getSkinClusterInfluences(currSkin)
                    # add any missing joints to current skinCluster
                    toAdd = [x for x in sknInfl if x not in currInfl]
                    if toAdd:
                        cmds.skinCluster(currSkin, e=1, ai=toAdd , lw=1, wt=0)
                    # load skin weights
                    cmds.deformerWeights(weightFile, path=wPath, im=1, df=currSkin, m='index')
                    [cmds.setAttr(infs + '.liw', 0) for infs in cmds.skinCluster(currSkin, q=1, inf=1)]
                    cmds.skinPercent(currSkin, sknMsh, nrm=1)
                else:
                    skin = cmds.skinCluster(sknMsh, sknInfl, tsb=1)[0]
                    cmds.deformerWeights(weightFile, path=wPath, im=1, df=skin, m='index')
                    cmds.skinPercent(skin, sknMsh, nrm=1)
            else:
                print(sknMsh, '<'*80)
                cmds.warning('Skin object does not exist in the scene')

def transferWeights(objLst=[], remove=False):
    '''
    objLst = ([]) List of object, source first.
    remove = (bol) Remove unused influences

    If no objLst, then selection based. 
    Target first. Multiple targets allowed.
    Nurbs surfaces and curves are supported.
    '''

    if objLst == []:
        if len(cmds.ls(sl=1))<2:
            raise IndexError('Select source, then target')
        else:
            source, target = cmds.ls(sl=1)[0], cmds.ls(sl=1)[1:]#(multiple targets)
    else:
        source, target = objLst[0], objLst[1:]


    for tgt in target:
        srcSkn = None
        tgtSkn = None
        srcSkn = getSkinClusters(source)
        tgtSkn = getSkinClusters(tgt)
        tgtTyp = cmds.objectType(omu.getDagPath(tgt, shape=True))

        if tgtTyp == 'nurbsSurface':
            if srcSkn and not tgtSkn:
                jts = getSkinClusterInfluences(srcSkn)
                cmds.select(jts, r=True) # cmds.skinCluster kept adding joint heirarchy. Using select instead.
                cmds.select(tgt, add=True)
                tgtSkn = cmds.skinCluster(tgt, jts, tsb=True)[0]
                cmds.copySkinWeights(source, tgt.cv, noMirror=True, surfaceAssociation='closestPoint', ia=['oneToOne','name'])
            if srcSkn and tgtSkn:
                cmds.copySkinWeights(source, tgt.cv, noMirror=True, surfaceAssociation='closestPoint', ia=['oneToOne','name'])

        elif tgtTyp == 'mesh':
            if srcSkn and not tgtSkn:
                jts = getSkinClusterInfluences(srcSkn)
                cmds.select(jts, r=True) # cmds.skinCluster kept adding joint heirarchy. Using select instead.
                cmds.select(tgt, add=True)
                tgtSkn = cmds.skinCluster(tgt, jts, tsb=True)[0]
                cmds.copySkinWeights(ss=srcSkn, ds=tgtSkn, noMirror=True, sa='closestPoint', ia=['closestJoint', 'oneToOne'])
            if srcSkn and tgtSkn:
                cmds.copySkinWeights(ss=srcSkn, ds=tgtSkn, noMirror=True, sa='closestPoint', ia=['closestJoint', 'oneToOne'])

        elif tgtTyp == 'nurbsCurve':
            if srcSkn and not tgtSkn:
                jts = getSkinClusterInfluences(srcSkn)
                cmds.select(jts, r=True) # cmds.skinCluster kept adding joint heirarchy. Using select instead.
                cmds.select(tgt, add=True)
                tgtSkn = cmds.skinCluster(tgt, jts, tsb=True)[0]
                cmds.copySkinWeights(source, tgt.cv, noMirror=True, surfaceAssociation='closestPoint', ia=['oneToOne','name'])
            if srcSkn and tgtSkn:
                cmds.copySkinWeights(source, tgt.cv, noMirror=True, surfaceAssociation='closestPoint', ia=['oneToOne','name'])

        if remove:
            removeUnusedInfluences(tgtSkn)

    cmds.select(target[-1], r=True)


def removeUnusedInfluences(sknCluster):
    currentInfluences = cmds.skinCluster(sknCluster, q=True, inf=True)

    weightedInfs = cmds.skinCluster(sknCluster, q=True, weightedInfluence=True)

    influencesToRemove = []
    for inf in currentInfluences:
        if inf not in weightedInfs:
            influencesToRemove.append(inf)

    if influencesToRemove != []:
        for inf in influencesToRemove:
            cmds.skinCluster(sknCluster, e=True, ri=inf)
