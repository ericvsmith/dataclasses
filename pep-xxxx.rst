PEP: xxx
Title: Data classes
Author: Eric V. Smith <eric@trueblade.com>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 02-Jun-2017
Python-Version: 3.7
Post-History: 02-Jun-2017

Abstract
========

There have been numerous attempts to define classes which exist
primarily to store a set of attributes.  Some examples include:

- collection.namedtuple in the standard library.

- typing.NamedTuple in the standard library.

- The popular attrs [#]_ project.

- Many user recipes and packages such as [#]_ and [#]_.

This PEP describes an addition to the standard library called Data
Classes.  A Data Class is a normal Python class, specified using a
class decorator, that defines a series of fields.  Fields are
specified as class members using PEP 526, Syntax for Variable
Annotations.  The class decorator arranges for much of the class
boilerplate code to be automatically added to the Data Class.  Member
functions may be added to the Data Class.

As an example::

  @dataclass
  class Point:
      x: float
      y: float
      z: float = 0

      def distance(self, other):
          return ((self.x-other.x)**2 +
                  (self.y-other.y)**2 +
                  (self.z-other.z)**2) ** 0.5

Rationale
=========

With the addition of PEP 526, Python has a concise way to specify the
type of class members.  This PEP leverages that syntax to provide a
simple way to describe Data Classes.

why not namedtuple
------------------

Point3D(2017, 6, 2) == Date(2017, 6, 2)
Point2D(1, 10) == (1, 10)
Accidental iteration

why not attrs
-------------

Needs to support python 2 and python 3
Syntax is simpler if using variable annotations

why not typing.NamedTuple

Use normal Python syntax
------------------------

Expressiveness
--------------

Efficiency
----------

Dynamic creation
----------------

Module level helper functions
-----------------------------

Mutable defaults
----------------

Specification
=============

PEP 526 Variable Annotations
----------------------------

Generated functions contain variable annotations
------------------------------------------------

Generate __init__
-----------------

Generate __repr__
-----------------

Frozen classes
--------------

Generate __hash__ and __cmp__
-----------------------------

Mutable defaults
----------------

__dataclass_fields__ attribute
------------------------------

Only variable declarations are inspected, not methods or properties
-------------------------------------------------------------------

Even if they are annotated with return types.

Reserved field names
--------------------

make_class()
------------

post-init function
------------------

Take a parameter?

Valid field names
-----------------

Module helper functions
-----------------------

Discussion
==========

python-ideas discussion
-----------------------

This discussion started on python-ideas [#]_ and was moved to a GitHub
repo [#]_ for further discussion.

- New syntax rejected, PEP 526 give enough flexibility.

- Mutable defaults

- slots=True being the default

- Should post-init take params?


Examples from Python's source code
==================================


References
==========

.. [#] attrs project on github
       (https://github.com/python-attrs/attrs)

.. [#] DictDotLookup recipe
       (http://code.activestate.com/recipes/576586-dot-style-nested-lookups-over-dictionary-based-dat/)

.. [#] attrdict package
       (https://pypi.python.org/pypi/attrdict)

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
