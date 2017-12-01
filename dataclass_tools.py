import dataclasses
from typing import Iterable, Union, Tuple, Type
from collections import OrderedDict

def add_slots(cls):
    # Need to create a new class, since we can't set __slots__
    #  after a class has been created.

    # Make sure __slots__ isn't already set.
    if '__slots__' in cls.__dict__:
        raise TypeError(f'{cls.__name__} already specifies __slots__')

    # Create a new dict for our new class.
    cls_dict = dict(cls.__dict__)
    flds = tuple(dataclasses.fields(cls))
    cls_dict['__slots__'] = flds
    for field_name in flds:
        # Remove our attributes, if present. They'll still be
        #  available in _MARKER.
        cls_dict.pop(field_name, None)
    # Remove __dict__ itself.
    cls_dict.pop('__dict__', None)
    # And finally create the class.
    qualname = getattr(cls, '__qualname__', None)
    cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)
    if qualname is not None:
        cls.__qualname__ = qualname
    return cls


def isdataclass(obj):
    """Returns True for dataclass classes and instances."""
    try:
        dataclasses.fields(obj)
        return True
    except TypeError:
        return False
