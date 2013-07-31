import pytest
from hsmpy.logic import (get_events,
                         flatten,)
from hsmpy import State, HSM, Event, Initial, Internal, T
from reusable import (make_miro_machine, make_nested_machine, leaf, composite,
                      orthogonal, A, B, C, D, E, F, G, H, I, TERMINATE, AB_ex,
                      AC_ex, BC_ex, AB_loc, AC_loc, BC_loc, BA_ex, CA_ex,
                      CB_ex, BA_loc, CA_loc, CB_loc)


class Test_get_events:

    def test_miro_machine_events(self):
        states, trans = make_miro_machine(use_logging=False)
        hsm = HSM(states, trans)
        event_set = get_events(hsm.flattened, trans)
        assert event_set == set([A, B, C, D, E, F, G, H, I, TERMINATE])

    def test_nested_machine_events(self):
        states, trans = make_nested_machine(False)
        hsm = HSM(states, trans)
        event_set = get_events(hsm.flattened, trans)
        assert event_set == set([A, B, C, AB_ex, AC_ex, BC_ex, AB_loc, AC_loc,
                                 BC_loc, BA_ex, CA_ex, CB_ex, BA_loc, CA_loc,
                                 CB_loc])


class RootEventA(Event): pass
class RootEventB(Event): pass
class RootEventC(Event): pass
class A1(RootEventA): pass
class A2(RootEventA): pass
class B1(RootEventB): pass
class C1(RootEventC): pass
class C2(RootEventC): pass
class C11(C1): pass
class C12(C1): pass
class C21(C2): pass
class C22(C2): pass
class Ignored(RootEventB): pass


class Test_get_events_with_subclasses:
    def setup_class(self):
        self.states = {
            'top': State({
                'left': State(),
                'right': State(),
            })
        }
        self.trans = {
            'top': {
                Initial: T('left'),
                A1: T('right'),
                B1: Internal(),
            },
            'left': {
                RootEventA: T('left'),  # also responds to A1 and A2
            },
            'right': {
                RootEventC: T('right'),  # also C1, C2, C11, C12, C21, C22
            }
        }
        self.hsm = HSM(self.states, self.trans)

    def test_get_events(self):
        event_set = get_events(self.hsm.flattened, self.trans)
        # RootEventB shouldn't appear in event_set since nobody explicitly
        # listens to it, only its subclasses
        assert event_set == set([RootEventA, RootEventC, A1, A2, B1, C1, C2,
                                 C11, C12, C21, C22])



class Test_flatten:
    def test_single_empty(self):
        assert flatten([]) == []

    def test_with_list(self):
        a = [1, 2, [3, 4, [5, 6], 7, [8, 9]], 10, [11, [12, 13]], 14]
        exp = list(range(1, 15))
        assert sorted(flatten(a)) == sorted(exp)

    def test_nested_empty(self):
        states = [
            composite('a', [
                orthogonal('submachines', [
                    composite('sub1', [
                        leaf('sub11'),
                        composite('sub12', [
                            leaf('sub121'),
                            leaf('sub122'),
                        ])
                    ]),
                    composite('sub2', [
                        leaf('sub21'),
                        composite('sub22', [
                            leaf('sub221'),
                            leaf('sub222'),
                        ]),
                    ]),
                ]),
                composite('b', [
                    leaf('b1')
                ]),
            ]),
            composite('c', [
                leaf('c1'),
                leaf('c2'),
            ]),
        ]
        names = [st.name for st in flatten(states)]
        expected = ['a', 'submachines', 'sub1', 'sub11', 'sub12', 'sub121',
                    'sub122', 'sub2', 'sub21', 'sub22', 'sub221', 'sub222',
                    'b', 'b1', 'c', 'c1', 'c2']
        assert len(names) == len(expected)
        assert set(names) == set(expected)

    def test_flatten_miro_machine(self):
        states, trans = make_miro_machine(use_logging=False)

        hsm = HSM(states, trans)
        names = [st.name for st in hsm.flattened]
        assert sorted(names) == sorted(['top', 'final', 's', 's1', 's11', 's2',
                                        's21', 's211'])



