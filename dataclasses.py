import sys
from copy import deepcopy
import collections
import inspect

__all__ = ['dataclass',
           'field',
           'FrozenInstanceError',

           # Helper functions.
           'fields',
           'isdataclass',
           'asdict',
           'astuple',
           ]

# Just for development, I'll remove this before shipping.
_debug = False

# Raised when an attempt is made to modify a frozen class.
class FrozenInstanceError(AttributeError): pass

# A sentinel object to detect if a parameter is supplied or not.
_MISSING = object()

# A sentinel object for default values to signal that a
#  default-factory will be used.
# This is given a nice repr() which will appear in the function
#  signature of dataclasses' constructors.
class _HAS_DEFAULT_FACTORY_CLASS:
    def __repr__(self):
        return '<factory>'
_HAS_DEFAULT_FACTORY = _HAS_DEFAULT_FACTORY_CLASS()

# The name of an attribute on the class where we store the Field
#  objects. Also used to check if a class is a Data Class.
_MARKER = '__dataclass_fields__'

# The name of the function, that if it exists, is called at the end of
# __init__.
_POST_INIT_NAME = '__dataclass_post_init__'

# Instances of Field are only ever created from within this module,
#  and only from the field() function, although Field instances are
#  exposed externally as (conceptually) read-only objects.
# name and type are filled in after the fact, not in __init__. They're
#  not known at the time this class is instantiated, but it's
#  convenient if they're available later.
# When cls._MARKER is filled in with a list of Field objects, the name
#  and type fields will have been populated.
class Field:
    __slots__ = ('name',
                 'type',
                 'default',
                 'default_factory',
                 'repr',
                 'hash',
                 'init',
                 'cmp',
                 )

    def __init__(self, default, default_factory, init, repr, hash, cmp):
        self.name = None
        self.type = None
        self.default = default
        self.default_factory = default_factory
        self.init = init
        self.repr = repr
        self.hash = hash
        self.cmp = cmp

    def __repr__(self):
        return ('Field('
                f'name={self.name!r},'
                f'type={self.type},'
                f'default={"_MISSING" if self.default is _MISSING else self.default},'
                f'default_factory={"_MISSING" if self.default_factory is _MISSING else self.default_factory},'
                f'init={self.init},'
                f'repr={self.repr},'
                f'hash={self.hash},'
                f'cmp={self.cmp}'
                ')')


# This function is used instead of exposing Field creation directly,
#  so that a type checker can be told (via overloads) that this is a
#  function whose type depends on its parameters.
def field(*, default=_MISSING, default_factory=_MISSING, init=True, repr=True,
          hash=None, cmp=True):
    if default is not _MISSING and default_factory is not _MISSING:
        raise ValueError('cannot specify both default and default_factory')
    return Field(default, default_factory, init, repr, hash, cmp)


def _tuple_str(obj_name, fields):
    # Return a string representing each field of obj_name as a tuple
    #  member. So, if fields is ['x', 'y'] and obj_name is "self",
    #  return "(self.x,self.y)".

    # Special case for the 0-tuple.
    if len(fields) == 0:
        return '()'
    # Note the trailing comma, needed for 1-tuple.
    return f'({",".join([f"{obj_name}.{f.name}" for f in fields])},)'


def _create_fn(name, args, body, globals=None, locals=None,
               return_type=_MISSING):
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

    if _debug:
        print(txt)
        print('locals:', locals)
        print('globals:', globals)
        print()

    exec(txt, globals, locals)
    return locals[name]


def _field_assign(frozen, name, value, self_name):
    # If we're a frozen class, then assign to our fields in __init__
    #  via object.__setattr__.  Otherwise, just use a simple
    #  assignment.
    # self_name is what "self" is called in this function: don't
    #  hard-code "self", since that might be a field name.
    if frozen:
        return f'object.__setattr__({self_name},{name!r},{value})'
    return f'{self_name}.{name}={value}'


