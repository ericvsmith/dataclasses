Start of discussion on python-ideas
https://mail.python.org/pipermail/python-ideas/2017-May/045618.html

Definitions
-----------

- A data class is a Python class that contains fields which are
  specified using PEP 526 variable annotations.


Goals
-----

- A minimum set of functionality for the initial release.  But we want
  to be able to add both new "core" functionality, as well as to allow
  third parties to add features.

- Allow multiple third parties to independently add features, without
  knowledge of or conflicts with each other.  For example, each
  extension might be in its own "namespace".

- Allow data classes to be subclassed in order to add additional
  fields.  For example, a Point3D deriving from a Point2D to add a z
  dimension.

- Allow specification of data classes whose instances are non-mutable
  and hashable (based on the values of fields).  Such data classes
  should be usable as dict keys, for example.

- Also allow for hashability and identity comparison based on object
  identity only.  For example, to store mutable objects as dict keys
  or in a numpy array.

- Do not subclass from tuple or list.  This is to make sure that
  Point2D(x=12, y=15) != Time(h=12, m=15).

- Efficient, for some definition.

- Allow data classes to declare methods.

- Allow data classes to specify a docstring.

- Allow for creation of data classes with a dynamically determined
  list of fields.  This is useful, for example, when creating data
  classes to represent rows in a CSV file or a database.

- For dynamically created data classes, allow a docstring to be
  specified.

- Support default values for fields. Fields without default values
  cannot follow fields with default values.

- Automatically create a __init__ function, which takes an argument
  for each field, with defaults as specified for each field, as
  appropriate.

- Support fields with default values that are not included in
  __init__.  What about such fields without default values?  Not
  allowed, or would they be initialized as None?

- Support mutable default values that are instantiated when new
  instances are created, possibly by providing a factory function.
  The canonical example is a default which is a list.

- Support optional (but by default) generation of all comparison
  functions, based on field values.

- Support setting __slots__.

- Optional support by type checkers (mypy) and typing.py (in the sense
  that you can declare and use data classes without using typing).

- That said, if you are using a type checker and/or typing.py, support
  it to the extent possible.

- Provide a way to detect if an object is an instance of any data
  class, similar to using _fields on namedtuples.  I'm not sure why
  people want to be able to detect this, but they do, and Raymond has
  always suggested looking for an attribute "_fields".

- Support the rough equivalent of nametuple's _asdict, _fields, and
  possibly others (like _astuple).

- Support fields that are not exposed in repr/str (for passwords, for
  example).

- Support fields that are not included in the hash (if generating
  one).

- Support fields that are not included in comparison functions (if
  generating them).



Non-goals
---------

- Compatibility with namedtuples.

- Compatibility with attrs.


Issues
------

- If not using a type checker, the type specified in the annotation is
  completely ignored, correct?  (Except for its existence, that is.)

- What happens with fields that do not have annotations? Are they
  ignored?

  class F:
      x: int = 0
      y = 1

- Can validation and conversion (ala attrs) be supported by the
  extensibility system, or does it need to be baked in?  It would be
  good if they were added by extensibility, so we can experiment with
  alternative implementations and feature sets.

- Since we have per-field information other than type, how does that
  get specified?  For example, a str that does not get included in the
  repr.  How to specify?  Use stubs, and functions like attr.ib()?

- Should __repr__/__str__ be optional?  Why?

- Do we need to specify __str__, or is __repr__ good enough?

- Should generation of __init__ be optional?  Why?  What would the
  default __init__ look like?  Parameterless?  What about defaults?

- Do we need the equivalent of nametuple's _replace() for immutable
  data classes?

- Should _asdict() and friends be members (like nametuple) or
  functions (like attrs)?

- Use inheritance, metaclasses, or decorators?  Implementation detail,
  decide after we finalize our goals.

- Should we explicitly support "shared" mutable defaults?  Like
  __init__(self, x=[]).  I think so.  That is, we shouldn't do
  something like try to detect mutable defaults and implicitly copy
  them.

- For dynamically created data classes, do we need an equivalent of
  namedtuple's "rename" parameter?  Or do we make the caller deal with
  invalid names and just raise an exception?  Should we provide a
  helper function?

- Using a class decorator provides an obvious place to add per-class
  parameters (hashable, frozen, etc).

- The only meaningful changes I've seen so far from attrs are:

  - Specification of types using PEP 526 and defaults using assignment
    syntax. But this is not to be underestimated for the simple cases!

  - Possibly moving converters and validators to the extension
    (metadata) mechanism.

- Brett's PyCon talk reminded me that with __init_subclass__ (PEP
  487), inheritance might be an attractive way to implement this.  Plus,
  it looks more like "do something to a class" and less like "create a
  new class", as it does with a decorator.

- Add annotations to all functions: __init__, __eq__, __hash__, etc?
