# TODO:

#  what exception to raise when non-default follows default? currently
#  ValueError

#  what to do if a user specifies a function we're going to overwrite,
#  like __init__? error? overwrite it?

#  use typing.get_type_hints() instead of accessing __annotations__
#  directly? recommended by PEP 526, but that's importing a lot just
#  to get at __annotations__

# if needed for efficiency, compute self_tuple and other_tuple just once, and pass them around

import collections

__all__ = ['dataclass', 'field', 'make_class']

_MISSING = object()
_MARKER = '__dataclass_fields__'
_SELF_NAME = '_self'
_OTHER_NAME = '_other'


class field:
    __slots__ = ('name',
                 'default',
                 'repr',
                 'hash',
                 'init',
                 'cmp',
                 )
    def __init__(self, *, default=_MISSING, repr=True, hash=True, init=True,
                 cmp=True):
        # Initialize name to None.  It's filled in later, when
        #  scanning through the class's fields.  We don't know it when
        #  the field is being initialized.
        self.name = None
        self.default = default
        self.repr = repr
        self.hash = hash
        self.init = init
        self.cmp = cmp

    # XXX: currently for testing. either complete this, or delete it
    def __repr__(self):
        return f'field(name={self.name!r},default={"_MISSING" if self.default is _MISSING else self.default!r})'


def _tuple_str(obj_name, fields):
    # Return a string representing each field of obj_name as a tuple
    #  member. So, if fields is ['x', 'y'] and obj_name is "self",
    #  return "(self.x,self.y)".

    #Special case for the 0-tuple
    if len(fields) == 0:
        return '()'
    # Note the trailing comma, needed for 1-tuple
    return f'({",".join([f"{obj_name}.{f.name}" for f in fields])},)'


def _create_fn(name, args, body, locals=None):
    # Note that we mutate locals when exec() is called. Caller beware!
    if locals is None:
        locals = {}
    args = ','.join(args)
    body = '\n'.join(f' {b}' for b in body)
    txt = f'def {name}({args}):\n{body}'
    #print(txt)
    exec(txt, None, locals)
    return locals[name]


def _field_init(info):
    # Return the text of the line in __init__ that will initialize
    #  this field.
    if info.default == _MISSING:
        # There's no default, just use the value from our parameter list.
        return f'{_SELF_NAME}.{info.name} = {info.name}'

    if isinstance(info.default, (list, dict, set)):
        # We're a type we know how to copy. If no default is given,
        #  copy the default.
        return (f'{_SELF_NAME}.{info.name} = '
                f'{_SELF_NAME}.__class__.{info.name}.copy() '
                f'if {info.name} is {_SELF_NAME}.__class__.{info.name} '
                f'else {info.name}')

    # XXX Is our default a factory function?
    return f'{_SELF_NAME}.{info.name} = {info.name}'


def _init(fields):
    # Make sure we don't have fields without defaults following fields
    #  with defaults.  This actually would be caught when exec-ing the
    #  function source code, but catching it here gives a better error
    #  message.
    seen_default = False
    for f in fields:
        if f.default is not _MISSING:
            seen_default = True
        else:
            if seen_default:
                raise ValueError(f'non-default argument {f.name} '
                                 'follows default argument')

    args = [_SELF_NAME] + [(f.name if f.default is _MISSING
                            else f"{f.name}=_def_{f.name}") for f in fields]
    body_lines = [_field_init(f) for f in fields]
    if len(body_lines) == 0:
        body_lines = ['pass']

    # locals needs to contain the defaults values: supply them.
    locals = {f'_def_{f.name}': f.default for f in fields
                                if f.default is not _MISSING}
    return _create_fn('__init__',
                      args,
                      body_lines,
                      locals)


def _repr(fields):
    return _create_fn('__repr__',
                      [f'{_SELF_NAME}'],
                      [f'return {_SELF_NAME}.__class__.__name__ + f"(' + ','.join([f"{f.name}={{{_SELF_NAME}.{f.name}!r}}" for f in fields]) + ')"'],
                      )


def _create_cmp_fn(name, op, fields):
    self_tuple = _tuple_str(_SELF_NAME, fields)
    other_tuple = _tuple_str(_OTHER_NAME, fields)
    return _create_fn(name,
                      [_SELF_NAME, _OTHER_NAME],
                      [f'if {_OTHER_NAME}.__class__ is '
                          f'{_SELF_NAME}.__class__:',
                       f'    return {self_tuple}{op}{other_tuple}',
                        'return NotImplemented'],
                      )


def _eq(fields):
    return _create_cmp_fn('__eq__', '==', fields)


def _ne():
    # __ne__ is slightly different, so use a different pattern.
    return _create_fn('__ne__',
                      [_SELF_NAME, _OTHER_NAME],
                      [f'result = {_SELF_NAME}.__eq__({_OTHER_NAME})',
                        'return NotImplemented if result is NotImplemented '
                            'else not result',
                       ],
                      )


def _lt(fields):
    return _create_cmp_fn('__lt__', '<',  fields)


def _le(fields):
    return _create_cmp_fn('__le__', '<=', fields)


def _gt(fields):
    return _create_cmp_fn('__gt__', '>',  fields)


def _ge(fields):
    return _create_cmp_fn('__ge__', '>=', fields)


