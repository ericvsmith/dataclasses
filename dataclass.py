# TODO:
#  what exception to raise when non-default follows default? currently ValueError
#  what to do if a user specifies a function we're going to overwrite, like __init__? error? overwrite it?

import ast
import collections

__all__ = ['dataclass']

_MISSING = "MISSING"
_MARKER = '__marker__'
_SELF_NAME = '_self'

class _FieldInfo:
    # type is never used.  Do we need to keep it?
    def __init__(self, type, default):
        self.type = type
        self.default = default


def _to_field_definition(typ):
    return typ


def _create_init(fields):
    # Example of creating a method with ast.

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

    args_with_self = [_SELF_NAME] + list(fields)
    args = [ast.Name(id=arg, ctx=ast.Load()) for arg in args_with_self]
    #[print('  ', ast.dump(a)) for a in args]
    defs = [ast.Name(id=f'_def_{k}', ctx=ast.Load())
            for idx, (k, v) in enumerate(fields.items())
            if v.default is not _MISSING]
    #[print('  ', ast.dump(a)) for a in defs]
    args_node = ast.arguments(args=[ast.arg(arg=arg)
                                    for arg in args_with_self],
                              kwonlyargs=[],
                              defaults=defs,
                              kw_defaults=[])

    stmts = [ast.Assign(targets=[ast.Attribute(value=ast.Name(id=_SELF_NAME,
                                                              ctx=ast.Load()),
                                               attr=a,
                                               ctx=ast.Store())],
                        value=ast.Name(id=a, ctx=ast.Load())) for a in fields]
    if len(stmts) == 0:
        # We need an empty body for __init__.  We still create
        #  __init__ even when it doesn't do anything, just to
        #  overwrite the __init__ that might be provided.  If we make
        #  that an error, delete this test.
        stmts = [ast.Pass()]
    module_node = ast.Module(body=[ast.FunctionDef(name='__init__',
                                                   args=args_node,
                                                   body=stmts,
                                                   decorator_list=[])])
    module_node = ast.fix_missing_locations(module_node)

    # Compile the ast.
    code = compile(module_node, '<string>', 'exec')

    # Locals contains defaults, supply them.
    locals = {f'_def_{k}': v.default
              for k, v in fields.items() if v.default is not _MISSING}
    eval(code, None, locals)

    # Extract our function from the newly created module.
    return locals['__init__']


def _create_repr(fields):
    # Example of creating methods via string and exec.
    txt =  (f'def __repr__({_SELF_NAME}):' #,{",".join(fields)}):'
            f' return {_SELF_NAME}.__class__.__name__ + f"(' + ','.join([f"{k}={{{_SELF_NAME}.{k}!r}}" for k in fields]) + ')"')
    locals={}
    exec(txt, None, locals)
    return locals['__repr__']


def _find_fields(cls):
    # Return a list tuples of tuples of (name, _FieldInfo), in order,
    #  for this class (and no subclasses).  Fields are found from
    #  __annotations__.  Default values are class attributes, if a
    #  field has a default.

    annotations = getattr(cls, '__annotations__', {})

    results = []
    for name, type in annotations.items():
        # If the annotation value isn't one of ours, then it's only a
        #  type.  Convert it to one of ours.
        results.append((name, _FieldInfo(_to_field_definition(type),
                                         getattr(cls, name, _MISSING))))
    return results


def dataclass(cls):
    fields = collections.OrderedDict()

    # In reversed order so that most derived class overrides earlier
    #  definitions.
    for m in reversed(cls.__mro__):
        # Only process classes marked with our decorator, or our own
        #  class.  Special case for ourselves because we haven't added
        #  _MARKER to ourselves yet.
        if m is cls or hasattr(m, _MARKER):
            for name, fieldinfo in _find_fields(m):
                fields[name] = fieldinfo

    setattr(cls, _MARKER, True)

    # Create __init__.
    cls.__init__ = _create_init(fields)

    # Create __repr__.
    cls.__repr__ = _create_repr(fields)

    return cls
