#!/usr/bin/env python3.6

from dataclass import dataclass

import unittest

class TestCase(unittest.TestCase):
    def test_no_fields(self):
        @dataclass
        class C:
            pass

        o = C()
        self.assertEqual(repr(o), 'C()')

    def XXX_test_no_fields_with_init(self):
        pass

    def test_one_field_no_default(self):
        @dataclass
        class C:
            x: int

        o = C(42)
        self.assertEqual(o.x, 42)

    def test_named_init_params(self):
        @dataclass
        class C:
            x: int

        o = C(x=32)
        self.assertEqual(o.x, 32)

    def test_two_fields_one_default(self):
        @dataclass
        class C:
            x: int
            y: int=0

        o = C(3)
        self.assertEqual((o.x, o.y), (3, 0))

        # Non-defaults following defaults. XXX: Exception type?
        with self.assertRaises(ValueError) as ex:
            @dataclass
            class C:
                x: int=0
                y: int
        self.assertEqual(str(ex.exception), 'non-default argument y follows default argument')

    def XXX_test_overwriting_init(self):
        @dataclass
        class C:
            x: int
            def __init__(self, x):
                self.x = 2 * x

        # XXX: should raise an error to instantiate?

    def test_field_named_self(self):
        @dataclass
        class C:
            self: str
        c=C('foo')
        self.assertEqual(c.self, 'foo')

    def test_repr(self):
        @dataclass
        class B:
            x: int

        @dataclass
        class C(B):
            y: int = 10

        o = C(4)
        self.assertEqual(repr(o), 'C(x=4,y=10)')

    def test_overwrite_fields(self):
        @dataclass
        class Base:
            x: str = 'base'

        @dataclass
        class C1(Base):
            x: str = 'C1'

        o = C1()
        self.assertEqual(repr(o), "C1(x='C1')")

unittest.main()

