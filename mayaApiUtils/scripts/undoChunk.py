import maya.cmds as cmds


class UndoChunk(object):
    '''
    DESCRIPTION:
        This class tries to manage undo chunks in a sensible way.  This is
        managed by tracking three variables:

        _chunkOpen (shared for class) - whether or not a chunk is open
        _chunkCount (shared for class) - how many chunks are currently open
        _instanceOpen (specific to instance) - is this instance open
    '''

    _chunkCount = 0
    _chunkOpen = False

    def __init__(self):
        self._instanceOpen = False

    def openChunk(self):
        result = False
        if not self._chunkCount:
            cmds.undoInfo(openChunk=True)
            self._chunkOpen = True
            result = True

        self._instanceOpen = True
        self._chunkCount = self._chunkCount + 1

        return result

    def closeChunk(self):
        result = False
        if self._instanceOpen:
            self._chunkCount = self._chunkCount - 1

            if not self._chunkCount and self._chunkOpen:
                cmds.undoInfo(closeChunk=True)
                self._chunkOpen = False
                result = True

        return result

    def __del__(self):
        if self._instanceOpen and not self._chunkCount and self._chunkOpen:
            cmds.undoInfo(closeChunk=True)


def executeAsUndoChunk(item, *args, **kwargs):
    try:
        chunk = UndoChunk()
        chunk.openChunk()

        result = item(*args, **kwargs)

    finally:
        chunk.closeChunk()

    return result


def undoable(function):
    '''
    DESCRIPTION:
        A decorator that will make commands undoable in maya
    '''
    def decoratorCode(*args, **kwargs):
        try:
            chunk = UndoChunk()
            chunk.openChunk()

            functionReturn = function(*args, **kwargs)

        finally:
            chunk.closeChunk()

        return functionReturn

    return decoratorCode


def repeatable(name):
    '''
    DESCRIPTION:
        A decorator that will make commands repeatable in maya
    '''
    def innerRepeatable(function):
        def decoratorCode(*args, **kwargs):
            functionReturn = None
            argString = ''
            if args:
                for each in args:
                    argString += str(each)+', '

            if kwargs:
                for key, item in kwargs.iteritems():
                    argString += str(key)+'='+str(item)+', '

            functionReturn = function(*args, **kwargs)
            try:
                cmds.repeatLast(addCommand='python(\'import %s; %s.%s(%s)\')' % (name, name, function.__name__, argString),
                              addCommandLabel=function.__name__)
            except:
                pass

            return functionReturn

        return decoratorCode

    return innerRepeatable
