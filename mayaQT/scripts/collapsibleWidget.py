'''
import collapsibleWidget

dui = collapsibleWidget.Demo()
dui.show()
'''
import os
from functools import partial

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class CollapsibleWidget(QGroupBox):
    '''
    DESCRIPTION:
        A collapsible group box widget

        :param QWidget widget: content of the collapsible item
        :param str title: label for the item
        :param QWidget parent: optional parent widget
    '''
    expandAllRequested = Signal()
    collapseAllRequested = Signal()
    clearAllRequested = Signal()
    clearSelectedRequested = Signal(object)

    Boxed = 1
    Rounded = 2
    Square = 3
    Maya = 4


    def __init__(self, widget, title='CollapsibleWidget', setTextColor=QColor(255.0, 255.0, 255.0), showExpandCollapseMenu=False, showDeleteMenu=False, collapsed=False, collapsible=True, parent=None):
        QGroupBox.__init__(self, parent)

        # list widget
        self._parent = parent

        self.mainLayout = layout = QVBoxLayout()
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        self._expandCollapseRect = QRect(0, 0, 30, 20)

        self._rolloutStyle = CollapsibleWidget.Maya

        self.setAcceptDrops(True)
        self.setLayout(layout)

        self.showExpandCollapseMenu = showExpandCollapseMenu
        self.showDeleteMenu = showDeleteMenu

        if showExpandCollapseMenu or showDeleteMenu:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.showMenu)

        self._widget = None
        self._collapsed = collapsed
        self._collapsible = collapsible
        self._clicked = False

        self.setTitle(QApplication.translate('CollapsibleWidget', title, None, -1))
        self._setTextColor = setTextColor


    def setWidget(self, widget):
        self.layout().addWidget(widget)
        self._widget = widget


    def widget(self):
        return self._widget


    def showMenu(self):
        if QRect(0, 0, self.width(), 20).contains(
            self.mapFromGlobal(QCursor.pos())):
            menu = QMenu()

            if self.showExpandCollapseMenu:
                expandAct = menu.addAction('Expand All')
                expandAct.triggered.connect(self.onExpandAllTriggered)

                collapseAct = menu.addAction('Collapse All')
                collapseAct.triggered.connect(self.onCollapseAllTriggered)

            if self.showDeleteMenu:
                clearAct = menu.addAction('Delete All')
                clearAct.triggered.connect(self.onClearAllTriggered)

                clearSelectedAct = menu.addAction('Delete Selected')
                clearSelectedAct.triggered.connect(self.onClearSelectedTriggered)

            menu.exec_(QCursor.pos())


    def onExpandAllTriggered(self):
        self.expandAllRequested.emit()


    def onCollapseAllTriggered(self):
        self.collapseAllRequested.emit()


    def onClearAllTriggered(self):
        self.clearAllRequested.emit()


    def onClearSelectedTriggered(self):
        self.clearSelectedRequested.emit(self)


    def setTextColor(self):
        return self._setTextColor


    def isCollapsed(self):
        return self._collapsed


    def isCollapsible(self):
        return self._collapsible


    def setCollapsible(self, state=False):
        self._collapsible = state


    def setCollapsed(self, state=False):
        if self.isCollapsible():
            parent = self._parent
            parent.setUpdatesEnabled(False)

            self._collapsed = state

            if state:
                self.setMinimumHeight(22)
                self.setMaximumHeight(22)
                self.widget().setVisible(False)
                parent.itemCollapsed.emit(self)
            else:
                self.setMinimumHeight(0)
                self.setMaximumHeight(1000000)
                self.widget().setVisible(True)
                parent.itemExpanded.emit(self)

            parent.setUpdatesEnabled(True)


    def toggleCollapsed(self):
        self.setCollapsed(not self.isCollapsed())


    def mouseReleaseEvent(self, event):
        if self._clicked and self._expandCollapseRect.contains(event.pos()):
            self.toggleCollapsed()
            event.accept()
        else:
            event.ignore()

        self._clicked = False


    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton
            and self._expandCollapseRect.contains(event.pos())):
            self._clicked = True
            event.accept()
        else:
            event.ignore()


    def setRolloutStyle(self, style):
        self._rolloutStyle = style


    def rolloutStyle(self):
        return self._rolloutStyle


    def __drawTriangle(self, painter, x, y):
        painter.setRenderHint(painter.Antialiasing, False)
        brush = QBrush(QColor(255, 255, 255, 255), Qt.SolidPattern)

        if not self.isCollapsed():
            tl, tr, tp = QPoint(x + 13, y + 8), QPoint(x + 24, y + 8), QPoint(x + 18, y + 13.0)
            points = [tl, tr, tp]
            triangle = QPolygon(points)
        else:
            tl, tr, tp = QPoint(x + 15, y + 6), QPoint(x + 20, y + 11), QPoint(x + 15, y + 16.0)
            points = [tl, tr, tp]
            triangle = QPolygon(points)

        currentBrush = painter.brush()
        painter.setBrush(brush)
        painter.drawPolygon(triangle)
        painter.setBrush(currentBrush)


    def paintEvent( self, event ):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(painter.Antialiasing)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)

        x = self.rect().x()
        y = self.rect().y()
        w = self.rect().width() - 1
        h = self.rect().height() - 1
        r = 8

        if self._rolloutStyle == CollapsibleWidget.Rounded:
            # draw the text
            painter.setPen(QColor(self._setTextColor))
            painter.drawText(x + 33, y + 3, w, 16, Qt.AlignLeft | Qt.AlignTop, self.title())

            # draw the triangle
            self.__drawTriangle(painter, x, y)

            # draw the borders
            pen = QPen(self.palette().color(QPalette.Light))
            pen.setWidthF(0.6)
            painter.setPen(pen)

            painter.drawRoundedRect(x + 1, y + 1, w - 1, h - 1, r, r)

            pen.setColor(self.palette().color(QPalette.Shadow))
            painter.setPen(pen)

            painter.drawRoundedRect(x, y, w - 1, h - 1, r, r)

        if self._rolloutStyle == CollapsibleWidget.Square:
            # draw the text
            painter.setPen(QColor(self._setTextColor))
            painter.drawText(x + 33, y + 3, w, 16, Qt.AlignLeft | Qt.AlignTop, self.title())

            self.__drawTriangle(painter, x, y)

            # draw the borders
            pen = QPen(self.palette().color(QPalette.Light))
            pen.setWidthF(0.6)
            painter.setPen(pen)

            painter.drawRect(x + 1, y + 1, w - 1, h - 1)

            pen.setColor(self.palette().color(QPalette.Shadow))
            painter.setPen(pen)

            painter.drawRect(x, y, w - 1, h - 1)

        if self._rolloutStyle == CollapsibleWidget.Maya:
            # Text
            painter.setPen(QColor(self._setTextColor))
            painter.drawText(x + 33, y + 3, w, 16, Qt.AlignLeft | Qt.AlignTop, self.title())

            self.__drawTriangle(painter, x, y)

            # Top Border
            headerHeight = 20
            headerRect = QRect(x, y, w, headerHeight)

            # Highlight
            painter.setBrush(QBrush(QColor(255, 255, 255, 34), Qt.SolidPattern))

            pen = QPen(Qt.NoPen)
            painter.setPen(pen)
            painter.drawRoundedRect(headerRect, 2, 2)

            # Shadow
            pen.setColor(self.palette().color(QPalette.Dark))

            if not self.isCollapsed():
                # Lower border
                pen = QPen(self.palette().color(QPalette.Dark))
                pen.setWidthF(0.8)
                painter.setPen(pen)

                offSet = headerHeight + 3
                bodyRect = QRect(x + 2, y + offSet, w - 2, h - headerHeight - 5)
                painter.fillRect(bodyRect, QColor(255, 255, 255, 7))

        if self._rolloutStyle == CollapsibleWidget.Boxed:
            if self.isCollapsed():
                arect = QRect(x + 1, y + 9, w - 1, 4)
                brect = QRect(x, y + 8, w - 1, 4)
                text = '+'
            else:
                arect = QRect(x + 1, y + 9, w - 1, h - 9)
                brect = QRect(x, y + 8, w - 1, h - 9)
                text = '-'

            # Borders
            pen = QPen(self.palette().color(QPalette.Light))
            pen.setWidthF(0.6)
            painter.setPen(pen)

            painter.drawRect(arect)

            pen.setColor(self.palette().color(QPalette.Shadow))
            painter.setPen(pen)

            painter.drawRect(brect)

            painter.setRenderHint(painter.Antialiasing, False)
            painter.setBrush(self.palette().color(QPalette.Window).darker(120))
            painter.drawRect(x + 10, y + 1, w - 20, 16)
            painter.drawText(x + 16, y + 1, w - 32, 16, Qt.AlignLeft | Qt.AlignVCenter, text)
            painter.setPen(QColor(self._setTextColor))
            painter.drawText(x + 10, y + 1, w - 20, 16, Qt.AlignCenter, self.title())

        # Expand Rect Extents
        pen = QPen(self.palette().color(QPalette.Light))
        pen.setWidthF(0.8)
        painter.setPen(pen)
        tr = self._expandCollapseRect.topRight()
        br = self._expandCollapseRect.bottomRight()
        painter.drawLine(tr, br)

        painter.end()


