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

This PEP was drafted in a separate repo:
https://github.com/ericvsmith/dataclasses.  Before commenting in a
public forum please at least read the `discussion`_ listed at the end
of this PEP.

Abstract
========

This PEP describes an addition to the standard library called Data
Classes.  A class decorator is provided which inspects a class
definition for variables annotated with PEP 526 "Syntax for Variable
Annotations".  In this document, such variables are called fields.
Using these fields, the decorator adds generated method definitions to
the class to support instance initialization, a repr, and comparisons
methods.  Such a class is called a Data Class, but there's really
nothing special about it: it is the same class but with the generated
methods added.

As an example::

  @dataclass
  class InventoryItem:
      name: str
      unit_price: float
      quantity_on_hand: int = 0

      def value(self) -> float:
          return self.unit_price * self.quantity_on_hand

The InventoryItem class will have the equivalent of these methods
added::

  def __init__(self, name:str, unit_price: float, quantity_on_hand: int = 0) -> None:
      self.name = name
      self.unit_price = unit_price
      self.quantity_on_hand = quantity_on_hand
  def __repr__(self):
      return f'InventoryItem(name={self.name!r},unit_price={self.unit_price!r},quantity_on_hand={self.quantity_on_hand!r})'
  def __eq__(self,other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) == (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __lt__(self,other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) < (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __le__(self,other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) <= (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __gt__(self,other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) > (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented
  def __ge__(self,other):
      if other.__class__ is self.__class__:
          return (self.name, self.unit_price, self.quantity_on_hand) >= (other.name, other.unit_price, other.quantity_on_hand)
      return NotImplemented

Data Classes saves you from writing and maintaining these functions.

Where is it not appopriate to use?  Maybe where you want immutable classes?

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

So, why is this needed?

With the addition of PEP 526, Python has a concise way to specify the
type of class members.  This PEP leverages that syntax to provide a
simple way to describe Data Classes.

What do we provide that people want, but don't find above?

Defining fields
---------------

Use normal Python syntax
------------------------

Expressiveness
--------------

Efficiency
----------

Class variables
---------------




Mutable defaults
----------------

Specification
=============

All of the functions described in this PEP will live in a module named
``dataclasses``.

The ``@dataclass`` decorator just makes the following changes to the
class.  It does not modify the class in any other way:

- Add a ``__init__`` method, based on the fields and their default values.
- Add a ``__repr__`` method.
- Add comparison functions:

  - ``__eq__``
  - ``__ne__``
  - ``__lt__``
  - ``__le__``
  - ``__gt__``
  - ``__ge__``

- Add a ``__hash__`` mehod.
- Adjust ``__annotations__`` to include base class fields.

Because a Data Class is just the defined class with some additional
added methods, it does not interfere with other Python features, such
as inheritance, metaclasses, etc.

@dataclass decorator
--------------------

Module level helper functions
-----------------------------

- fields
- asdict
- astuple

Notes
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
dynamically defined.  Here's an example of how to dynamically create a
Data Class::



Maybe just let the user create the class however they want, with __annotations__, then say cls = dataclass(cls)?

While the standard usage of Data Classes will be to use the
``@dataclass`` decorator on a class definition, it is also possible to
dynamically create a Data Class using the ``make_class`` function.  The signature is::

  def make_class(cls_name, fields, *, bases=None, repr=True, cmp=True,
                 hash=None, init=True, slots=False, frozen=False):

``cls_name`` is the name of the class to create.  ``fields`` is an
iterable of ``field`` objects.  If the class is to have base classes
other than ``object``, they are passed as the ``bases`` parameter.  The remaining parameter


Examples from Python's source code
==================================

(or, from other projects)


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
