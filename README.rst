This is an implementation of PEP 557, Data Classes.  It is a backport
for Python 3.6.

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
