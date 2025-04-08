from maya import OpenMaya as om


def get_dag_path(node, shape):
    '''
    Gets Maya dag path

    node  = (str) Name of maya object
    shape = (bol) Return Shape node
    '''
    
    if shape:
        sel = om.MSelectionList()
        sel.add(node)
        d = om.MDagPath()
        sel.getDagPath(0, d)
        d.extendToShapeDirectlyBelow( 0 )
        # print(d.partialPathName())
        return d.partialPathName()
    else:
        sel = om.MSelectionList()
        sel.add(node)
        d = om.MDagPath()
        sel.getDagPath(0, d)
        # print(d.partialPathName())
        return d

def get_mdagpath_from_object_name(object_name):
  '''
  Returns the corresponding MDagPath object based on the objectName as a string. 

  Accepts:
    objectName - string

  Returns: 
    MDagPath object
  '''

  selection_list = om.MSelectionList()
  selection_list.add(object_name)  
  dag_path = om.MDagPath()
  it = om.MItSelectionList(selection_list)
  it.getDagPath(dag_path)
  
  return dag_path