def _field_init(f, frozen, globals, self_name):
    # Return the text of the line in the body of __init__ that will initialize
    #  this field.

    default_name = f'_dflt_{f.name}'
    if f.default_factory is not _MISSING:
        if f.init:
            # This field has a default factory.  If a parameter is
            #  given, use it.  If not, call the factory.
            globals[default_name] = f.default_factory
            value = (f'{default_name}() '
                     f'if {f.name} is _HAS_DEFAULT_FACTORY '
                     f'else {f.name}')
        else:
            # This is a field that's not in the __init__ params, but
            #  has a default factory function.  It needs to be
            #  initialized here by calling the factory function,
            #  because there's no other way to initialize it.

            # For a field initialized with a default=defaultvalue, the
            #  class dict just has the default value
            #  (cls.fieldname=defaultvalue). But that won't work for a
            #  default factory, the factory must be called in __init__
            #  and we must assign that to self.fieldname. We can't
            #  fall back to the class dict's value, both because it's
            #  not set, and because it might be different per-class
            #  (which, after all, is why we have a factory function!).

            globals[default_name] = f.default_factory
            value = f'{default_name}()'
    else:
        # No default factory.
        if f.init:
            if f.default is _MISSING:
                # There's no default, just do an assignment.
                value = f.name
            elif f.default is not _MISSING:
                globals[default_name] = f.default
                value = f.name
        else:
            # This field does not need initialization. Signify that to
            #  the caller by returning None.
            return None

    # Now, actually generate the field assignment.
    return _field_assign(frozen, f.name, value, self_name)


def _init_param(f):
    # Return the __init__ parameter string for this field.
    #  For example, the equivalent of 'x:int=3' (except instead of 'int',
    #  reference a variable set to int, and instead of '3', reference a
    #  variable set to 3).
    if f.default is _MISSING and f.default_factory is _MISSING:
        # There's no default, and no default_factory, just
        #  output the variable name and type.
        default = ''
    elif f.default is not _MISSING:
        # There's a default, this will be the name that's used to look it up.
        default = f'=_dflt_{f.name}'
    elif f.default_factory is not _MISSING:
        # There's a factory function. Set a marker.
        default = '=_HAS_DEFAULT_FACTORY'
    return f'{f.name}:_type_{f.name}{default}'


def _init_fn(fields, frozen, has_post_init, self_name):
    # Make sure we don't have fields without defaults following fields
    #  with defaults.  This actually would be caught when exec-ing the
    #  function source code, but catching it here gives a better error
    #  message, and future-proofs us in case we build up function using
    #  ast.
    seen_default = False
    for f in fields:
        # Only consider fields in the __init__ call.
        if f.init:
            if not (f.default is _MISSING and f.default_factory is _MISSING):
                seen_default = True
            elif seen_default:
                raise TypeError(f'non-default argument {f.name!r} '
                                'follows default argument')

    globals = {'_MISSING': _MISSING,
               '_HAS_DEFAULT_FACTORY': _HAS_DEFAULT_FACTORY}

    body_lines = []
    for f in fields:
        line = _field_init(f, frozen, globals, self_name)
        if line is not None:
            # line is None means that this field doesn't require
            #  initialization. Just skip it.
            body_lines.append(line)

    # Does this class have an post-init function?
    if has_post_init:
        body_lines += [f'{self_name}.{_POST_INIT_NAME}()']

    # If no body lines, add 'pass'.
    if len(body_lines) == 0:
        body_lines = ['pass']

    locals = {f'_type_{f.name}': f.type for f in fields}
    return _create_fn('__init__',
                      [self_name] +[_init_param(f) for f in fields if f.init],
                      body_lines,
                      locals=locals,
                      globals=globals,
                      return_type=None)


def _repr_fn(fields):
    return _create_fn('__repr__',
                      ['self'],
                      ['return self.__class__.__name__ + f"(' +
                       ', '.join([f"{f.name}={{self.{f.name}!r}}"
                                  for f in fields]) +
                       ')"'])


def _frozen_setattr(self, name, value):
    raise FrozenInstanceError(f'cannot assign to field {name!r}')


def _frozen_delattr(self, name):
    raise FrozenInstanceError(f'cannot delete field {name!r}')


def _cmp_fn(name, op, self_tuple, other_tuple):
    # Create a comparison function.  If the fields in the object are
    #  named 'x' and 'y', then self_tuple is the string
    #  '(self.x,self.y)' and other_tuple is the string
    #  '(other.x,other.y)'.

    return _create_fn(name,
                      ['self', 'other'],
                      [ 'if other.__class__ is self.__class__:',
                       f' return {self_tuple}{op}{other_tuple}',
                        'return NotImplemented'])


def _set_eq_fns(cls, fields):
    # Create and set the equality comparison methods on cls.
    # Pre-compute self_tuple and other_tuple, then re-use them for
    #  each function.
    self_tuple = _tuple_str('self', fields)
    other_tuple = _tuple_str('other', fields)
    for name, op in [('__eq__', '=='),
                     ('__ne__', '!='),
                     ]:
        _set_attribute(cls, name, _cmp_fn(name, op, self_tuple, other_tuple))


