PEP: xxx
Title: Data container classes
Author: Eric V. Smith <eric@trueblade.com>
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: 02-Jun-2017
Python-Version: 3.7
Post-History: 02-Jun-2017

Abstract
========

There have been numerous attempts to define classes exist primarily as containers for ...

Describe fields. This PEP proposes a module for defining data classes.

Rationale
=========

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

Reserved field names
--------------------

make_class()
------------

- Valid field names

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


Examples from Python's source code
==================================


References
==========

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
