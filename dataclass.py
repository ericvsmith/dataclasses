# TODO:

#  what exception to raise when non-default follows default? currently
#  ValueError

#  what to do if a user specifies a function we're going to overwrite,
#  like __init__? error? overwrite it?

#  use typing.get_type_hints() instead of accessing __annotations__
#  directly? recommended by PEP 526, but that's importing a lot just
#  to get at __annotations__

# is __annotations__ guaranteed to be an ordered mapping?

# if needed for efficiency, compute self_tuple and other_tuple just once, and pass them around

import collections

__all__ = ['dataclass', 'field', 'make_class']

_MISSING = object()
_MARKER = '__dataclass_fields__'

# Use '_self' instead of 'self' so that fields can be named 'self'.
_SELF = '_self'
_OTHER = '_other'


# This is used for both static field specs (in a class statement), and
#  in dynamic class creation (using make_class).  In the static case,
#  name and type must not be specified (they're inferred from
#  cls.__dict__ and __annocations__, respectively).  In the dynamic
#  case, they must be specified.
# In either case, when cls._MARKER is filled in with a list of
#  fields(), the name and type fields will have been populated.
class field:
    __slots__ = ('name',
                 'type',
                 'default',
                 'repr',
                 'hash',
                 'init',
                 'cmp',
                 )
    def __init__(self, name=None, type=None, *, default=_MISSING, repr=True,
                 hash=None, init=True, cmp=True):
        self.name = name
        self.type = type
        self.default = default
        self.repr = repr
        self.hash = hash
        self.init = init
        self.cmp = cmp

    # XXX: currently for testing. either complete this, or delete it
    def __repr__(self):
        return f'''field(name={self.name!r},default={"_MISSING"
                if self.default is _MISSING else self.default!r})'''


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
        return f'{_SELF}.{info.name} = {info.name}'

    if isinstance(info.default, (list, dict, set)):
        # We're a type we know how to copy. If no default is given,
        #  copy the default.
        return (f'{_SELF}.{info.name} = '
                f'{_SELF}.__class__.{info.name}.copy() '
                f'if {info.name} is {_SELF}.__class__.{info.name} '
                f'else {info.name}')

    # XXX Is our default a factory function?
    return f'{_SELF}.{info.name} = {info.name}'