def _set_compare_fns(cls, fields):
    # Create and set the comparison methods on cls.
    # Pre-compute self_tuple and other_tuple, then re-use them for
    #  each function.
    self_tuple = _tuple_str('self', fields)
    other_tuple = _tuple_str('other', fields)
    for name, op in [('__lt__', '<'),
                     ('__le__', '<='),
                     ('__gt__', '>'),
                     ('__ge__', '>='),
                     ]:
        _set_attribute(cls, name, _cmp_fn(name, op, self_tuple, other_tuple))


def _hash_fn(fields):
    self_tuple = _tuple_str('self', fields)
    return _create_fn('__hash__',
                      ['self'],
                      [f'return hash({self_tuple})'])


def _find_fields(cls):
    # Return a list tuples of of (name, type, Field()), in order, for
    #  this class (and no super-classes).  Fields are found from
    #  __annotations__ (which is guaranteed to be ordered).  Default
    #  values are from class attributes, if a field has a default.  If
    #  the default value is a Field(), then it contains additional
    #  info beyond (and possibly including) the actual default value.
    #  Fields which are ClassVars are ignored.

    annotations = getattr(cls, '__annotations__', {})

    results = []
    for a_name, a_type in annotations.items():
        # If this is a ClassVar, ignore it. It makes no sense for a
        #  ClassVar to be a field.

        # If typing has not been imported, then it's impossible for
        #  any annotation to be a ClassVar. So, only look for ClassVar
        #  if typing has been imported.
        typing = sys.modules.get('typing')
        if typing is not None:
            # This test uses a typing internal class, but it's the best
            #  way to test if this is a ClassVar.
            if type(a_type) is typing._ClassVar:
                # This field is a ClassVar. Ignore it.
                continue

        # If the default value isn't derived from field, then it's
        #  only a normal default value.  Convert it to a Field().
        default = getattr(cls, a_name, _MISSING)
        if isinstance(default, Field):
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


def _process_class(cls, repr, eq, compare, hash, init, frozen):
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
        b_fields = getattr(b, _MARKER, None)
        if b_fields:
            for f in b_fields.values():
                fields[f.name] = f

    # Now find fields in our class.  While doing so, validate some
    #  things, and set the default values (as class attributes)
    #  where we can.
    for name, type_, f in _find_fields(cls):
        fields[name] = f

        # The name and type must not be filled in before hand: we
        #  grabbed them from the annotations.
        assert f.name is None and f.type is None

        # Set the field name and type, which we don't know until now.
        f.name = name
        f.type = type_

        # Validations for fields directly on our class.  This is
        #  delayed until now, instead of in the Field() constructor,
        #  since only here do we know the field name, which allows
        #  better error reporting.

        # If init=False, we must have a default value.  Otherwise,
        # how would it get initialized?
        if (not f.init and f.default is _MISSING and
                           f.default_factory is _MISSING):
            raise TypeError(f'field {name} has init=False, but '
                            'has no default value or factory function')

        # If the class attribute (which is the default value for
        #  this field) exists and is of type 'Field', replace it
        #  with the real default.  This is so that normal class
        #  introspection sees a real default value.
        if isinstance(getattr(cls, name, None), Field):
            if f.default is _MISSING:
                # If there's no default, delete the class attribute.
                #  This happens if we specify field(repr=False), for
                #  example.  The class attribute should not be set at
                #  all in the post-processed class.
                delattr(cls, name)
            else:
                setattr(cls, name, f.default)

        # Disallow mutable defaults for known types.
        if isinstance(f.default, (list, dict, set)):
            # XXX: include a statement about using a factory in the error message
            raise ValueError(f'mutable default {type(f.default)} for field '
                             f'{name} is not allowed')

    # Just to save some typing in the code below, get the fields as a list.
    field_list = list(fields.values())

    # Remember all of the fields on our class (including bases).  This
    #  marks this class as being a dataclass.
    setattr(cls, _MARKER, fields)

    # We also need to check if a parent class is frozen: frozen has to
    #  be inherited down.
    is_frozen = frozen or cls.__setattr__ is _frozen_setattr

    # If we're generating comparison methods, also generate the eq methods.
    if compare:
        eq = True

    if init:
        # Does this class have a post-init function?
        has_post_init = hasattr(cls, _POST_INIT_NAME)
        _set_attribute(cls, '__init__',
                       _init_fn(field_list,
                                is_frozen,
                                has_post_init,

                                # The name to use for the "self" param
                                #  in __init__.  Use "self" if possible.
                                '__dataclass_self__' if 'self' in fields
                                    else 'self',
                                ))
    if repr:
        _set_attribute(cls, '__repr__',
                       _repr_fn(list(filter(lambda f: f.repr, field_list))))

    if is_frozen:
        _set_attribute(cls, '__setattr__', _frozen_setattr)
        _set_attribute(cls, '__delattr__', _frozen_delattr)

    generate_hash = False
    if hash is None:
        if eq and frozen:
            # Generate a hash function.
            generate_hash = True
        elif eq and not frozen:
            # Not hashable.
            _set_attribute(cls, '__hash__', None)
        elif not eq:
            # Otherwise, use the base class definition of hash().  That is,
            #  don't set anything on this class.
            pass
        else:
            assert "can't get here"
    else:
        generate_hash = hash
    if generate_hash:
        _set_attribute(cls, '__hash__',
                       _hash_fn(list(filter(lambda f: f.cmp
                                                      if f.hash is None
                                                      else f.hash,
                                            field_list))))

    if eq:
        # Create and __eq__ and __ne__ methods.
        _set_eq_fns(cls, list(filter(lambda f: f.cmp, field_list)))

    if compare:
        # Create and __lt__, __le__, __gt__, and __ge__ methods.
        # Create and set the comparison functions.
        _set_compare_fns(cls, list(filter(lambda f: f.cmp, field_list)))

    if not getattr(cls, '__doc__'):
        # Create a class doc-string
        cls.__doc__ = \
            cls.__name__ + str(inspect.signature(cls)).replace(' -> None', '')

    return cls


