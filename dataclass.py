# TODO:

#  what exception to raise when non-default follows default? currently
#  ValueError

# sepcial name in __init__: _self: reserve this name?

import typing
import collections

__all__ = ['dataclass', 'field', 'make_class', 'FrozenInstanceError']


# Raised when an attempt is made to modify a frozen class.
class FrozenInstanceError(AttributeError):
    msg = "can't set attribute"
    args = [msg]


_MISSING = object()
_MARKER = '__dataclass_fields__'
_POST_INIT_NAME = '__dataclass_post_init__'

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
        return f'field(name={self.name!r},default={"_MISSING" if self.default is _MISSING else self.default!r},cmp={self.cmp})'


def _tuple_str(obj_name, fields):
    # Return a string representing each field of obj_name as a tuple
    #  member. So, if fields is ['x', 'y'] and obj_name is "self",
    #  return "(self.x,self.y)".

    # Special case for the 0-tuple.
    if len(fields) == 0:
        return '()'
    # Note the trailing comma, needed for 1-tuple.
    return f'({",".join([f"{obj_name}.{f.name}" for f in fields])},)'


def _create_fn(name, args, body, globals=None, locals=None, return_type=_MISSING):
    # Note that we mutate locals when exec() is called. Caller beware!
    if locals is None:
        locals = {}
    return_annotation = ''
    if return_type is not _MISSING:
        locals['_return_type'] = return_type
        return_annotation = '->_return_type'
    args = ','.join(args)
    body = '\n'.join(f' {b}' for b in body)
    txt = f'def {name}({args}){return_annotation}:\n{body}'
    #print(txt)
    exec(txt, globals, locals)
    return locals[name]


def _field_assign(frozen, name, value):
    # If we're a frozen class, then assign to our fields in __init__
    #  via object.__setattr__.  Otherwise, just use a simple
    #  assignment.
    if frozen:
        return f'object.__setattr__({_SELF},{name!r},{value})'
    return f'{_SELF}.{name}={value}'


def _field_init(f, frozen):
    # Return the text of the line in __init__ that will initialize
    #  this field.

    # If this field has a default, and if we're using that default,
    #  then copy it.  Otherwise, just assign the value.

    # Do we know we don't have to copy the default value?
    dont_need_copy = type(f.default) in {bool, int, float, complex, str,
                                         tuple, frozenset}
    # Do we know how to copy the default value?
    can_copy = type(f.default) in {list, dict, set}

    if f.default is _MISSING:
        # There's no default, just do an assignment.
        value = f.name
    elif dont_need_copy:
        value = (f'type({_SELF}).{f.name} '
                 f'if {f.name} is _MISSING else {f.name}')
    elif can_copy:
        value = (f'type({_SELF}).{f.name}.copy() '
                 f'if {f.name} is _MISSING else {f.name}')
    else:
        value = (f'_copy.copy(type({_SELF}).{f.name}) '
                 f'if {f.name} is _MISSING else {f.name}')
    return _field_assign(frozen, f.name, value)


def _init_fn(fields, frozen, has_post_init):
    # Make sure we don't have fields without defaults following fields
    #  with defaults.  This actually would be caught when exec-ing the
    #  function source code, but catching it here gives a better error
    #  message, and future-proofs us in case we build up function using
    #  ast.
    seen_default = False
    for f in fields:
        if f.default is not _MISSING:
            seen_default = True
        elif seen_default:
            raise TypeError(f'non-default argument {f.name} '
                            'follows default argument')

    body_lines = [_field_init(f, frozen) for f in fields]

    # Does this class have an post-init function?
    if has_post_init:
        body_lines += [f'{_SELF}.{_POST_INIT_NAME}()']

    # If no body lines, add 'pass'
    if len(body_lines) == 0:
        body_lines = ['pass']


    import copy
    globals = {'_MISSING': _MISSING,
               '_copy': copy}

    locals = {f'_type_{f.name}': f.type for f in fields}
    return _create_fn('__init__',
                      [_SELF] +
                      [(f'{f.name}:_type_{f.name}' if f.default is _MISSING
                        else f'{f.name}:_type_{f.name}=_MISSING')
                        for f in fields],
                      body_lines,
                      locals=locals,
                      globals=globals,
                      return_type=None)


