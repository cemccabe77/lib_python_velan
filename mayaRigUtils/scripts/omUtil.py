from maya import OpenMaya as om


def getDagPath(node, shape):
    '''
    Gets Maya dag path

    node  = (str) Name of maya object
    shape = (bol) Return Shape node
    '''
    


    '''
    # Get the MDagPath of the object.
    sel_list = om.MSelectionList()
    sel_list.add( node )
    dag = om.MDagPath()
    component = om.MObject()
    sel_list.getDagPath( 0, dag, component )

    # Show that we have the trasnform node.
    print dag.partialPathName()

    # Extend the MDagPath to the shape node.
    dag.extendToShapeDirectlyBelow( 0 )

    # Show that we now have the shape node.
    print dag.partialPathName()

    return dag.partialPathName()
    '''



    if shape:
        sel = om.MSelectionList()
        sel.add(node)
        d = om.MDagPath()
        sel.getDagPath(0, d)
        d.extendToShapeDirectlyBelow( 0 )
        print(d.partialPathName())
        return d.partialPathName()
    else:
        sel = om.MSelectionList()
        sel.add(node)
        d = om.MDagPath()
        sel.getDagPath(0, d)
        print(d.partialPathName())
        return d

def get_mdagpath_from_object_name( object_name ):
  '''
  Returns the corresponding MDagPath object based on the objectName as a string. 

  Accepts:
    objectName - string

  Returns: 
    MDagPath object

  '''

  selList = om.MSelectionList()
  selList.add( object_name )  
  dagPath = om.MDagPath()
  it = om.MItSelectionList( selList )
  it.getDagPath(dagPath)
  
  return dagPath