class Test_State_equals:
    def test_fresh(self):
        assert State() == State()

    def test_names(self):
        s1 = State()
        s1.name = 'asd'
        s2 = State()
        assert not s1 == s2
        s2.name = 'asd'
        assert s1 == s2

    def test_all_attribs(self):
        par1 = State()
        par1.name = 'parent'
        par2 = State()
        par2.name = 'parent'
        assert par1 == par2

        # lambdas must be same instance
        action = lambda a, b: a + b

        s1 = State()
        s1.name = 'name'
        s1.parent = par1
        s1.kind = 'leaf'
        s1.on_enter = action
        s1.on_exit = action

        s2 = State()
        assert not s1 == s2
        s2.name = 'name'
        assert not s1 == s2
        s2.parent = par1
        assert not s1 == s2
        s2.kind = 'leaf'
        assert not s1 == s2
        s2.on_enter = action
        assert not s1 == s2
        s2.on_exit = action
        assert s1 == s2  # now it's same

    def test_children_empty(self):
        s1 = State()
        s2 = State()

        s1.states = []
        assert not s1 == s2  # s2 has {}
        s2.states = []
        assert s1 == s2

    def test_children_dict(self):
        s1 = State()
        s2 = State()
        s1.states = {1: 'a', 2: {}}
        s2.states = {1: 'a', 2: {}}
        assert s1 == s2
        s1.states = {1: 'a', 2: {3: {}}}
        assert not s1 == s2

        s1.states = [State(), State()]
        s2.states = [State(), State()]
        assert s1 == s2

        s1.states = { 'a': State(), 'b': State() }
        s2.states = { 'a': State(), 'b': State() }
        assert s1 == s2

    def test_children_dict_nested(self):
        s1 = State()
        s2 = State()
        s1.states = {
            'a': State({
                's': State(),
                's2': State() }),
            'b': State()
        }
        assert not s1 == s2
        s2.states = {
            'a': State({
                's': State(),
                's2': State() }),
            'b': State()
        }
        assert s1 == s2

    def test_children_list_different_order(self):
        s1 = State()
        s2 = State()
        s1.states = [leaf('1'), leaf('2'), leaf('3')]
        s2.states = [leaf('1'), leaf('2'), leaf('3')]
        assert s1 == s2
        s2.states = [leaf('3'), leaf('1'), leaf('2')]
        assert s1 == s2
        s2.states = [leaf('3'), leaf('999'), leaf('2')]
        assert not s1 == s2

    def test_children_list_nested(self):
        s1 = State()
        s2 = State()
        s1.states = [
            State([State(), State()]),
            State([State(), State()]),
        ]
        s2.states = [
            State([State()]),
            State([State(), State()]),
        ]
        assert not s1 == s2
        s2.states = [
            State([State(), State()]),
            State([State(), State()]),
        ]
        assert s1 == s2

    def test_children_list_different_order_nested(self):
        s1 = State()
        s2 = State()
        s1.states = [
            composite('A', [leaf('1'), leaf('2')]),
            composite('B', [leaf('3'), leaf('4')]),
        ]
        s2.states = [
            composite('A', [leaf('2'), leaf('1')]),
            composite('B', [leaf('4'), leaf('3')]),
        ]
        assert s1 == s2
        s2.states = [
            composite('B', [leaf('4'), leaf('3')]),
            composite('A', [leaf('2'), leaf('1')]),
        ]
        assert s1 == s2
        s2.states = [
            composite('B', [leaf('4'), leaf('3')]),
            composite('A', [leaf('999'), leaf('1')]),
        ]
        assert not s1 == s2

    def test_with_different_subclasses(self):
        class SubState(State):
            pass

        s1 = State()
        s2 = SubState()
        assert not s1 == s2

        s1 = SubState()
        s2 = SubState()
        assert s1 == s2

        s1.states = {
            'a': State({
                's': State(),
                's2': State() }),
            'b': State()
        }
        s2.states = {
            'a': State({
                's': SubState(),
                's2': State() }),
            'b': State()
        }
        assert not s1 == s2
        s1.states = {
            'a': State({
                's': SubState(),
                's2': State() }),
            'b': State()
        }
        assert s1 == s2



class Test_state_sig_and_name:
    @pytest.mark.parametrize(('sig', 'name'), [
        ((), ''),
        (('',), ''),
        (('a',), 'a'),
        (('Hello, world!',), 'Hello, world!'),
        ((1,), '1'),
        (('a', 0), 'a[0]'),
        (('hello', 345), 'hello[345]'),
        (('a', 2, 'sub'), 'a[2].sub'),
        (('a', 2, 'sub', 3), 'a[2].sub[3]'),
        (('A', 2, 'sub', 3, 'enough'), 'A[2].sub[3].enough'),
    ])
    def test_sig_to_name(self, sig, name):
        assert State.sig_to_name(sig) == name

    @pytest.mark.parametrize(('sig', 'name'), [
        (('a',), 'a'),
        (('Hello, world!',), 'Hello, world!'),
        (('asd',), '  asd  '),
        (('asd bb',), '  asd bb '),
        (('1',), '1'),
        (('a', 2, 'sub'), 'a[2].sub'),
        (('a', 2, 'sub'), '   a   [ 2]  .   sub   '),
        (('A', 2, 'sub', 3, 'sub   sub'), 'A [ 2 ] . sub [3 ] . sub   sub '),
        (('A', 2, 'S  U B', 3, 'sub sub'), '  A[2].  S  U B [3].  sub sub  '),
    ])
    def test_name_to_sig(self, sig, name):
        assert State.name_to_sig(name) == sig

    @pytest.mark.parametrize(('name'), [
        '',
        ' ',
        'a[0]',
        'asd[3]',
        'asd[3].',
        'asd[3]. ',
        'a[2].sub[3]',
        'A[2].sub[3].subsub[4]',
        '[0]',
        '[0].sub',
        'asd[',
        'asd[].sub',
        'asd[-1].sub',
        '.',
        '',
        '   . ',
        '[',
        ']',
        'asd[asd',
        'asd]asd',
        'a[[0].sub',
        'a[0]].sub',
        'a[[0]].sub',
        'a[1 2].sub',
        'a[1 asd[1].sub ].sub',
        'asd.asdf',
        'a.sd[3]',
        'asd[3].',
        'asd[3].asd.',
        'asd[3].asd.asd',
        'asd[3].asd.asd[0].asd',
        'asd[3][4]',
        'asd[3][4].',
        'asd[3][4].asd',
    ])
    def test_name_to_sig_malformed(self, name):
        with pytest.raises(ValueError):
            res = State.name_to_sig(name)
            print res
