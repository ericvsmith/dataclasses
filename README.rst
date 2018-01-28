This is an implementation of PEP 557, Data Classes.  It is a backport
for Python 3.6.  Version 0.4 matches Python 3.7 beta 1.

See https://www.python.org/dev/peps/pep-0557/ for the details.

A test file can be found at
https://github.com/ericvsmith/dataclasses/blob/master/test_dataclasses.py,
or in the sdist file.

Example::

  from dataclasses import dataclass, field
  @dataclass
  class InventoryItem:
      name: str
      unit_price: float
      quantity_on_hand: int = 0

      def total_cost(self) -> float:
          return self.unit_price * self.quantity_on_hand

  item = InventoryItem('hammers', 10.49, 12)
  print(item.total_cost())

Some additional tools can be found in dataclass_tools.py, included in
the sdist.

Compatibility
-------------

This backport assumes that dict objects retain their sort order.  This
is true in the language spec for Python 3.7 and greater.  Since this
is a backport to Python 3.6, it raises an interesting question: does
that guarantee apply to 3.6?  For CPython 3.6 it does.  As of the time
of this writing, it's also true for all other Python implementations
that claim to be 3.6 compatible, of which there are none.  See the
analysis at the end of this email:

https://mail.python.org/pipermail/python-dev/2017-December/151325.html

As of version 0.4, this code no longer works with Python 3.7. For 3.7,
use the built-in dataclasses module.