class DraggableWidget(CollapsibleWidget):
    '''
    DESCRIPTION:
        Widget that is collapsible as well as draggable

        :param QWidget widget: content of the collapsible item
        :param str title: label for the item
        :param QWidget parent: optional parent widget
    '''

    def __init__(self, widget, title='Draggable Widget', setTextColor=QColor(255.0, 255.0, 255.0), showExpandCollapseMenu=True, showDeleteMenu=True, parent=None):
        super(DraggableWidget, self).__init__(
            widget, title=title, setTextColor=setTextColor, showExpandCollapseMenu=showExpandCollapseMenu, showDeleteMenu=showDeleteMenu, parent=parent)

        self._setTextColor = setTextColor

        self._dragDropRect = QRect(2, 7, 10, 6)
        self._clicked = False

        self._rubberPos = None
        self._rubberBand = QRubberBand(QRubberBand.Rectangle, self)


    def mousePressEvent( self, event ):
        # Internal move
        if (event.button() == Qt.LeftButton
            and self._dragDropRect.contains(event.pos())):
            # create the pixmap
            # pixmap = QPixmap.grabWidget(self, self.rect())
            pixmap = self.grab(self.rect())

            # create the mimedata
            mimeData = QMimeData()
            mimeData.setText('ItemTitle::%s' % (self.title()))

            # create the drag
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())

            drag.exec_(Qt.MoveAction)

            self._rubberPos = event.pos()
            self._rubberBand.setGeometry(QRect(self._rubberPos, QSize()))
            self._rubberBand.show()

        super(DraggableWidget, self).mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self._rubberPos:
            pos = event.pos()
            lx, ly = self._rubberPos.x(), self._rubberPos.y()
            rx, ry = pos.x(), pos.y()
            size = QSize(abs(rx - lx), abs(ry - ly))
            self._rubberBand.setGeometry(
                QRect(QPoint(min(lx, rx), min(ly, ry)), size))


    def mouseReleaseEvent(self, event):
        self._rubberPos = None
        self._rubberBand.hide()
        super(DraggableWidget, self).mouseReleaseEvent(event)


    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(painter.Antialiasing)

        rect = self._dragDropRect

        # draw the lines
        l = rect.left() + 2
        r = rect.right() - 2
        cy = rect.center().y()

        for y in (cy - 3, cy, cy + 3):
            painter.drawLine(l, y, r, y)

        painter.end()

        super(DraggableWidget, self).paintEvent(event)