def _repr_fn(fields):
    return _create_fn('__repr__',
                      [_SELF],
                      [f'return {_SELF}.__class__.__name__ + f"(' +
                         ','.join([f"{f.name}={{{_SELF}.{f.name}!r}}"
                                   for f in fields]) +
                         ')"'])


def _frozen_setattr(self, name, value):
    raise FrozenInstanceError()


def _frozen_delattr(self, name):
    raise FrozenInstanceError()


# All __ne__ functions are the same, and don't depend on the fields.
def _ne(self, other) -> bool:
    result = self.__eq__(other)
    return NotImplemented if result is NotImplemented else not result


def _cmp_fn(name, op, self_tuple, other_tuple):
    # Create a comparison function.  If the fields in the object are
    #  named 'x' and 'y', then self_tuple is the string
    #  '(_self.x,_self.y)' and other_tuple is the string
    #  '(_other.x,_other.y'),

    if op == '!=':
        # __ne__ is slightly different from other comparison
        #  functions, since it only calls __eq__.  Return a regular
        #  function: no need to generate the source code, since it's
        #  indepenedent of the fields involved.
        return _ne

    return _create_fn(name,
                      [_SELF, _OTHER],
                      [f'if {_OTHER}.__class__ is {_SELF}.__class__:',
                       f'    return {self_tuple}{op}{other_tuple}',
                        'return NotImplemented'])


def _set_cmp_fns(cls, fields):
    # Create and set all of the comparison functions on cls.
    # Pre-compute self_tuple and other_tuple, then re-use them for
    #  each function.
    self_tuple = _tuple_str(_SELF, fields)
    other_tuple = _tuple_str(_OTHER, fields)
    for name, op in [('__eq__', '=='),
                     ('__ne__', '!='),
                     ('__lt__', '<'),
                     ('__le__', '<='),
                     ('__gt__', '>'),
                     ('__ge__', '>='),
                     ]:
        _set_attribute(cls, name, _cmp_fn(name, op, self_tuple, other_tuple))


def _hash_fn(fields):
    self_tuple = _tuple_str(_SELF, fields)
    return _create_fn('__hash__',
                      [_SELF],
                      [f'return hash({self_tuple})'])


def _find_fields(cls):
    # Return a list tuples of of (name, type, field()), in order, for
    #  this class (and no super-classes).  Fields are found from
    #  __annotations__ (which is guaranteed to be ordered).  Default
    #  values are from class attributes, if a field has a default.  If
    #  the default value is a field(), then it contains additional
    #  info beyond (and possibly including) the actual default value.
    #  Fields which are ClassVars are ignored.

    annotations = getattr(cls, '__annotations__', {})

    results = []
    for a_name, a_type in annotations.items():
        # This test uses a typing internal class, but it's the best
        #  way to test if this is a ClassVar.
        if type(a_type) is typing._ClassVar:
            # Skip this field if it's a ClassVar
            continue

        # If the default value isn't derived from field, then it's
        # only a normal default value.  Convert it to a field().
        default = getattr(cls, a_name, _MISSING)
        if isinstance(default, field):
            f = default
        else:
            f = field(default=default)
        results.append((a_name, a_type, f))
    return results


def _set_attribute(cls, name, value):
    # Raise AttributeError if an attribute by this name already
    #  exists.
    if name in cls.__dict__:
        raise AttributeError(f'Cannot overwrite attribute {name} '
                             f'in {cls.__name__}')
    setattr(cls, name, value)


