'''
DESCRIPTION:
    Maya dockable window
USAGE:
    from dockableWidget import (
        DockableWidgetUIScript, DemoDockableWidget)

    # Create
    DemoDockableWidget = DockableWidgetUIScript(DemoDockableWidget)

    # Delete
    DockableWidgetUIScript(DemoDockableWidget, delete=True)

    # Query
    import maya.cmds as cmds

    uiExists = cmds.workspaceControl(DemoDockableWidget.workspace_ctrl_name, query=True, exists=True)
    print('UI Exists: %s') % uiExists

    # If user closes the workspaceControl it is not deleted, but hidden
    from dockableWidget import findControl

    ctrl = DemoDockableWidget.workspace_ctrl_name

    # Show/Hide workspaceControl
    cmds.workspaceControl(ctrl, edit=True, restore=True)
    cmds.workspaceControl(ctrl, edit=True, visible=False)
    cmds.workspaceControl(ctrl, edit=True, visible=True)
'''

from __future__ import print_function

# auto docs build compatibility
try:
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
    from maya import OpenMayaUI as omui
    import maya.cmds as cmds
    mayaAvailable = False
except ImportError:
    mayaAvailable = False
    MayaQWidgetDockableMixin = type('MayaQWidgetDockableMixin', (), {})

try:
    from PySide2.QtWidgets import (
        QLabel,
        QSizePolicy,
        QWidget,
        QVBoxLayout)
    from PySide2.QtCore import (
        Signal, Qt)
except ImportError:
    from PySide.QtWidgets import (
        QLabel,
        QSizePolicy,
        QWidget,
        QVBoxLayout)
    from PySide.QtCore import (
        Signal, Qt)

try:
    from shiboken2 import wrapInstance
except ImportError:
    try:
        from shiboken import wrapInstance
    except ImportError:
        pass

from .widgetRegistry import SingleItemRegistry


# CONSTANTS
UI_SCRIPT_TEMPLATE_DEFAULT = (
    'import dockableWidget as dw;\n'
    'dw.DockableWidgetUIScript(dw.DemoDockableWidget, restore=True)')


class DockableWidget(MayaQWidgetDockableMixin, QWidget):
    '''
    A widget that can be dockable in the Maya interface
    '''
    registry = SingleItemRegistry

    ctrl_obj_name = 'DockableWidgetNameNotSet'
    workspace_ctrl_name = ctrl_obj_name + 'WorkspaceControl'
    window_title = 'Window Title Not Set'
    uiScript = UI_SCRIPT_TEMPLATE_DEFAULT


    def __init__(self, parent=None, **kwargs):
        super(DockableWidget, self).__init__(parent=parent, **kwargs)

        self.registry.register(self)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setWindowTitle(self.window_title)
        self.setObjectName(self.ctrl_obj_name)
        self.setContentsMargins(0, 0, 0, 0)


    def __del__(self):
        # Change to True to debug
        if False:
            print('{} Being deleted'.format(self))


class DemoDockableWidget(DockableWidget):
    '''
    Demo of how to create a dockable widget

    The class variables are all required, though not enforced in the code.
    Whether this will or won't change is TBD.

    The `uiScript` variable is especially important since this governs
    much of the behavior of the control:

    https://help.autodesk.com/cloudhelp/2017/ENU/Maya-Tech-Docs/CommandsPython/workspaceControl.html
    '''
    # Unique name
    ctrl_obj_name = 'MyReallyAwesomeCustomWidget'

    # All workspace controls are named this way by Maya
    workspace_ctrl_name = ctrl_obj_name + 'WorkspaceControl'

    # Tile for your workspace control tab
    window_title = 'Awesome Custom Window Title'

    # Script Maya executes to build the UI of the workspaceControl
    uiScript = UI_SCRIPT_TEMPLATE_DEFAULT


    def __init__(self, parent=None, **kwargs):
        if self.registry.getInstance(DemoDockableWidget) is not None:
            print('\nREGISTRY WARNING (for demo purposes):')
            print('Cannot create multiple UI instances for any single type.\n'
                  'Therefore the old instance will be replaced in the registry.\n')
        super(DemoDockableWidget, self).__init__(parent=parent)

        self.label = QLabel()
        self.label.setText('DEMO UI')
        self.label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)

        self.setLayout(layout)


