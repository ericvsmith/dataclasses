#!/usr/bin/env python3.6

from dataclass import dataclass, field, make_class

import unittest

class TestCase(unittest.TestCase):
    def test_no_fields(self):
        @dataclass
        class C:
            pass

        o = C()
        self.assertEqual(repr(o), 'C()')

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

    def test_overwriting_init(self):
        @dataclass
        class C:
            x: int
            def __init__(self, x):
                self.x = 2 * x

        # XXX: should raise an error to instantiate? or just work by overwriting the given __init__?
        self.assertEqual(C(10).x, 10)

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

        @dataclass
        class D(C):
            x: int = 20
        self.assertEqual(repr(D()), 'D(x=20,y=10)')

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
        self.assertLessEqual(C(), C())
        self.assertGreaterEqual(C(), C())

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

        # For operators returning False, we have to use assertFalse.
        self.assertFalse(C(0, 1) < C(0, 0))
        self.assertFalse(C(1, 0) < C(0, 0))
        self.assertFalse(C(0, 1) <= C(0, 0))
        self.assertFalse (C(0, 2) <= C(0, 1))
        self.assertFalse(C(1, 0) <=  C(0, 0))
        self.assertFalse(C(0, 0) > C(0, 1))
        self.assertFalse(C(0, 0) > C(1, 0))
        self.assertFalse(C(0, 0) >= C(0, 1))
        self.assertFalse(C(0, 0) >= C(0, 1))
        self.assertFalse(C(0, 0) >= C(1, 0))

    def test_0_field_hash(self):
        @dataclass(hash=True)
        class C:
            pass
        self.assertEqual(hash(C()), hash(()))

    def test_1_field_hash(self):
        @dataclass(hash=True)
        class C:
            x: int
        self.assertEqual(hash(C(4)), hash((4,)))
        self.assertEqual(hash(C(42)), hash((42,)))

    def test_hash(self):
        @dataclass(hash=True)
        class C:
            x: int
            y: str
        self.assertEqual(hash(C(1, 'foo')), hash((1, 'foo')))

    def test_no_hash(self):
        @dataclass(hash=None)
        class C:
            x: int
        with self.assertRaises(TypeError) as ex:
            hash(C(1))
        self.assertEqual(str(ex.exception), "unhashable type: 'C'")

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

    def test_not_in_cmp(self):
        @dataclass
        class C:
            x: int = 0
            y: int = field(cmp=False, default=4)

        self.assertEqual(C(), C(0, 20))
        self.assertEqual(C(1, 10), C(1, 20))
        self.assertNotEqual(C(3), C(4, 10))
        self.assertNotEqual(C(3, 10), C(4, 10))

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

        # And the equivalent dynamically created class:
        D = make_class('D',
                       [field('x', int),
                        field('y', str, init=False, default=None),
                        field('z', str, repr=False),
                        ])

        for cls in C, D:
            # __dataclass_fields__ is a list of 3 elements, all of which are in __annotations__
            self.assertIsInstance(cls.__dataclass_fields__, list)
            for f in cls.__dataclass_fields__:
                self.assertIn(f.name, cls.__annotations__)

            self.assertEqual(len(cls.__dataclass_fields__), 3)
            self.assertEqual(cls.__dataclass_fields__[0].name, 'x')
            self.assertEqual(cls.__dataclass_fields__[0].type, int)
            self.assertFalse(hasattr(cls, 'x'))
            self.assertTrue (cls.__dataclass_fields__[0].init)
            self.assertTrue (cls.__dataclass_fields__[0].repr)
            self.assertEqual(cls.__dataclass_fields__[1].name, 'y')
            self.assertEqual(cls.__dataclass_fields__[1].type, str)
            self.assertIsNone(getattr(cls, 'y'))
            self.assertFalse(cls.__dataclass_fields__[1].init)
            self.assertTrue (cls.__dataclass_fields__[1].repr)
            self.assertEqual(cls.__dataclass_fields__[2].name, 'z')
            self.assertEqual(cls.__dataclass_fields__[2].type, str)
            self.assertFalse(hasattr(cls, 'z'))
            self.assertTrue (cls.__dataclass_fields__[2].init)
            self.assertFalse(cls.__dataclass_fields__[2].repr)

    def test_field_order(self):
        @dataclass
        class B:
            a: str = 'B:a'
            b: str = 'B:b'
            c: str = 'B:c'

        @dataclass
        class C(B):
            b: str = 'C:b'

        self.assertEqual([(f.name, f.default) for f in C.__dataclass_fields__],
                         [('a', 'B:a'),
                          ('b', 'C:b'),
                          ('c', 'B:c')])

        @dataclass
        class D(B):
            c: str = 'D:c'

        self.assertEqual([(f.name, f.default) for f in D.__dataclass_fields__],
                         [('a', 'B:a'),
                          ('b', 'B:b'),
                          ('c', 'D:c')])

        @dataclass
        class E(D):
            a: str = 'E:a'
            d: str = 'E:d'

        self.assertEqual([(f.name, f.default) for f in E.__dataclass_fields__],
                         [('a', 'E:a'),
                          ('b', 'B:b'),
                          ('c', 'D:c'),
                          ('d', 'E:d')])

    def test_class_attrs(self):
        # We only have a class attribute if a default value is
        #  specified, either directly or via a field with a default.
        default = object()
        @dataclass
        class C:
            x: int
            y: int = field(repr=False)
            z: object = default
            t: int = field(default=100)

        self.assertFalse(hasattr(C, 'x'))
        self.assertFalse(hasattr(C, 'y'))
        self.assertIs   (C.z, default)
        self.assertEqual(C.t, 100)

    def XXX_test_mutable_defaults(self):
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

    def test_default_identity(self):
        class MyClass:
            pass
        m = MyClass()

        @dataclass
        class C:
            x: MyClass = m

        c = C()
        self.assertIs(c.x, m)
        c = C(None)
        self.assertIsNone(c.x)

    def test_no_options(self):
        # call with dataclass()
        @dataclass()
        class C:
            x: int

        self.assertEqual(repr(C(42)), 'C(x=42)')

    def test_not_tuple(self):
        # Make sure we can't be compared to a tuple.
        @dataclass
        class Point:
            x: int
            y: int
        self.assertNotEqual(Point(1, 2), (1, 2))

        # And that we can't compare to another unrelated dataclass
        @dataclass
        class C:
            x: int
            y: int
        self.assertNotEqual(Point(1, 3), C(1, 3))

    def test_no_name_or_type(self):
        with self.assertRaises(ValueError) as ex:
            @dataclass
            class Point:
                x: int = field('x')
        self.assertEqual(str(ex.exception), 'cannot specify name or type '
                                            "for 'x'")

        with self.assertRaises(ValueError) as ex:
            @dataclass
            class Point:
                x: int = field(type=str)
        self.assertEqual(str(ex.exception), 'cannot specify name or type '
                                            "for 'x'")

    def test_make_simple(self):
        C = make_class('C', 'a b')
        self.assertEqual(repr(C(1, 2)), 'C(a=1,b=2)')

    def test_make_derived(self):
        @dataclass
        class Base:
            x: int
            y: int

        C = make_class('C',
                       [field('z', int),
                        field('x', int),
                        ],
                       bases=(Base,))
        self.assertEqual(repr(C(4,5,6)), 'C(x=4,y=5,z=6)')

    def test_make_derived_defaults(self):
        @dataclass
        class Base:
            x: int = 5
            y: int = 20

        C = make_class('C',
                       [field('z', int, default=30),
                        field('x', int, default=10),
                        ],
                       bases=(Base,))
        self.assertEqual(repr(C()), 'C(x=10,y=20,z=30)')

        C = make_class('C',
                       [field('z', int, default=30),
                        field('x', int, default=10, init=False),
                        ],
                       bases=(Base,))
        self.assertEqual(repr(C(1)), 'C(x=10,y=1,z=30)')

    def test_make_invalid_fields(self):
        with self.assertRaises(ValueError) as ex:
            C = make_class('C',
                           [field('x', int),
                            field(),
                            ])
        self.assertEqual(str(ex.exception), 'name must be specified for field #2')

        with self.assertRaises(ValueError) as ex:
            C = make_class('C',
                           [field('x'),
                            ])
        self.assertEqual(str(ex.exception), "type must be specified for field 'x'")

    def test_slots(self):
        @dataclass(slots=True)
        class C:
            x: int
            y: int = 0

        c = C(10)
        self.assertEqual(C.__slots__, ('x', 'y'))
        self.assertEqual(c.__slots__, ('x', 'y'))
        c.x = 4
        c.y = 12
        self.assertEqual(repr(c), 'C(x=4,y=12)')

        with self.assertRaises(AttributeError) as ex:
            c.z = 0
        self.assertEqual(str(ex.exception), "'C' object has no attribute 'z'")

    def test_no_slots(self):
        @dataclass
        class C:
            pass
        # We can create new member variables
        C().x = 3

        # Same behavior with slots=False
        @dataclass(slots=False)
        class C:
            pass
        # We can create new member variables
        C().x = 3

        # Even though we can create a new member, it's not included in
        #  the equality check, since it's not a field.
        a = C()
        a.x = 10
        b = C()
        b.x = ''
        self.assertEqual(a, b)

def main():
    unittest.main()


if __name__ == '__main__':
    main()