def _hash(fields):
    self_tuple = _tuple_str(_SELF_NAME, fields)
    return _create_fn('__hash__',
                      [_SELF_NAME],
                      [f'return hash({self_tuple})'])


def _find_fields(cls):
    # Return a list tuples of tuples of (name, field()), in order, for
    #  this class (and no subclasses).  Fields are found from
    #  __annotations__.  Default values are from class attributes, if
    #  a field has a default.

    # Note that the type (as retrieved from __annotations__) is only
    #  used to identify fields.  The actual value of the type
    #  annotation is not saved anywhere.  It can be retrieved from
    #  __annotations__ if needed.

    # XXX: are __annotations__ known to ordered? I don't think so.
    #  Maybe iterate over class members (which are in order) and only
    #  consider ones that are in __annotations__?

    annotations = getattr(cls, '__annotations__', {})

    results = []
    for name, type_ in annotations.items():
        # If the default value isn't derived from field, then it's
        # only a normal default value.  Convert it to a field().
        default = getattr(cls, name, _MISSING)
        if not isinstance(default, field):
            default = field(default=default)
        results.append((name, default))
    return results


class Factory:
    pass


def _process_class(cls, repr, cmp, hash, init, slots, frozen):
    # Use an OrderedDict because:
    #  - Order matters!
    #  - Derived class fields overwrite base class fields.
    fields = collections.OrderedDict()

    # Find our base classes in reverse MRO order, and exclude
    #  ourselves.  In reversed order so that more derived classes
    #  overrides earlier field definitions in base classes.
    bases = [b for b in cls.__mro__ if not b is cls]

    for b in bases:
        # Only process classes marked with our decorator.
        if hasattr(b, _MARKER):
            # This is one of our base classes, where we've already
            #  set _MARKER with a list of fields.  Add them to the
            #  fields we're building up.  already processed.
            for f in getattr(b, _MARKER):
                fields[f.name] = f

    # Now process our class.
    for name, info in _find_fields(cls):
        fields[name] = info

        # For fields defined in our class, set the name, which we
        #  don't know until now.
        info.name = name

        # Field validations for fields directly on our class.
        #  This is delayed until now, instead of in the field()
        #  constructor, since only here do we know the field name,
        #  which allows better error reporting.

        # If init=False, we must have a default value.  Otherwise,
        # how would it get initialized?
        if not info.init and info.default == _MISSING:
            raise ValueError(f'field {name} has init=False, but '
                             'has no default value')

        # If the class attribute (which is the default value for
        #  this field) exists and is of type 'field', replace it
        #  with the real default.  This is so that normal class
        #  introspection sees a real default value.
        if isinstance(getattr(cls, name, None), field):
            setattr(cls, name, info.default)

    # We've de-duped and have the fields in order, so we no longer
    #  need a dict of them.  Convert to a list of just the values.
    fields = list(fields.values())

    # Remember the total set of fields on our class (including
    #  bases).
    setattr(cls, _MARKER, fields)

    if init:
        cls.__init__ = _init(list(filter(lambda f: f.init, fields)))
    if repr:
        cls.__repr__ = _repr(list(filter(lambda f: f.repr, fields)))
    cls.__hash__ = _hash(list(filter(lambda f: f.hash, fields)))

    if cmp:
        # Create comparison functions.
        cmp_fields = list(filter(lambda f: f.cmp, fields))
        cls.__eq__ = _eq(cmp_fields)
        cls.__ne__ = _ne()
        cls.__lt__ = _lt(cmp_fields)
        cls.__le__ = _le(cmp_fields)
        cls.__gt__ = _gt(cmp_fields)
        cls.__ge__ = _ge(cmp_fields)

    return cls


def dataclass(_cls=None, *, repr=True, cmp=True, hash=None, init=True,
               slots=False, frozen=False):
    def wrap(cls):
        return _process_class(cls, repr, cmp, hash, init, slots, frozen)

    # See if we're being called as @dataclass or @dataclass().
    if _cls is None:
        # We're called as @dataclass()
        return wrap

    # We're called as @dataclass, with a class
    return wrap(_cls)


def make_class(cls_name, fields, *, bases=None, repr=True, cmp=True,
               hash=None, init=True, slots=False, frozen=False):
    # fields is a list of (name, type, field)
    if bases is None:
        bases = (object,)

    if isinstance(fields, str):
        # This is for the case of using 'x y' as a shortcut for
        #  ['x', 'y'].
        fields = fields.replace(',', ' ').split()

    # Normalize the fields.  The user can supply:
    #  - just a name
    #  - tuple of (name, default)
    #  - tuple of (name, field())
    #  - tuple of (name,
    fields1 = {}  # XXX needs to be an orderedict
    annotations = {}  # XXX also ordered?
    for v in fields:
        type_ = default = _MISSING
        if len(v) == 3:
            name, type_, default = v
        elif len(v) == 2:
            name, type_ = v
        else:
            name = v

        if type_ is _MISSING:
            pass

        # If the default value isn't derived from field, then it's
        # only a normal default value.  Convert it to a field().
        if not isinstance(default, field):
            f = field(default=default)
        else:
            f = default

        f.name = name

        fields1[f.name] = f
        annotations[f.name] = type_

    fields1['__annotations__'] = annotations
    return _process_class(type(cls_name, bases, fields1),
                          repr, cmp, hash, init, slots, frozen)
