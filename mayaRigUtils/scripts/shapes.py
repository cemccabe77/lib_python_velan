import maya.cmds as cmds


def getShapes(node, orig=False):
    '''
    Returns Orig shape, or all shapes

    node = (str) Name of node to query
    orig = (bol) Return orig shape only
    '''
    shapes = cmds.listRelatives(node, shapes=True)
    if orig == False:
        return shapes
    
    if len(shapes) > 2:    
        shapes = shapes[0:2]

    output_shapes = [s for s in shapes if cmds.getAttr(f'{s}.intermediateObject')]
    current_shape = cmds.listRelatives(node, shapes=True)[0]
    if len(output_shapes) != 1:
        return False

    for shape in shapes:
        is_output = shape in output_shapes
        if is_output == True:
            return(shape)

def getGeometryType(geometry):
    '''
    Returns geometry type
    '''
    if "." in geometry:
        return cmds.getAttr(geometry, type=True)

    if "transform" in cmds.nodeType(geometry, inherited=True):
        shapes = cmds.listRelatives(geometry, shapes=True, noIntermediate=True)
        if not shapes:
            raise RuntimeError(
                "No shape nodes associated with '{}'.".format(geometry))
        geometry = shapes[0]

    return cmds.nodeType(geometry)

def duplicateClean(source, name, parent=None, shapeOnly=False):
    '''
    Duplicates an object without construction history.
    Or creates new shape node (orig) - used in proximityWrap in rigUtils

    source = (str) Name of object
    name   = (str) Name of new object to create
    parent = (str) Name of object to parent new object under
    shapeOnly = (bol) Create new shape node
    '''
    sourceType = getGeometryType(source)
    
    dup=None
    if not shapeOnly:
        dup = cmds.createNode("transform", name=name, parent=parent) 
        parent = dup

    duplicateShape = cmds.createNode(sourceType, name=name, parent=parent) 
    cmds.connectAttr(source+'.outMesh', duplicateShape+'.inMesh')
    cmds.dgeval(duplicateShape+'.outMesh')
    cmds.disconnectAttr(source+'.outMesh', duplicateShape+'.inMesh')
    cmds.sets(duplicateShape, forceElement="initialShadingGroup")
    cmds.setAttr(duplicateShape+'.intermediateObject', 1)


    return dup or duplicateShape