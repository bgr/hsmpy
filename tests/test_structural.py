import pytest
from hsmpy.logic import (get_events,
                         get_state_by_sig,
                         get_incoming_transitions,
                         flatten,
                         duplicates)
from hsmpy.validation import (find_duplicate_sigs,
                              find_nonexistent_transition_sources,
                              find_nonexistent_transition_targets,
                              find_missing_initial_transitions,
                              find_invalid_initial_transitions,
                              find_invalid_local_transitions,
                              find_unreachable_states)

from hsmpy import Initial, Event
from hsmpy import InternalTransition as Internal
from hsmpy import Transition as T
from hsmpy import LocalTransition as Local
from hsmpy import State, HSM
from reusable import (make_miro_machine, make_nested_machine, leaf, composite,
                      orthogonal, A, B, C, D, E, F, G, H, I, TERMINATE, AB_ex,
                      AC_ex, BC_ex, AB_loc, AC_loc, BC_loc, BA_ex, CA_ex,
                      CB_ex, BA_loc, CA_loc, CB_loc)



class Test_find_duplicates(object):

    def test_empty(self):
        assert duplicates(None) == []
        assert duplicates([]) == []

    def test_no_duplicates(self):
        assert duplicates([1]) == []
        assert duplicates([1, 2, 3, 4]) == []

    def test_one_duplicate(self):
        assert duplicates([1, 1]) == [1]
        assert duplicates([1, 1, 2]) == [1]
        assert duplicates([1, 2, 1]) == [1]
        assert duplicates([2, 1, 1]) == [1]
        assert duplicates(list('abCdefgChi')) == ['C']

    def test_multiple_duplicates(self):
        dups = duplicates(list('abC_dEfgCh_iEjE__k'))
        assert sorted(dups) == sorted(['C', 'E', '_'])

    def test_duplicate_state_names(self):
        states = {
            'top': State({
                'left': State({
                    'left_A': State(),
                    'right': State(),
                    'left_B': State(),
                    'left': State(),
                }),
                'right': State({
                    'right_A': State(),
                    'right_B': State(),
                    'left': State(),
                }),
            }),
            'left_B': State(),
        }
        hsm = HSM(states, {}, skip_validation=True)
        # extract name from tuple
        dups = [name[-1] for name in find_duplicate_sigs(hsm.flattened)]
        assert sorted(dups) == sorted(['left', 'right', 'left_B'])