def findControl(objName, ctrlType):
    '''Utility to get a Python instance of a control with a given name'''
    ptr = omui.MQtUtil.findControl(objName)
    ####TODO##
    #ctrl = wrapInstance(long(ptr), ctrlType) if ptr else None
    ctrl = wrapInstance(int(ptr), ctrlType) if ptr else None

    if ctrl:
        print('Control found: {}'.format(objName))
    else:
        print('Control not found: \'{}\''.format(objName))

    return ctrl


def deleteWorkspaceControl(control):
    '''Utility to wipe out a workspace control completely'''
    if cmds.workspaceControl(control, q=True, exists=True):
        cmds.workspaceControl(control, e=True, close=True)
        cmds.deleteUI(control, control=True)
        print('Control deleted: {}'.format(control))
    else:
        print('Control not found: \'{}\''.format(control))


def DockableWidgetUIScript(dockableWidgetType, restore=False, delete=False):
    '''
    When the control is restoring, the workspace control has already
    been created and all that needs to be done is restoring its UI.
    '''
    # global customMixinWindow
    registry = getattr(dockableWidgetType, 'registry', None)
    instance = registry.getInstance(dockableWidgetType) if registry else None
    customMixinWindow = instance # could be None
    ctrl_obj_name = dockableWidgetType.ctrl_obj_name

    if delete == True:
        # If due to some error, or uiScript of workspace control has
        # changed, the control needs to be recreated
        ctrl = findControl(ctrl_obj_name, QWidget)

        # Workspace control found, now try to delete it.
        #
        # This first method isn't really necessary
        # as the workspace control name is always the name of the
        # child control with 'WorkspaceControl' appended.
        #
        # If the control is not found, fallback to the second method.
        if ctrl:
            # Reference this immediately! It tends to be very volitile.
            workspaceCtrl = ctrl.parent().objectName()
        else:
            workspaceCtrl = ctrl_obj_name + 'WorkspaceControl'

        deleteWorkspaceControl(workspaceCtrl)
        customMixinWindow = None

        return

    elif restore == True:
        # Grab the created workspace control with the following.
        restoredControl = omui.MQtUtil.getCurrentParent()

    if customMixinWindow is None:
        # Create a custom mixin widget for the first time
        customMixinWindow = dockableWidgetType()
        customMixinWindow.setObjectName(ctrl_obj_name)

    if restore == True:
        # Add custom mixin widget to the workspace control
        mixinPtr = omui.MQtUtil.findControl(ctrl_obj_name)
        ####TODO##
        #omui.MQtUtil.addWidgetToMayaLayout(long(mixinPtr), long(restoredControl))
        omui.MQtUtil.addWidgetToMayaLayout(int(mixinPtr), int(restoredControl))
    else:
        # Create a workspace control for the mixin widget by passing
        # all the needed parameters. See workspaceControl command
        # documentation for all available flags.
        try:
            customMixinWindow.show(
                dockable=True,
                height=320, width=240,
                uiScript=dockableWidgetType.uiScript)
        # There is an issue if maintaining a reference to an instance
        # which has been wrapped by Maya and deleted prior to calling
        # this script. Storing weak references to the instances also
        # does not solve this problem as they get garbage collected as
        # soon as they are wrapped
        # TODO: control deleted callback?
        except RuntimeError:
            customMixinWindow = dockableWidgetType()
            customMixinWindow.setObjectName(ctrl_obj_name)
            customMixinWindow.show(
                dockable=True,
                height=320, width=240,
                uiScript=dockableWidgetType.uiScript)

    return customMixinWindow


def main():
    ui = DockableWidgetUIScript()
    return ui


if __name__ == '__main__':
    # NOTE: main cannot be run more than once since control will not
    # get deleted by Maya between calls and name clash will result
    main()
