'''
DESCRIPTION:
    Various registries for use under different constraints depending on the situation.
USAGE:
    A reference to a single instance per object type is being tracked at any given time
    This provides the ability to create many widgets of different type with
    this module as well as reliably provide access to the UI instances that have
    been created.

        reg = dw.DemoDockableWidget.registry
        print(list(reg.getInstances(dw.DemoDockableWidget)))

    If you want your own registry (recommended) you can add one to your module
    very easily. That way you can segregate registries based on different needs.

    For Maya workspace widgets in particular, it's recommended you maintain a reference (not a weak ref)
    so using SingleItemRegistry can be used for that.

    A single registry object can keep track of many widgets

        class MyWidget(QtWidget):
            registry = SingleItemRegistry

            def __init__(self, parent=None):
                super(MyWidget, self).__init__(parent=parent)

                # Register my widget
                self.registry.register(self)
'''

import pprint

from collections import defaultdict
import weakref


DEBUG = False


class SingleItemRegistry():
    '''
    DESCRIPTION:
        For cases where it is desirable to maintain a registry
        that holds a single instance for each object type at any given time.

        Note that when a weakref reference can be implemented safely,
        WeakRefRegistry should be used instead.

        This class aims to fulfill object registry needs where
        multiple inheritance or use of mixin classes would be problematic
    '''
    _registry = defaultdict(list)


    @classmethod
    def getInstance(cls, obj):
        if obj in cls._registry and len(cls._registry[obj]):
            return cls._registry[obj][0]


    @classmethod
    def getInstances(cls, obj):
        return cls._registry.get(obj, [])


    @classmethod
    def register(cls, inst):
        '''Return any items that were forced to deregister'''
        popped = cls.deregister(inst)
        cls._registry[inst.__class__].append(inst)
        return popped


    @classmethod
    def deregister(cls, inst):
        '''Remove items from the registry'''
        if inst.__class__ in cls._registry:
            return cls._registry.pop(inst.__class__)


class WeakRefRegistryMixin(object):
    '''
    DESCRIPTION:
        Simple registry mixin to use with any class, enabling access to
        the class instances via the class itself.

    EXAMPLES::

        >>> class X(WeakRefRegistryMixin):
        ...     def __init__(self, name):
        ...         super(X, self).__init__()
        ...         self.name = name

        >>> class Y(object):
        ...     def spam(self, x, y):
        ...         return x + y

        >>> class Z(Y, WeakRefRegistryMixin):
        ...     def __init__(self, name):
        ...         # it will work in this instance but
        ...         # super does not work very nicely with mixins
        ...         # and multiple inheritance
        ...         # super(Z, self).__init__()
        ...         Y.__init__(self)
        ...         WeakRefRegistryMixin.__init__(self)
        ...         self.name = name

        >>> x = X('x') # doctest: +ELLIPSIS
        <weakref at ...; to 'X' at ...>

        >>> for r in X.getInstances():
        ...     print(r.name)
        <class '__main__.X'>
        x

        >>> z = Z('z') # doctest: +ELLIPSIS
        <weakref at ...; to 'Z' at ...>

        >>> for _r in Z.getInstances():
        ...     print(_r.name)
        <class '__main__.Z'>
        z

        >>> zz = Z('zz') # doctest: +ELLIPSIS
        <weakref at ...; to 'Z' at ...>

        >>> for __r in Z.getInstances():
        ...     print(__r.name)
        <class '__main__.Z'>
        z
        zz
    '''
    __refs__ = defaultdict(list)


    def __init__(self):
        ref = weakref.ref(self)
        self.__refs__[self.__class__].append(ref)
        if DEBUG:
            print(repr(ref))
            #pprint.pprint(self.__refs__)


    @classmethod
    def getInstances(cls):
        if DEBUG:
            print(repr(cls))
        for inst_ref in cls.__refs__[cls]:
            inst = inst_ref()
            if inst is not None:
                yield inst


class WeakRefRegistry():
    '''
    DESCRIPTION:
        Each item of which is a weakref reference
        This class aims to fulfill object registry needs where
        multiple inheritance or use of mixin classes would be problematic
    '''
    _registry = defaultdict(list)


    @classmethod
    def getInstances(cls, obj):
        if DEBUG:
            print(repr(obj))
        for inst_ref in cls._registry[obj]:
            # Attempt to dereference, if no obj exists returns None
            inst = inst_ref()
            if inst is not None:
                yield inst


    @classmethod
    def register(cls, inst):
        ref = weakref.ref(inst)
        cls._registry[inst.__class__].append(ref)
        if DEBUG:
            print(repr(ref))


class WidgetType1(object):
    registry = WeakRefRegistry

    def __init__(self, parent=None):
        self.parent = parent
        self.registry.register(self)


    def __del__(self):
        if DEBUG:
            print('{} Being deleted'.format(self))


class WidgetType2(object):
    '''
    EXAMPLES:
        # Create some widgets of different types
        >>> widgetType1a = WidgetType1(parent='foo') # doctest: +ELLIPSIS
        <weakref at ...; to 'WidgetType1' at ...>

        >>> widgetType1b = WidgetType1(parent='bar') # doctest: +ELLIPSIS
        <weakref at ...; to 'WidgetType1' at ...>

        >>> widgetType2a = WidgetType2(parent='eggs') # doctest: +ELLIPSIS
        <weakref at ...; to 'WidgetType2' at ...>

        >>> widgetType2b = WidgetType2(parent='bacon') # doctest: +ELLIPSIS
        <weakref at ...; to 'WidgetType2' at ...>

        # Access the widget registry
        # Notice the 2 widget types have the same registry
        >>> reg = widgetType1a.registry

        # Query instances in the registry by type
        >>> print(list(reg.getInstances(WidgetType1))) # doctest: +ELLIPSIS
        <class '__main__.WidgetType1'>
        [<__main__.WidgetType1 object at ...>, <__main__.WidgetType1 object at ...>]

        >>> print(list(reg.getInstances(WidgetType2))) # doctest: +ELLIPSIS
        <class '__main__.WidgetType2'>
        [<__main__.WidgetType2 object at ...>, <__main__.WidgetType2 object at ...>]

        # Deleting and Setting to None reliably decrease the reference count
        # weakref eliminates reference cycles which impede garbage collection
        >>> del(widgetType1a) # doctest: +ELLIPSIS
        <__main__.WidgetType1 object at ...> Being deleted

        >>> widgetType1b = None # doctest: +ELLIPSIS
        <__main__.WidgetType1 object at ...> Being deleted

        >>> print(list(reg.getInstances(WidgetType1)))
        <class '__main__.WidgetType1'>
        []

        >>> print(list(reg.getInstances(WidgetType2))) # doctest: +ELLIPSIS
        <class '__main__.WidgetType2'>
        [<__main__.WidgetType2 object at ...>, <__main__.WidgetType2 object at ...>]
    '''

    registry = WeakRefRegistry


    def __init__(self, parent=None):
        self.parent = parent
        self.registry.register(self)


    def __del__(self):
        if DEBUG:
            print('{} Being deleted'.format(self))


if __name__ == '__main__':
    '''
    verbose: python widgetRegistry.py -v
    '''
    import doctest
    DEBUG = True
    doctest.testmod()
