from dataclasses import fields, dataclass, Field
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
    cls_dict['__slots__'] = tuple(fields(cls))
    for f in fields(cls).values():
        # Remove our attributes. They'll still be available in _MARKER.
        cls_dict.pop(f.name, None)
    # Remove __dict__ itself.
    cls_dict.pop('__dict__', None)
    # And finally create the class.
    qualname = getattr(cls, '__qualname__', None)
    cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)
    if qualname is not None:
        cls.__qualname__ = qualname
    return cls


def make_dataclass(cls_name: str,
                   fields: Iterable[Union[Tuple[str, Type], Tuple[str, Type, Field]]],
                   bases=(),
                   ns=None):
    anns = OrderedDict((name, tp) for name, tp, *_ in fields)
    ns = ns or {}
    ns['__annotations__'] = anns
    for item in fields:
        if len(item) == 3:
            name, tp, spec = item
            ns[name] = spec
    cls = type(cls_name, bases, ns)
    return dataclass(cls)