class Test_structural_analysis(object):

    def setup_class(self):
        states = {
            'top': State({  # bad initial transition (local)
                'left': State({  # no initial transition
                    'left_A': State(),
                    'left_B': State(),
                    'bad': State({ 'bad1': State() }),  # unreachable; missing
                                                        # initial transition
                }),
                'middle': State({  # bad initial transition (outside)
                    'mid_A': State(),       # both unreachable
                }),
                'ortho_unreachable': State([  # unreachable
                    ({ 'subunr1': State(), }, {} ),  # unreachable since
                    ({ 'subunr2': State(), }, {} ),  # parent is unreachable
                ]),
                'ortho': State([  # reachable (transition points to it)
                    ({ 'sub1': State(), }, {} ),  # reachable automaticlly
                    ({ 'sub2': State({ 'unr': State() }), }, {} ),
                                        # ^ unreachable (no tran to it)
                ]),
                'right': State({  # bad initial transition (loop)
                    'right_A': State(),  # unreachable (incoming also unreach.)
                    'right_B': State(),  # unreachable; only has self loop
                }),
            })
        }

        trans = {
            'top': {
                Initial: Local('left_B'),  # initial trans cannot be local
                C: Local('ortho')
            },
            'left': {  # no initial transition
                A: T('right'),
                B: T('left'),  # loop
                C: Internal(),
            },
            'right': {
                A: Local('left_A'),  # invalid (target not local)
                B: Local('right'),  # invalid loop (loop cannot be local)
                C: T('bad_target_1'),
                Initial: T('right'),  # inital transition cannot be loop
            },
            'middle': {
                Initial: T('top'),  # initial transition cannot go outside
                A: T('right_A'),  # this shouldn't make right_A reachable
                B: Internal(),
            },
            'bad_source_1': {
                A: Local('bad_target_2'),  # invalid, but omitted in check
                                           # since target state doesn't exist
            },
            'left_A': {
                A: T('left_A'),  # loop
                B: T('left'),
            },
            'left_B': {
                A: Local('left_A')  # invalid (not a parent-child relationship)
            },
            'right_A': {
                A: T('left_B'),
                B: Local('top'),
            },
            'right_B': {
                A: T('right_B'),  # loop
            },
            'bad_source_2': {
                A: T('left'),
                B: T('right'),
            },
        }
        self.hsm = HSM(states, trans, skip_validation=True)

    def test_get_state_by_sig(self):
        f = lambda nice: get_state_by_sig((nice,), self.hsm.flattened)
        assert f('top').name == 'top'
        assert f('left').name == 'left'
        assert f('mid_A').name == 'mid_A'
        assert f('right_B').name == 'right_B'

    def test_get_state_by_sig_in_orthogonal(self):
        f = lambda tup: get_state_by_sig(tup, self.hsm.flattened)
        assert f(('ortho',)).sig == ('ortho',)
        assert f(('ortho', 0, 'sub1')).sig == ('ortho', 0, 'sub1')
        assert f(('ortho', 1, 'sub2')).sig == ('ortho', 1, 'sub2')


    def test_get_incoming_trans(self):
        # exclude Transition objects from result tuples for cleaner checks
        def f(name, include_loops):
            res = [(src[-1], evt) for src, evt, _tran
                   in get_incoming_transitions((name,), self.hsm.trans,
                                               include_loops)]
            return sorted(res)

        assert f('top', False) == sorted([
            ('right_A', B),
            ('middle', Initial)])

        assert f('top', True) == sorted([
            ('right_A', B),
            ('middle', Initial)])

        assert f('left', False) == sorted([
            ('bad_source_2', A),
            ('left_A', B)])

        assert f('left', True) == sorted([
            ('bad_source_2', A),
            ('left_A', B),
            ('left', B)])

        assert f('right_B', False) == []
        assert f('right_B', True) == [('right_B', A)]


    def test_find_nonexistent_transition_sources(self):
        t = find_nonexistent_transition_sources(self.hsm.flattened,
                                                self.hsm.trans)
        assert sorted(t) == sorted([('bad_source_1',), ('bad_source_2',)])


    def test_find_nonexistent_transition_targets(self):
        t = find_nonexistent_transition_targets(self.hsm.flattened,
                                                self.hsm.trans)
        assert sorted(t) == sorted([('bad_target_1',), ('bad_target_2',)])


    def test_find_missing_initial_transitions(self):
        func = find_missing_initial_transitions
        names = [s.name for s in func(self.hsm.flattened, self.hsm.trans)]
        assert sorted(names) == sorted(['left', 'bad', 'ortho[1].sub2'])


    def test_find_invalid_initial_transitions(self):
        func = find_invalid_initial_transitions
        names = [s.name for s in func(self.hsm.flattened, self.hsm.trans)]
        assert sorted(names) == sorted(['top', 'middle', 'right'])


    def test_find_invalid_local_transitions(self):
        res_tuples = [(src[-1], evt, tran[-1]) for src, evt, tran
                      in find_invalid_local_transitions(self.hsm.flattened,
                                                        self.hsm.trans)]
        assert sorted(res_tuples) == sorted([
            ('left_B', 'A', 'left_A'),
            ('right', 'A', 'left_A'),
            ('right', 'B', 'right'),
        ])


    def test_find_unreachable_states(self):
        names = [st.name  # first element of tuple
                 for st in find_unreachable_states(self.hsm.root,
                                                   self.hsm.flattened,
                                                   self.hsm.trans)]
        expected = ['middle', 'mid_A', 'right_A', 'right_B', 'bad', 'bad1',
                    'ortho_unreachable', 'ortho_unreachable[0].subunr1',
                    'ortho_unreachable[1].subunr2', 'ortho[1].unr']
        assert sorted(names) == sorted(expected)


class Test_get_events(object):

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


class Test_get_events_with_subclasses(object):
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


class Test_flatten(object):
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



class Test_State_equals(object):
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


class Test_state_sig_and_name(object):
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