class CollapsibleListWidget(QListWidget):
    '''
    DESCRIPTION:
        Container for collapsible items
    '''
    # Item type
    #ItemClass = DraggableWidget
    ItemClass = CollapsibleWidget

    # Signals
    itemCollapsed = Signal(object)
    itemExpanded = Signal(object)
    itemsReordered = Signal()
    itemsDeleted = Signal(list)


    def __init__(self, *args, **kwargs):
        super(CollapsibleListWidget, self).__init__(*args, **kwargs)
        '''
        SelectionMode = 0 => NoSelection
        SelectionMode = 1 => SingleSelection
        SelectionMode = 2 => MultiSelection
        SelectionMode = 3 => ExtendedSelection
        SelectionMode = 4 => ContiguousSelection
        '''
        self.setSelectionMode(self.SingleSelection)

        if self.ItemClass is DraggableWidget:
            self.setAcceptDrops(True)
            self.setDragDropMode(self.InternalMove)

        self.rolloutStyle = self.ItemClass.Maya


    def emitItemsReordered(self):
        # print('Items Re-ordered')
        self.itemsReordered.emit()


    def indexOf(self, widget):
        '''
        DESCRIPTION:
            Searches for widget (not including child layouts).

            :returns: the item index containing the widget
            :rtype: QModelIndex
        '''
        for i in range(self.count()):
            if self.itemWidget(self.item(i)) is widget:
                return self.indexFromItem(self.item(i))


    def itemFromWidget(self, widget):
        '''
        DESCRIPTION:
            Searches for widget (not including child layouts).

            :returns: the item containing the widget
            :rtype: QListWidgetItem
        '''
        for i in range(self.count()):
            if self.itemWidget(self.item(i)) is widget:
                return self.item(i)


    def onItemCollapsed(self, widget, *args):
        index = self.indexOf(widget)
        if index:
            item = self.itemFromIndex(index)
            item.setSizeHint(widget.sizeHint())


    def onItemExpanded(self, widget, *args):
        index = self.indexOf(widget)
        if index:
            item = self.itemFromIndex(index)
            item.setSizeHint(widget.sizeHint())


    def onExpandAllRequested(self):
        for widget in self.findChildren(self.ItemClass):
            widget.setCollapsed(False)


    def onCollapseAllRequested(self):
        for widget in self.findChildren(self.ItemClass):
            widget.setCollapsed(True)


    def onClearAllRequested(self):
        items = self.getItems()
        self.clear()
        self.itemsDeleted.emit(items)


    def onClearSelectedRequested(self, widget, *args):
        items = [self.itemFromWidget(widget)]
        self.clearItem(widget)
        self.itemsDeleted.emit(items)


    def getItems(self):
        try:
            return [self.item(i) for i in range(self.count())]
        except:
            return []


    def clearItem(self, widget):
        index = self.indexOf(widget)
        item = self.itemFromWidget(widget)
        if index:
            self.takeItem(index.row())
        self.itemsDeleted.emit([item])


    def makeItem(self, widget, title=None, setTextColor=QColor(255.0, 255.0, 255.0), collapsed=False, showExpandCollapseMenu=True, showDeleteMenu=True, row=-1):
        item = QListWidgetItem()
        item.setData(Qt.UserRole + 1, title)

        collapsibleWidget = self.ItemClass(widget, title=title, setTextColor=setTextColor, showExpandCollapseMenu=showExpandCollapseMenu, showDeleteMenu=showDeleteMenu, parent=self)

        # Internal widget
        collapsibleWidget.setWidget(widget)
        item.setSizeHint(
            collapsibleWidget.sizeHint())

        # Style
        collapsibleWidget.setRolloutStyle(self.rolloutStyle)

        # Signals
        self.itemCollapsed.connect(partial(self.onItemCollapsed, collapsibleWidget))
        self.itemExpanded.connect(partial(self.onItemExpanded, collapsibleWidget))
        collapsibleWidget.expandAllRequested.connect(self.onExpandAllRequested)
        collapsibleWidget.collapseAllRequested.connect(self.onCollapseAllRequested)
        collapsibleWidget.clearAllRequested.connect(self.onClearAllRequested)
        collapsibleWidget.clearSelectedRequested.connect(
            partial(self.onClearSelectedRequested, collapsibleWidget))

        # Collapsed
        if collapsed:
            collapsibleWidget.setCollapsed(collapsed)

        if row < 0:
            self.addItem(item)
        else:
            self.insertItem(row, item)

        self.setItemWidget(item, collapsibleWidget)

        return item


    def dragEnterEvent(self, event):
        event.acceptProposedAction()


    def dragMoveEvent(self, event):
        event.acceptProposedAction()


    def dropEvent(self, event):
        s = event.source()
        w = s.widget()
        i = self.indexOf(s)
        r = i.row()
        row = self.indexAt(event.pos()).row()

        self.takeItem(r)
        new = self.makeItem(
            w, title=str(s.title()),
            setTextColor=s.setTextColor(),
            collapsed=s.isCollapsed(),
            row=row)

        self.emitItemsReordered()

        super(CollapsibleListWidget, self).dropEvent(event)


class Demo(QDialog):
    '''
    DESCRIPTION:
        Create a container and fill it with CollapsibleWidgets
    '''

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.setLayout(QVBoxLayout())
        widget = CollapsibleListWidget()

        widget.makeItem(self.buildFrame(), title='A #############')
        widget.makeItem(self.buildFrame(), title='B #############')
        widget.makeItem(self.buildFrame(), title='C #############')
        widget.makeItem(self.buildFrame(), title='D #############')

        self.layout().addWidget(widget)


    def buildFrame(self):
        frame = QFrame(self)
        frame.setLayout(QVBoxLayout())
        frame.layout().addWidget(QPushButton('Test'))

        return frame