# _cls should never be specified by keyword, so start it with an
#  underscore. The presense of _cls is used to detect if this
#  decorator is being called with parameters or not.
def dataclass(_cls=None, *, init=True, repr=True, hash=None, eq=True,
              compare=True, frozen=False):
    def wrap(cls):
        return _process_class(cls, repr, eq, compare, hash, init, frozen)

    # See if we're being called as @dataclass or @dataclass().
    if _cls is None:
        # We're called as @dataclass().
        return wrap

    # We're called as @dataclass, with a class.
    return wrap(_cls)


def fields(class_or_instance):
    """Returns the list of fields of this dataclass. Accepts a dataclass
    or an instance of one."""
    try:
        return getattr(class_or_instance, _MARKER)
    except AttributeError:
        raise TypeError('must be called with a dataclass type or instance')


def isdataclass(obj):
    """Returns True if obj is an instance of a dataclass, otherwise
    returns False."""
    return not isinstance(obj, type) and hasattr(obj, _MARKER)


def asdict(obj, *, dict_factory=dict):
    """Get the fields of a dataclass instance as a new dictionary mapping
    field names to field values. Example usage::

      @dataclass
      class C:
          x: int
          y: int

      c = C(1, 2)
      assert asdict(c) == {'x': 1, 'y': 2}

    If given, 'dict_factory' will be used instead of built-in dict.
    The function applies recursively to field values that are
    dataclass instances. This will also look into built-in containers: tuples,
    lists, and dicts.
    """
    if not isdataclass(obj):
        raise TypeError("asdict() should be called on dataclass instances")
    return _asdict_inner(obj, dict_factory)

def _asdict_inner(obj, dict_factory):
    if isdataclass(obj):
        result = []
        for name in fields(obj):
            value = _asdict_inner(getattr(obj, name), dict_factory)
            result.append((name, value))
        return dict_factory(result)
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_asdict_inner(v, dict_factory) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)((_asdict_inner(k, dict_factory), _asdict_inner(v, dict_factory))
                          for k, v in obj.items())
    else:
        return deepcopy(obj)


def astuple(obj, *, tuple_factory=tuple):
    """Get the fields of a dataclass instance as a new tuple of field values.
    Example usage::

      @dataclass
      class C:
          x: int
          y: int

    c = C(1, 2)
    assert asdtuple(c) == (1, 2)

    If given, 'tuple_factory' will be used instead of built-in tuple.
    The function applies recursively to field values that are
    dataclass instances. This will also look into built-in containers: tuples,
    lists, and dicts.
    """
    if isinstance(obj, type) or not hasattr(obj, _MARKER):
        raise TypeError("astuple() should be called on dataclass instances")
    return _astuple_inner(obj, tuple_factory)

def _astuple_inner(obj, tuple_factory):
    if isdataclass(obj):
        result = []
        for name in fields(obj):
            value = _astuple_inner(getattr(obj, name), tuple_factory)
            result.append(value)
        return tuple_factory(result)
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_astuple_inner(v, tuple_factory) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)((_astuple_inner(k, tuple_factory), _astuple_inner(v, tuple_factory))
                          for k, v in obj.items())
    else:
        return deepcopy(obj)