def _init(fields):
    # Make sure we don't have fields without defaults following fields
    #  with defaults.  This actually would be caught when exec-ing the
    #  function source code, but catching it here gives a better error
    #  message, and future-proofs us in case we build up function using
    #  ast.
    seen_default = False
    for f in fields:
        if f.default is not _MISSING:
            seen_default = True
        else:
            if seen_default:
                raise ValueError(f'non-default argument {f.name} '
                                 'follows default argument')

    args = [_SELF] + [(f.name if f.default is _MISSING
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
                      [_SELF],
                      [f'return {_SELF}.__class__.__name__ + f"(' +
                         ','.join([f"{f.name}={{{_SELF}.{f.name}!r}}"
                                   for f in fields]) +
                         ')"'],
                      )


def _create_cmp_fn(name, op, fields):
    self_tuple = _tuple_str(_SELF, fields)
    other_tuple = _tuple_str(_OTHER, fields)
    return _create_fn(name,
                      [_SELF, _OTHER],
                      [f'if {_OTHER}.__class__ is {_SELF}.__class__:',
                       f'    return {self_tuple}{op}{other_tuple}',
                        'return NotImplemented'],
                      )


def _eq(fields):
    return _create_cmp_fn('__eq__', '==', fields)


def _ne():
    # __ne__ is slightly different, so use a different pattern.
    return _create_fn('__ne__',
                      [_SELF, _OTHER],
                      [f'result = {_SELF}.__eq__({_OTHER})',
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
    self_tuple = _tuple_str(_SELF, fields)
    return _create_fn('__hash__',
                      [_SELF],
                      [f'return hash({self_tuple})'])


def _find_fields(cls):
    # Return a list tuples of of (name, type, field()), in order, for
    #  this class (and no subclasses).  Fields are found from
    #  __annotations__.  Default values are from class attributes, if
    #  a field has a default.  If the default value is a field(), then
    #  it contains additional info beyond (and possibly including) the
    #  actual default value.

    # XXX: are __annotations__ known to ordered? I don't think so.
    #  Maybe iterate over class members (which are in order) and only
    #  consider ones that are in __annotations__?

    annotations = getattr(cls, '__annotations__', {})

    results = []
    for name, type in annotations.items():
        # If the default value isn't derived from field, then it's
        # only a normal default value.  Convert it to a field().
        default = getattr(cls, name, _MISSING)
        if isinstance(default, field):
            f = default
        else:
            f = field(default=default)
        results.append((name, type, f))
    return results


class Factory:
    pass


def _process_class(cls, repr, cmp, hash, init, slots, frozen, dynamic):
    # Use an OrderedDict because:
    #  - Order matters!
    #  - Derived class fields overwrite base class fields.
    fields = collections.OrderedDict()

    # Find our base classes in reverse MRO order, and exclude
    #  ourselves.  In reversed order so that more derived classes
    #  overrides earlier field definitions in base classes.
    for b in [b for b in cls.__mro__ if not b is cls]:
        # Only process classes marked with our decorator.
        if hasattr(b, _MARKER):
            # This is one of our base classes, where we've already
            #  set _MARKER with a list of fields.  Add them to the
            #  fields we're building up.
            for f in getattr(b, _MARKER):
                fields[f.name] = f

    # Now process our class.
    for name, type, f in _find_fields(cls):
        # The checks for dynamic=True happen in make_class(), since it
        #  can generate better error message for missing f.name.
        if not dynamic:
            # The name and type must not be filled in: we grab them
            #  from the annotations.
            if f.name is not None or f.type is not None:
                raise ValueError(f'cannot specify name or type for {name!r}')

            # For fields defined in our class, set the name and type,
            #  which we don't know until now.
            f.name = name
            f.type = type

        fields[name] = f

        # Validations for fields directly on our class.  This is
        #  delayed until now, instead of in the field() constructor,
        #  since only here do we know the field name, which allows
        #  better error reporting.

        # If init=False, we must have a default value.  Otherwise,
        # how would it get initialized?
        if not f.init and f.default is _MISSING:
            raise ValueError(f'field {name} has init=False, but '
                             'has no default value')

        # If the class attribute (which is the default value for
        #  this field) exists and is of type 'field', replace it
        #  with the real default.  This is so that normal class
        #  introspection sees a real default value.
        if isinstance(getattr(cls, name, None), field):
            if f.default is _MISSING:
                # If there's no default, delete the class attribute.
                #  This happens if we specify field(repr=False), for
                #  example.  The class attribute should not be set at
                #  all in the post-processed class.
                delattr(cls, name)
            else:
                setattr(cls, name, f.default)


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
    if hash is None:
        # Not hashable.
        cls.__hash__ = None
    elif hash:
        cls.__hash__ = _hash(list(filter(lambda f: f.hash or f.hash is None,
                                         fields)))
    # Otherwise, use the base class definition of hash().  That is,
    #  don't set anything on this class.

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
        return _process_class(cls, repr, cmp, hash, init, slots, frozen,
                              False)

    # See if we're being called as @dataclass or @dataclass().
    if _cls is None:
        # We're called as @dataclass().
        return wrap

    # We're called as @dataclass, with a class.
    return wrap(_cls)


def make_class(cls_name, fields, *, bases=None, repr=True, cmp=True,
               hash=None, init=True, slots=False, frozen=False,
               default_type=str):
    # fields is a list of (name, type, field)
    if bases is None:
        bases = (object,)

    if isinstance(fields, str):
        # This is for the case of using 'x y' as a shortcut for
        #  ['x', 'y'].
        fields = fields.replace(',', ' ').split()

    # Normalize the fields.  The user can supply:
    #  - just a name
    #  - a field() with name and type specified
    fields1 = {}  # XXX needs to be an orderedict
    annotations = {}  # XXX also ordered?
    for idx, f in enumerate(fields, 1):
        if isinstance(f, str):
            # Only a name specified, assume it's of type default_type.
            f = field(f, default_type)

        if f.name is None:
            raise ValueError(f'name must be specified for field #{idx}')
        if f.type is None:
            raise ValueError(f'type must be specified for field {f.name!r}')

        fields1[f.name] = f
        annotations[f.name] = type

    fields1['__annotations__'] = annotations
    return _process_class(type(cls_name, bases, fields1), repr, cmp, hash,
                          init, slots, frozen, True)
