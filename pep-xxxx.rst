PEP: xxx
Title: Data Classes
Author: Eric V. Smith <eric@trueblade.com>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 02-Jun-2017
Python-Version: 3.7
Post-History: 02-Jun-2017

Notice for Reviewers
====================

This PEP and the initial implementation were drafted in a separate
repo: https://github.com/ericvsmith/dataclasses.  Before commenting in
a public forum please at least read the `discussion`_ listed at the
end of this PEP.

Abstract
========

This PEP describes an addition to the standard library called Data
Classes.  A class decorator is provided which inspects a class
definition for variables annotated with PEP 526 "Syntax for Variable
Annotations".  In this document, such variables are called fields.
Using these fields, the decorator adds generated method definitions to
the class to support instance initialization, a repr, and comparisons
methods.  Such a class is called a Data Class, but there's really
nothing special about the class: it is the same class but with the
generated methods added.

As an example::

  @dataclass
  class InventoryItem:
      name: str
      unit_price: float
      quantity_on_hand: int = 0

      def total_cost(self) -> float:
          return self.unit_price * self.quantity_on_hand

The InventoryItem class will have the equivalent of these methods
added::

  def __init__(self, name: str, unit_price: float, quantity_on_hand: int = 0) -> None:
      self.name = name
      self.unit_price = unit_price
      self.quantity_on_hand = quantity_on_hand
  def __repr__(self):
      return f'InventoryItem(name={self.name!r},unit_price={self.unit_price!r},quantity_on_hand={self.quantity_on_hand!r})'
  def __eq__(self, other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) == (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __ne__(self, other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) != (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __lt__(self, other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) < (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __le__(self, other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) <= (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __gt__(self, other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) > (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __ge__(self, other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) >= (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented

Data Classes saves you from writing and maintaining these functions.

Rationale
=========

There have been numerous attempts to define classes which exist
primarily to store values which are accessible by attribute lookup.
Some examples include:

- collection.namedtuple in the standard library.

- typing.NamedTuple in the standard library.

- The popular attrs [#]_ project.

- Many example online recipes [#]_, packages [#]_, and questions [#]_.
  David Beazley used a form of data classes as the motivating example
  in a PyCon 2013 metaclass talk [#]_.

So, why is this PEP needed?

With the addition of PEP 526, Python has a concise way to specify the
type of class members.  This PEP leverages that syntax to provide a
simple, unobtrusive way to describe Data Classes.

No base classes or metaclasses are used.  The decorated classes are
truly "normal" Python classes.  The Data Class decorator should not
interfere with any usage of the class.

Being in the standard library will allow many of the simpler usages of
existing libraries like those listed above to consolidate on Data
Classes.  Many of the libraries listed will have different feature
sets, and will of course continue to exist and prosper.

Where is it not appopriate to use Data Classes?

- Compatibility with tuples is required.

- True immutability is required.

- Type validation beyond that provided by PEPs 484 and 526 is
  required, or value validation.

XXX What do we provide that people want, but don't find above?

Specification
=============

All of the functions described in this PEP will live in a module named
``dataclasses``.

A function ``dataclass`` which is typically used as a class decorator
is provided to post-process classes and add generated member
functions, described below.

The ``dataclass`` decorator examines the class to find ``field``'s.  A
``field`` is defined as any variable identified in
``__annotations__``.  That is, a variable that is decorated with a
type annotation.  With a single exception described below, none of the
Data Class machinery examines the type specified in the annotation.

The ``dataclass`` decorator is typicalled applied with no parameters.
However, it also supports the following logical signature::

  def dataclass(*, init=True, repr=True, hash=None, cmp=True, frozen=False)

If ``dataclass`` is used just as a simple decorator with no
parameters, it acts as if it has the default values documented in this
signature.  For example::

  @dataclass
  class C:
      ...

is equivalent to::

  @dataclass()
  class C:
      ...

and::

  @dataclass(init=True, repr=True, hash=None, cmp=True, frozen=False)
  class C:
      ...

The various parameters to ``dataclass`` are:

- ``init``: If false, no ``__init__`` method will be generated.

- ``repr``: If false, no ``__repr__`` function will be generated.

- ``hash``, ``cmp``: For a discussion of ``hash`` and ``cmp`` and how
  they interact, see below.

- ``frozen``: If true, assigning to fields will generate an exception.
  This emulates read-only frozen instances.  See the discussion below.

``field``'s may optionally specify a default value, using normal
Python syntax::

  @dataclass
  class C:
      int a       # 'a' has no default value
      int b = 0   # assign a default value for 'b'

For common and simple use cases, no other functionality is required.
There are, however, some Data Class features that require additional
per-field information.  To satisfy this need for additional
information, you can replace the default field value with a call to
the provided ``field()`` function.  The signature of ``field()`` is::

  def field(*, default=<MISSING>, default_factory=None, repr=True,
            hash=None, init=True, cmp=True)

The ``<MISSING>`` value is an unspecified sentinel object used to
detect if the ``default`` parameter is provided.

The various parameters are:

- ``default``: If provided, this will be the default value for this
  field.  This is needed because the ``field`` call itself replaces
  the normal position of the default value.

- ``default_factory``: If provided, a zero-argument callable that will
  be called when a default value is needed for this field.  Among
  other purposes, this can be used to specify fields with mutable
  default values, discussed below.  It is an error to specify both
  ``default`` and ``default_factory``.

- ``init``: If true, this field is included as a parameter to the
  generated ``__init__`` function.

- ``repr``: If true, this field is included in the string returned by
  the generated ``__repr__`` function.

- ``hash``, ``cmp``: See the discussion of how these fields interact,
  below.

post-init processing
--------------------

Also allows for initial field values that depend on one or more other
fields.

class variables
---------------

hash and cmp
------------

frozen instances
----------------

mutable default values
----------------------

Module level helper functions
-----------------------------

- ``fields(class_or_instance)``

- ``asdict(instance)``

- ``astuple(instance)``

Notes to self
-----
- docstr for __init__, etc.
- Should there be a __dir__ that includes the module-level helpers?
- PEP 526 Variable Annotations
- Generated functions contain variable annotations
- Generate __init__
- Generate __repr__
- Frozen classes
- Generate __hash__ and __cmp__
- Mutable defaults
- __dataclass_fields__ attribute: implementation detail
- Only variable declarations are inspected, not methods or properties, even if they are annotated with return types.
- Members that are ClassVar are ignored
- Reserved field names
- make_class()
- post-init function: Take a parameter?
- Valid field names
- Module helper functions
- Default factory functions: called in __init__ time if init=False
- default values are added

.. _discussion:

Discussion
==========

python-ideas discussion
-----------------------

This discussion started on python-ideas [#]_ and was moved to a GitHub
repo [#]_ for further discussion.

- New syntax rejected, PEP 526 give enough flexibility.

- Mutable defaults

Support for automatically setting ``__slots__``?
------------------------------------------------

For the initial release, no.  ``__slots__`` needs to be added at class
creation time.  The decorator is called after the class is created, so
in order to add ``__slots__`` the decorator would have to create a new
class, set ``__slots__``, and return it.  Because this behavior is
somewhat surprising, the initial version of Data Classes will not
support automatically setting ``__slots__``.  There are a number of
workarounds:

  - Manually add ``__slots__`` in the class definition.

  - Write a function (which could be used as a decorator) that
    inspects the class using ``fields()`` and creates a new class with
    ``__slots__`` set.

Should post-init take params?
-----------------------------


why not namedtuple
------------------

- Point3D(2017, 6, 2) == Date(2017, 6, 2)
- Point2D(1, 10) == (1, 10)
- Accidental iteration, which makes it difficult to add fields
- No option for mutable instances
- Cannot specify default values
- Cannot control which fields are used for hash, repr, etc.

why not attrs
-------------

- attrs is constrained in using new language features, Data Classes
  can use features that are only in the newest version of Python.

- Syntax is simpler if using variable annotations

why not typing.NamedTuple
-------------------------

This produces a namedtuple, so it shares namedtuple's benefits and
some of its downsides.  For classes with statically defined fields, it
does support the more familiar class creation syntax, including type
annotations.  However, its use of metaclasses sometimes makes it
difficult to use in certain inheritance scenarios.

Dynamic creation of classes
---------------------------

An earlier version of this PEP and the sample implementation provided
a ``make_class`` function that dynamically created Data Classes.  This
functionality was later dropped, although it might be added at a later
time as a helper function.  The ``@dataclass`` decorator does not care
how classes are created, so they could be either statically defined or
dynamically defined.  For this Data Class::

  @dataclass
  class C:
      x: int
      y: int = field(init=False, default=0)

Here's is one way of dynamically creating the same Data Class::

  cls_dict = {'__annotations__': OrderedDict(x=int, y=int,),
              'y': field(init=False, default=0),
              }
  C = dataclass(type('C', (object,), cls_dict))


Examples from Python's source code
==================================

(or, from other projects)


Acknowledgements
================
Ivan Levkivskyi,
Hynek Schlawack,
Guido van Rossum,
Raymond Hettinger,
attrs project

References
==========

.. [#] attrs project on github
       (https://github.com/python-attrs/attrs)

.. [#] DictDotLookup recipe
       (http://code.activestate.com/recipes/576586-dot-style-nested-lookups-over-dictionary-based-dat/)

.. [#] attrdict package
       (https://pypi.python.org/pypi/attrdict)

.. [#] StackOverflow question about data container classes
       (https://stackoverflow.com/questions/3357581/using-python-class-as-a-data-container)

.. [#] David Beazley metaclass talk featuring data classes
       (https://www.youtube.com/watch?v=sPiWg5jSoZI)

.. [#] Start of python-ideas discussion
       (https://mail.python.org/pipermail/python-ideas/2017-May/045618.html)

.. [#] GitHub repo where discussions and initial development took place
       (https://github.com/ericvsmith/dataclasses)

Copyright
=========

This document has been placed in the public domain.


..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   coding: utf-8
   End:
