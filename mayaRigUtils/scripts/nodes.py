import maya.cmds as cmds


def getNextFreeMultiIndex(attrName, startIndex):
	'''
	Find the next unconnected multi index starting at the passed in index.
	'''
	# assume a max of 1 million connections
	while startIndex < 1000000:
		if len( cmds.connectionInfo( '{}[{}]'.format(attrName, startIndex), sfd=True ) or [] ) == 0:
			return startIndex
		startIndex += 1
	# No connections means the first index is available
	return 0

def transfer_standard_attrs(source, target, create_attrs_if_they_dont_exist = True):
    """
    Transfer over the standard model publish attributes from one transform to another, applies attributes to both the new transform and its shape

    create_attrs_if_they_dont_exist(bool): if set to True, the script will create the attributes if they dont exist
    returns None
    """
    model_status_attrs = ["mdlAssetID",
                        "mdlDate",
                        "mdlDateString",
                        "mdlPath",
                        "mdlTaskID",
                        "mdlUsername",
                        "mdlVersion",
                        "mdlUUID",
                        "mdlPreviousName",
                        "mdlCurrentName"]

    for attr in model_status_attrs:
        val = cmds.getAttr(source + "." + attr)
        shape = cmds.listRelatives(target,s=True)
        
        if create_attrs_if_they_dont_exist == True:
            if not cmds.objExists(target + "." + attr):
                cmds.addAttr(target, ln = attr, dt = "string", k = True)
            if shape:    
                if not cmds.objExists(shape[0] + "." + attr):
                    cmds.addAttr(shape[0], ln = attr, dt = "string", k = True)
              
        cmds.setAttr(target + "." + attr, val, type = "string")   
        if shape:
            cmds.setAttr(shape[0] + "." + attr, val, type = "string")



	# # transfer on single sel
	# sel = cmds.selected()
	# transfer_standard_attrs(sel[0], sel[1], create_attrs_if_they_dont_exist = True)



	# # transfer on multiple sel
	# atrLst = cmds.ls(sl=1)
	# tgtLst = cmds.ls(sl=1)
	# for k in zip(atrLst, tgtLst):
	#     transfer_standard_attrs(k[0], k[1], create_attrs_if_they_dont_exist = True)



