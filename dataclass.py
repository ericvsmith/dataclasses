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

__all__ = ['dataclass', 'field']

_MISSING = "MISSING"
_MARKER = '__dataclass_fields__'
_SELF_NAME = '_self'
_OTHER_NAME = '_other'


# XXX: can't use slots, because we fill in name later
# maybe create another (derived?) type that adds the name, so we can use slots?
# not sure how many of these we're going to have
class field:
    ## __slots__ = ('name',
    ##              'default',
    ##              'repr',
    ##              'hash',
    ##              'init',
    ##              'cmp',
    ##              )
    def __init__(self, *, default=_MISSING, repr=True, hash=True, init=True, cmp=True):
        self.name = None  # added later
        self.default = default
        self.repr = repr
        self.hash = hash
        self.init = init
        self.cmp = cmp

    # XXX: currently for testing. either complete this, or delete it
    def __repr__(self):
        return f'field({self.name})'


def _to_field_definition(type):
    return type


def _tuple_str(obj_name, fields):
    # Return a string representing each field of obj_name as a tuple
    #  member. So, if fields is ['x', 'y'] and obj_name is "self",
    #  return "(self.x,self.y)".

    #Special case for the 0-tuple
    if len(fields) == 0:
        return '()'
    # Note the trailing comma, needed for 1-tuple
    return f'({",".join([f"{obj_name}.{f}" for f in fields])},)'


def _create_fn(name, args, body, locals=None):
    # Note that we mutate locals. Caller beware!
    if locals is None:
        locals = {}
    args = ','.join(args)
    body = '\n'.join(f' {b}' for b in body)
    txt = f'def {name}({args}):\n{body}'
    #print(txt)
    exec(txt, None, locals)
    return locals[name]


def _init(fields):
    # Make sure we don't have fields without defaults following fields
    #  with defaults.  If I switch to building the source to the
    #  __init__ function and compiling it, this isn't needed, since it
    #  will catch the problem.
    seen_default = False
    for k, v in fields.items():
        if v.default is not _MISSING:
            seen_default = True
        else:
            if seen_default:
                raise ValueError(f'non-default argument {k} follows default argument')

    args = [_SELF_NAME] + [(f if info.default is _MISSING else f"{f}=_def_{f}") for f, info in fields.items()]
    body_lines = [f'{_SELF_NAME}.{f}={f}' for f in fields]
    if len(body_lines) == 0:
        body_lines = ['pass']

    # Locals contains defaults, supply them.
    locals = {f'_def_{f}': info.default
              for f, info in fields.items() if info.default is not _MISSING}
    return _create_fn('__init__',
                      args,
                      body_lines,
                      locals)


def _repr(fields):
    return _create_fn('__repr__',
                      [f'{_SELF_NAME}'],
                      [f'return {_SELF_NAME}.__class__.__name__ + f"(' + ','.join([f"{k}={{{_SELF_NAME}.{k}!r}}" for k in fields]) + ')"'],
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
    # __ne__ is slightly different, use a different pattern.
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

    annotations = getattr(cls, '__annotations__', {})

    results = []
    for name, type in annotations.items():
        # If the default value isn't derived from field, then it's
        # only a normal default value.  Convert it to a field().
        default = getattr(cls, name, _MISSING)
        if not isinstance(default, field):
            default = field(default=default)
        results.append((name, default))
    return results


def _field_filter(fields, predicate):
    # Use an OrderedDict to guarantee order.
    filtered = collections.OrderedDict()
    for k, v in fields.items():
        if predicate(k, v):
            filtered[k] = v
    return filtered


def dataclass(cls):
    fields = collections.OrderedDict()
    our_fields = []

    # In reversed order so that most derived class overrides earlier
    #  definitions.
    for m in reversed(cls.__mro__):
        # Only process classes marked with our decorator, or our own
        #  class.  Special case for ourselves because we haven't added
        #  _MARKER to ourselves yet.
        if m is cls or hasattr(m, _MARKER):
            for name, info in _find_fields(m):
                fields[name] = info

                # Field validations for our class.  This is delayed
                #  until now, instead of in the field() constructor,
                #  since only here do we know the field name, which
                #  allows better error reporting.
                if m is cls:
                    info.name = name
                    our_fields.extend([info])

                    # If init=False, we must have a default value.
                    #  Otherwise, how would it get initialized?
                    if not info.init and info.default == _MISSING:
                        raise ValueError(f'field {name} has init=False, but '
                                         'has no default value')

                    # If the class attribute (which is the default
                    #  value for this field) exists and is of type
                    #  'field', replace it with the real default.
                    #  This is so that normal class introspection sees
                    #  a real default value.
                    if isinstance(getattr(cls, name, None), field):
                        setattr(cls, name, info.default)

    setattr(cls, _MARKER, our_fields)

    cls.__init__ = _init(_field_filter(fields, lambda k, info: info.init))
    cls.__repr__ = _repr(_field_filter(fields, lambda k, info: info.repr))
    cls.__hash__ = _hash(_field_filter(fields, lambda k, info: info.hash))

    # Create comparison functions.
    cmp_fields = _field_filter(fields, lambda k, info: info.cmp)
    cls.__eq__ = _eq(cmp_fields)
    cls.__ne__ = _ne()
    cls.__lt__ = _lt(cmp_fields)
    cls.__le__ = _le(cmp_fields)
    cls.__gt__ = _gt(cmp_fields)
    cls.__ge__ = _ge(cmp_fields)

    return cls
