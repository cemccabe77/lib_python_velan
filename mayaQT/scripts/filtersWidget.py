'''
DESCRIPTION:
    Maya filters widget
'''
import os
import fnmatch
import time

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


class SearchFiltersFrame(QFrame):
    '''
    DESCRIPTION:
        a custom ui that implements multiple filters. The relationship between
        each filter can be 'and' or 'or'.
    SIGNALS:
        filterResultChanged: emitted when filter result changes. The list of filtered
                              result is passed
        filterResultIndicesChanged: emitted when filter result changes. The list of filtered
                                     result indices is passed
    ATTRIBUTES:
        filterResults: results from all the filters, in the format of a list of strings
        filterResultIndices: results from all the filters, in the format of a list of indices
    '''
    __filterFrames = []
    __inputList = []
    __widgetDict = {}
    __filterResults = []
    __fliterResultIndices = []
    __wildcardRequired = True
    filterResultChanged = Signal(list)
    filterResultIndicesChanged = Signal(list)


    def __init__(self, parent, inputList=[], wildcardRequired=True,
                 *args, **kwargs):
        '''
        DESCRIPTION:
            init function
        ARGUMENTS:
            parent: parent widget
            inputList: a list of strings the widget filters on
            wildcardRequired: if True, wild card is required to do pattern match.
                               for example, 'test' only matches 'test', not 'testA'
                               or 'a test'.
        '''
        super(SearchFiltersFrame, self).__init__(parent, *args, **kwargs)
        self.__filterFrames = []
        self.__inputList = inputList
        self.__widgetDict = {}
        self.__filterResults = []
        self.__filterResultIndices = []
        self.__wildcardRequired = wildcardRequired
        self.__setupUi()


    def updateInputList(self, inputList):
        '''
        DESCRIPTION:
            update the inputList that all the filters operate on
        '''
        ####medwards##
        #start = time.perf_counter()

        #speed optimization
        identical = True
        if len(self.__inputList) != len(inputList):
            identical = False
        else:
            for i, j in zip(self.__inputList, inputList):
                if i != j:
                    identical = False
                    break

        if not identical:
            self.__inputList = inputList
            self.__updateFilterResult()

        ####medwards##end = time.perf_counter()
        #print('self.guideSearchFiltersFrame[mode].updateInputList(guides)')
        #print(end-start)


    @property
    def filterResults(self):
        '''
        DESCRIPTION:
            results from all the filters, in the format of a list of strings
        '''
        return self.__filterResults


    @property
    def filterResultIndices(self):
        '''
        DESCRIPTION:
            results from all the filters, in the format of a list of indices
        '''
        return self.__filterResultIndices


    @property
    def wildcardRequired(self):
        '''
        DESCRIPTION:
            if True, wild card is required to do pattern match.
            for example, 'test' only matches 'test', not 'testA' or 'a test'.
        '''
        return self.__wildcardRequired


    @wildcardRequired.setter
    def wildcardRequired(self, value):
        self.__wildcardRequired = value
        self.__updateFilterResult()


    def __setupUi(self):
        '''
        DESCRIPTION:
            set up the ui
        '''
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSizeConstraint(QLayout.SetMaximumSize)
        self.verticalLayout.setSpacing(0)
        self.__addFilterFrame()


    def __addFilterFrame(self):
        '''
        DESCRIPTION:
            internal function to add a filter frame
        '''
        frame = QFrame(self)
        frame.setFrameShape(QFrame.NoFrame)
        frame.setFrameShadow(QFrame.Raised)

        horizontalLayout = QHBoxLayout(frame)
        horizontalLayout.setContentsMargins(0, 0, 0, 0)

        opComboBox = QComboBox(frame)
        opComboBox.addItem('And')
        opComboBox.addItem('Or')
        if not self.__filterFrames:
            opComboBox.setEnabled(False)
        horizontalLayout.addWidget(opComboBox)

        negateComboBox = QComboBox(frame)
        negateComboBox.addItem('')
        negateComboBox.addItem('Not')
        horizontalLayout.addWidget(negateComboBox)

        lineEdit = QLineEdit(frame)
        horizontalLayout.addWidget(lineEdit)

        dirName = os.path.dirname(__file__)

        addButton = QToolButton(frame)
        addButton.setAutoRaise(True)
        icon = QIcon()
        ####TODO##
        imgPath = os.path.join(dirName, '../icons/plus.png')
        icon.addPixmap(QPixmap(imgPath),
                       QIcon.Normal, QIcon.Off)
        addButton.setIcon(icon)
        horizontalLayout.addWidget(addButton)

        removeButton = QToolButton(frame)
        removeButton.setAutoRaise(True)
        icon = QIcon()
        ####TODO##
        imgPath = os.path.join(dirName, '../icons/minus.png')
        icon.addPixmap(QPixmap(imgPath),
                       QIcon.Normal, QIcon.Off)
        removeButton.setIcon(icon)
        horizontalLayout.addWidget(removeButton)
        if not self.__filterFrames:
            removeButton.setEnabled(False)
        else:
            for value in self.__widgetDict.values():
                rButton = value[-1]
                rButton.setEnabled(True)

        self.verticalLayout.addWidget(frame)
        self.__filterFrames.append(frame)
        self.__widgetDict[frame] = (opComboBox, negateComboBox,
                                     lineEdit, addButton, removeButton)
        opComboBox.currentIndexChanged.connect(self.__updateFilterResult)
        negateComboBox.currentIndexChanged.connect(self.__updateFilterResult)
        lineEdit.editingFinished.connect(self.__updateFilterResult)
        addButton.clicked.connect(self.__addFilterFrame)
        ####medwards####
        ####removeButton.clicked.connect(self.__removeFilterFrame)
        removeButton.clicked.connect(self.removeFilterFrame)

        self.adjustSize()


    def __updateFilterResult(self):
        '''
        DESCRIPTION:
            update the filter result
        '''
        if not self.__inputList:
            return

        indexDict = {}
        for frame in self.__filterFrames:
            index = self.verticalLayout.indexOf(frame)
            indexDict[index] = self.__widgetDict[frame]

        indices = indexDict.keys()
        ####TODO##
        #indices.sort()
        indices = sorted(indices)

        start = True
        results = []
        resultIndices = []
        operated = False
        for index in indices:
            opComboBox, negateComboBox, lineEdit, addButton, removeButton = indexDict[index]
            if start:
                op = 'Or'
                start = False
            else:
                op = str(opComboBox.currentText())

            if str(negateComboBox.currentText()) == 'Not':
                negate = True
            else:
                negate = False
            pattern = str(lineEdit.text())
            pattern = pattern.strip()
            pattern = pattern.rstrip()
            if not pattern:
                continue
            if not self.__wildcardRequired:
                if not pattern.startswith('*'):
                    pattern = '*' + pattern
                if not pattern.endswith('*'):
                    pattern = pattern + '*'

            operated = True
            if op == 'Or':
                tempList = self.__inputList
                tempListIndices = range(len(self.__inputList))
            else:
                tempList = results[:]
                tempListIndices = resultIndices[:]
                results = []
                resultIndices = []

            for itemIndex, item in zip(tempListIndices, tempList):

                match = fnmatch.fnmatch(item, pattern)
                if negate ^ match:
                    if itemIndex not in resultIndices:
                        results.append(item)
                        resultIndices.append(itemIndex)


        if not operated:
            self.__filterResults = self.__inputList
            self.__filterResultIndices = range(len(self.__inputList))
            self.filterResultChanged.emit(self.__filterResults)
            self.filterResultIndicesChanged.emit(self.__filterResultIndices)
            return

        tempList = zip(results, resultIndices)
        ####TODO##
        #tempList.sort(key=lambda x: x[1])
        tempList = sorted(tempList, key=lambda x: x[1])

        filterResults = [i[0] for i in tempList]
        filterResultIndices = [i[1] for i in tempList]

        needUpdate = False
        if len(self.__filterResults) != len(filterResults):
            needUpdate = True
        else:
            for i, j in zip(self.__filterResults, filterResults):
                if i != j:
                    needUpdate = True
                    break
        if len(self.__filterResultIndices) != len(filterResultIndices):
            needUpdate = True
        else:
            for i, j in zip(self.__filterResultIndices, filterResultIndices):
                if i != j:
                    needUpdate = True
                    break
        if needUpdate:
            self.__filterResults = filterResults
            self.__filterResultIndices = filterResultIndices
            self.filterResultChanged.emit(self.__filterResults)
            self.filterResultIndicesChanged.emit(self.__filterResultIndices)


    def __removeFilterFrame(self):
        '''
        DESCRIPTION:
            removes a filter frame
        '''
        sender = self.sender()
        parentFrame = sender.parent()
        siblings = parentFrame.children()
        layout = parentFrame.layout()
        for widget in siblings:
            if layout == widget:
                continue
            layout.removeWidget(widget)
            widget.deleteLater()
            widget = None

        del self.__widgetDict[parentFrame]
        self.__filterFrames.remove(parentFrame)

        self.verticalLayout.removeWidget(parentFrame)
        parentFrame.deleteLater()
        parentFrame = None

        if len(self.__widgetDict) == 1:
            opComboBox, negateComboBox, lineEdit, addButton, removeButton = self.__widgetDict.values()[0]
            opComboBox.setEnabled(False)
            removeButton.setEnabled(False)

        for frame in self.__filterFrames:
            index = self.verticalLayout.indexOf(frame)
            if index == 0:
                self.__widgetDict[frame][0].setEnabled(False)
            else:
                self.__widgetDict[frame][0].setEnabled(True)

        self.__updateFilterResult()
        self.adjustSize()


    def removeFilterFrame(self):
        '''
        DESCRIPTION:
            removes a filter frame
        '''
        sender = self.sender()
        parentFrame = sender.parent()
        siblings = parentFrame.children()
        layout = parentFrame.layout()
        for widget in siblings:
            if layout == widget:
                continue
            layout.removeWidget(widget)
            widget.deleteLater()
            widget = None

        del self.__widgetDict[parentFrame]
        self.__filterFrames.remove(parentFrame)

        self.verticalLayout.removeWidget(parentFrame)
        parentFrame.deleteLater()
        parentFrame = None

        if len(list(self.__widgetDict)) == 1:
            opComboBox, negateComboBox, lineEdit, addButton, removeButton = list(self.__widgetDict.values())[0]
            opComboBox.setEnabled(False)
            removeButton.setEnabled(False)

        for frame in self.__filterFrames:
            index = self.verticalLayout.indexOf(frame)
            if index == 0:
                self.__widgetDict[frame][0].setEnabled(False)
            else:
                self.__widgetDict[frame][0].setEnabled(True)

        self.__updateFilterResult()
        self.adjustSize()