def _process_class(cls, repr, cmp, hash, init, slots, frozen, dynamic):
    # Use an OrderedDict because:
    #  - Order matters!
    #  - Derived class fields overwrite base class fields.
    fields = collections.OrderedDict()

    # Find our base classes in reverse MRO order, and exclude
    #  ourselves.  In reversed order so that more derived classes
    #  override earlier field definitions in base classes.
    for b in cls.__mro__[-1:0:-1]:
        # Only process classes that have been processed by our
        #  decorator.  That is, they have a _MARKER attribute.
        for f in getattr(b, _MARKER, []):
            fields[f.name] = f

    # Now process our class.
    for name, type_, f in _find_fields(cls):
        # The checks for dynamic=True happen in make_class(), since it
        #  can generate better error message for missing f.name.
        if not dynamic:
            # The name and type must not be filled in before hand: we
            #  grabbed them from the annotations.
            if f.name is not None or f.type is not None:
                raise TypeError(f'cannot specify name or type for {name!r}')

            # For fields defined in our class, set the name and type,
            #  which we don't know until now.
            f.name = name
            f.type = type_

        fields[name] = f

        # Validations for fields directly on our class.  This is
        #  delayed until now, instead of in the field() constructor,
        #  since only here do we know the field name, which allows
        #  better error reporting.

        # If init=False, we must have a default value.  Otherwise,
        # how would it get initialized?
        if not f.init and f.default is _MISSING:
            raise TypeError(f'field {name} has init=False, but '
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
    #  bases).  This marks this class as being a dataclass.
    setattr(cls, _MARKER, fields)

    # We also need to check if a parent class is frozen: frozen has to
    #  be inherited down.
    is_frozen = frozen or cls.__setattr__ is _frozen_setattr

    if init:
        # Does this class have a post-init function?
        has_post_init = hasattr(cls, _POST_INIT_NAME)
        _set_attribute(cls, '__init__',
                       _init_fn(list(filter(lambda f: f.init, fields)),
                                is_frozen,
                                has_post_init))
    if repr:
        _set_attribute(cls, '__repr__',
                       _repr_fn(list(filter(lambda f: f.repr, fields))))
    if is_frozen:
        _set_attribute(cls, '__setattr__', _frozen_setattr)
        _set_attribute(cls, '__delattr__', _frozen_delattr)

    generate_hash = False
    if hash is None:
        if cmp and frozen:
            # Generate a hash function.
            generate_hash = True
        elif cmp and not frozen:
            # Not hashable.
            _set_attribute(cls, '__hash__', None)
        elif not cmp:
            # Otherwise, use the base class definition of hash().  That is,
            #  don't set anything on this class.
            pass
        else:
            assert "can't get here"
    else:
        generate_hash = hash
    if generate_hash:
        _set_attribute(cls, '__hash__',
                       _hash_fn(list(filter(lambda f: f.hash or f.hash is None,
                                            fields))))

    if cmp:
        # Create and set the comparison functions.
        _set_cmp_fns(cls, list(filter(lambda f: f.cmp, fields)))

    if slots:
        # Need to create a new class, since we can't set __slots__
        #  after a class has been created.

        # Make sure __slots__ isn't already set.
        if '__slots__' in cls.__dict__:
            # XXX Code duplication from _set_attribute: fix.
            raise AttributeError(f'Cannot overwrite attribute __slots__ '
                                 f'in {cls.__name__}')

        # Create a new dict for our new class.
        cls_dict = dict(cls.__dict__)
        cls_dict['__slots__'] = tuple(f.name for f in fields)
        for f in fields:
            # Remove our attributes. They'll still be available in _MARKER.
            cls_dict.pop(f.name, None)
        # Remove __dict__ itself.
        cls_dict.pop('__dict__', None)
        # And finally create the class.
        cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)

    return cls


# _cls should never be specified by keyword, so start it with an
#  underscore.
def dataclass(_cls=None, *, repr=True, cmp=True, hash=None, init=True,
               slots=False, frozen=False):
    def wrap(cls):
        return _process_class(cls, repr, cmp, hash, init, slots, frozen,
                              dynamic=False)

    # See if we're being called as @dataclass or @dataclass().
    if _cls is None:
        # We're called as @dataclass().
        return wrap

    # We're called as @dataclass, with a class.
    return wrap(_cls)


def make_class(cls_name, fields, *, bases=None, repr=True, cmp=True,
               hash=None, init=True, slots=False, frozen=False):
    # fields is a list of (name, type, field)
    if bases is None:
        bases = (object,)

    # Look through each field and build up an ordered class dictionary
    #  and an ordered dictionary for __annotations__.
    cls_dict = collections.OrderedDict()
    annotations = collections.OrderedDict()
    for idx, f in enumerate(fields, 1):
        if f.name is None:
            raise TypeError(f'name must be specified for field #{idx}')
        if f.type is None:
            raise TypeError(f'type must be specified for field {f.name!r}')

        cls_dict[f.name] = f
        annotations[f.name] = type
    cls_dict['__annotations__'] = annotations

    # Create the class
    cls = type(cls_name, bases, cls_dict)

    # And now process it normally, except pass in dynamic=True to skip
    #  some checks that don't hold when the fields are pre-created
    #  with a valid name and type.
    return _process_class(cls, repr, cmp, hash, init, slots, frozen,
                          dynamic=True)
