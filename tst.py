#!/usr/bin/env python3.6

from dataclass import dataclass, field

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

        # XXX: should raise an error to instantiate? or just ignored?

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

    def test_overwrite_fields_in_derived_class(self):
        # Note that x from C1 replaces x in Base, but the order remains
        #  the same as defined in Base.
        @dataclass
        class Base:
            x: str = 'base'
            y: int = 0

        @dataclass
        class C1(Base):
            z: int = 10
            x: int = 15

        o = C1()
        self.assertEqual(repr(o), 'C1(x=15,y=0,z=10)')

        o = C1(x=5)
        self.assertEqual(repr(o), 'C1(x=5,y=0,z=10)')

    def test_0_field_cmp(self):
        @dataclass
        class C:
            pass
        self.assertEqual(C(), C())
#        self.assertNotEqual(C(), C())
#        self.assertLess(C(), C())

    def test_1_field_cmp(self):
        @dataclass
        class C:
            x: int
        self.assertEqual(C(1), C(1))
        self.assertNotEqual(C(0), C(1))
        self.assertLess(C(0), C(1))
        self.assertLessEqual(C(0), C(1))
        self.assertLessEqual(C(1), C(1))
        self.assertGreater(C(1), C(0))
        self.assertGreaterEqual(C(1), C(0))
        self.assertGreaterEqual(C(1), C(1))

    def test_simple_cmp(self):
        @dataclass
        class C:
            x: int
            y: int
        self.assertEqual(C(0, 0), C(0, 0))
        self.assertEqual(C(1, 2), C(1, 2))
        self.assertNotEqual(C(1, 0), C(0, 0))
        self.assertLess(C(0, 0), C(0, 1))
        self.assertLess(C(0, 0), C(1, 0))
        self.assertLessEqual(C(0, 0), C(0, 1))
        self.assertLessEqual(C(0, 1), C(0, 1))
        self.assertLessEqual(C(0, 0), C(1, 0))
        self.assertLessEqual(C(1, 0), C(1, 0))
        self.assertGreater(C(0, 1), C(0, 0))
        self.assertGreater(C(1, 0), C(0, 0))
        self.assertGreaterEqual(C(0, 1), C(0, 0))
        self.assertGreaterEqual(C(0, 1), C(0, 1))
        self.assertGreaterEqual(C(1, 0), C(0, 0))
        self.assertGreaterEqual(C(1, 0), C(1, 0))

        # XXX: These all test operator returning True. What about operator returning False

    def test_0_field_hash(self):
        @dataclass
        class C:
            pass
        self.assertEqual(hash(C()), hash(()))

    def test_1_field_hash(self):
        @dataclass
        class C:
            x: int
        self.assertEqual(hash(C(4)), hash((4,)))
        self.assertEqual(hash(C(42)), hash((42,)))

    def test_hash(self):
        @dataclass
        class C:
            x: int
            y: str
        self.assertEqual(hash(C(1, 'foo')), hash((1, 'foo')))

    def test_field_no_default(self):
        @dataclass
        class C:
            x: int = field()

        self.assertEqual(repr(C(5)), 'C(x=5)')

        with self.assertRaises(TypeError) as ex:
            C()
        self.assertEqual(str(ex.exception),
                         "__init__() missing 1 required positional argument: "
                         "'x'")

    def test_field_default(self):
        default = object()
        @dataclass
        class C:
            x: object = field(default=default)

        self.assertIs(C.x, default)
        c = C(10)
        self.assertEqual(repr(c), 'C(x=10)')
        self.assertEqual(c.x, 10)

        # If we delete the instance attribute, we should then see the
        #  class attribute.
        del c.x
        self.assertIs(c.x, default)

    def test_not_in_repr(self):
        @dataclass
        class C:
            x: int = field(repr=False)
        with self.assertRaises(TypeError):
            C()
        c = C(10)
        self.assertEqual(repr(c), 'C()')

        @dataclass
        class C:
            x: int = field(repr=False)
            y: int
        c = C(10, 20)
        self.assertEqual(repr(c), 'C(y=20)')

    def test_not_in_init(self):
        # If init=False, we must have a default value.
        # Otherwise, how would it get initialized?
        with self.assertRaises(ValueError) as ex:
            @dataclass
            class C:
                x: int = field(init=False)
        self.assertEqual(str(ex.exception), 'field x has init=False, but has no default value')

        with self.assertRaises(ValueError) as ex:
            @dataclass
            class C:
                x: int
                y: int = 0
                z: int = field(init=False)
                t: int
        self.assertEqual(str(ex.exception), 'field z has init=False, but has no default value')

    def test_class_marker(self):
        @dataclass
        class C:
            x: int
            y: str = field(init=False, default=None)
            z: str = field(repr=False)

        # __dataclass_fields__ is a list of 3 elements, all of which are in __annotations__
        self.assertIsInstance(C.__dataclass_fields__, list)
        for f in C.__dataclass_fields__:
            self.assertIn(f.name, C.__annotations__)

        self.assertEqual(len(C.__dataclass_fields__), 3)
        self.assertEqual(C.__dataclass_fields__[0].name, 'x')
        self.assertTrue (C.__dataclass_fields__[0].init)
        self.assertTrue (C.__dataclass_fields__[0].repr)
        self.assertEqual(C.__dataclass_fields__[1].name, 'y')
        self.assertFalse(C.__dataclass_fields__[1].init)
        self.assertTrue (C.__dataclass_fields__[1].repr)
        self.assertEqual(C.__dataclass_fields__[2].name, 'z')
        self.assertTrue (C.__dataclass_fields__[2].init)
        self.assertFalse(C.__dataclass_fields__[2].repr)

    def test_mutable_defaults(self):
        @dataclass
        class C:
            l: list = []

        o1 = C()
        o2 = C()
        self.assertEqual(o1, o2)
        o1.l.extend([1, 2])
        self.assertNotEqual(o1, o2)
        self.assertEqual(o1.l, [1, 2])
        self.assertEqual(o2.l, [])

    def XXX_test_default_identity(self):
        class MyClass:
            pass
        m = MyClass()

        @dataclass
        class C:
            x: MyClass = m

        c = C()
        self.assertIs(c.x, m)

    def test_no_options(self):
        # call with dataclass()
        @dataclass()
        class C:
            x: int

        self.assertEqual(repr(C(42)), 'C(x=42)')


def main():
    unittest.main()


if __name__ == '__main__':
    main()
