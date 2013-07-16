from hsmpy.statemachine import (_get_path,
                                _get_path_from_root,
                                _get_common_parent,
                                _get_events,
                                _get_state_by_name,
                                _get_incoming_transitions,
                                _find_duplicates,
                                _find_duplicate_names,
                                _find_nonexistent_transition_sources,
                                _find_nonexistent_transition_targets,
                                _find_missing_initial_transitions,
                                _find_invalid_initial_transitions,
                                _find_invalid_local_transitions,
                                _find_unreachable_states,
                                _flatten,
                                _reformat,
                                )

from hsmpy import Initial, Event
from hsmpy import InternalTransition as Internal
from hsmpy import Transition as T
from hsmpy import LocalTransition as Local
from hsmpy import State, HSM
from predefined_machines import make_miro_machine, make_nested_machine
from predefined_machines import (A, B, C, D, E, F, G, H, I, TERMINATE, AB_ex,
                                 AC_ex, BC_ex, AB_loc, AC_loc, BC_loc, BA_ex,
                                 CA_ex, CB_ex, BA_loc, CA_loc, CB_loc)


class MockState(object):
    def __init__(self, parent):
        self.parent = parent


class Test_get_path(object):

    def test_branching(self):
        root = MockState(parent=None)

        left = MockState(parent=root)
        left_A = MockState(parent=left)
        left_B = MockState(parent=left)

        middle = MockState(parent=root)
        middle_A = MockState(parent=middle)

        right = MockState(parent=root)
        right_A = MockState(parent=right)
        right_A_1 = MockState(parent=right_A)
        right_A_2 = MockState(parent=right_A)

        assert _get_path(root, root) == ([], root, [])
        assert _get_path(left, left) == ([], left, [])
        assert _get_path(left_A, left_B) == ([left_A], left, [left_B])
        assert _get_path(left_B, left_A) == ([left_B], left, [left_A])
        assert _get_path(middle, root) == ([middle], root, [])
        assert _get_path(root, middle) == ([], root, [middle])
        assert _get_path(middle_A, left_A) == ([middle_A, middle],
                                               root, [left, left_A])
        assert _get_path(right_A_1, left) == ([right_A_1, right_A, right],
                                              root, [left])
        assert _get_path(right_A_2, left_B) == ([right_A_2, right_A, right],
                                                root, [left, left_B])
        assert _get_path(left_B, right_A_2) == ([left_B, left], root,
                                                [right, right_A, right_A_2])
        assert _get_path(right_A, root) == ([right_A, right], root, [])
        assert _get_path(root, right_A) == ([], root, [right, right_A])

    def test_with_HSM_instance(self):
        states = {
            'root': State({
                'left': State({
                    'left_A': State(),
                    'left_B': State(),
                }),
                'middle': State({
                    'middle_A': State(),
                    'middle_B': State(),
                    'middle_C': State(),
                }),
                'right': State({
                    'right_A': State({
                        'right_A_1': State(),
                        'deep': State(),
                        'right_A_2': State(),
                    }),
                    'right_B': State(),
                })
            })
        }

        flattened = HSM(states, {}, skip_validation=True).flattened

        left_B = _get_state_by_name(('left_B',), flattened)
        deep = _get_state_by_name(('deep',), flattened)

        exits, parent, entries = _get_path(deep, left_B)
        exits = [st.name[0] for st in exits]
        entries = [st.name[0] for st in entries]

        assert exits == ['deep', 'right_A', 'right']
        assert parent.name[0] == 'root'
        assert entries == ['left', 'left_B']


class Test_get_path_from_root(object):

    def test_single_node(self):
        root = MockState(parent=None)
        assert _get_path_from_root(root) == [root]

    def test_one_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        assert _get_path_from_root(root) == [root]
        assert _get_path_from_root(ch_1) == [root, ch_1]

    def test_multiple_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        ch_2 = MockState(parent=ch_1)
        ch_3 = MockState(parent=ch_2)
        ch_4 = MockState(parent=ch_3)
        assert _get_path_from_root(root) == [root]
        assert _get_path_from_root(ch_1) == [root, ch_1]
        assert _get_path_from_root(ch_2) == [root, ch_1, ch_2]
        assert _get_path_from_root(ch_3) == [root, ch_1, ch_2, ch_3]
        assert _get_path_from_root(ch_4) == [root, ch_1, ch_2, ch_3, ch_4]

    def test_branching(self):
        root = MockState(parent=None)

        left = MockState(parent=root)
        left_A = MockState(parent=left)
        left_B = MockState(parent=left)

        middle = MockState(parent=root)
        middle_A = MockState(parent=middle)
        middle_B = MockState(parent=middle)
        middle_C = MockState(parent=middle)

        right = MockState(parent=root)
        right_A = MockState(parent=right)
        right_B = MockState(parent=right)
        right_A_1 = MockState(parent=right_A)
        right_A_2 = MockState(parent=right_A)

        assert _get_path_from_root(left) == [root, left]
        assert _get_path_from_root(left_A) == [root, left, left_A]
        assert _get_path_from_root(left_B) == [root, left, left_B]
        assert _get_path_from_root(middle) == [root, middle]
        assert _get_path_from_root(middle_A) == [root, middle, middle_A]
        assert _get_path_from_root(middle_B) == [root, middle, middle_B]
        assert _get_path_from_root(middle_C) == [root, middle, middle_C]
        assert _get_path_from_root(right) == [root, right]
        assert _get_path_from_root(right_A) == [root, right, right_A]
        assert _get_path_from_root(right_B) == [root, right, right_B]
        assert _get_path_from_root(right_A_1) == [root, right, right_A,
                                                  right_A_1]
        assert _get_path_from_root(right_A_2) == [root, right, right_A,
                                                  right_A_2]

    def test_with_HSM_instance(self):
        states = {
            'root': State({
                'left': State({
                    'left_A': State(),
                    'left_B': State(),
                }),
                'middle': State({
                    'middle_A': State(),
                    'middle_B': State(),
                    'middle_C': State(),
                }),
                'right': State({
                    'right_A': State({
                        'right_A_1': State(),
                        'deep': State(),
                        'right_A_2': State(),
                    }),
                    'right_B': State(),
                })
            })
        }

        flattened = HSM(states, {}, skip_validation=True).flattened
        deep = _get_state_by_name(('deep',), flattened)
        state_names = [state.name[0] for state in _get_path_from_root(deep)]
        assert state_names == ['root', 'right', 'right_A', 'deep']


class Test_get_common_parent(object):

    def test_single_node(self):
        root = MockState(parent=None)
        assert _get_common_parent(root, root) == root

    def test_one_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        assert _get_common_parent(root, ch_1) == root
        assert _get_common_parent(ch_1, root) == root
        assert _get_common_parent(ch_1, ch_1) == ch_1

    def test_multiple_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        ch_2 = MockState(parent=ch_1)
        ch_3 = MockState(parent=ch_2)
        ch_4 = MockState(parent=ch_3)
        assert _get_common_parent(root, ch_2) == root
        assert _get_common_parent(ch_2, root) == root
        assert _get_common_parent(ch_1, ch_2) == ch_1
        assert _get_common_parent(ch_2, ch_1) == ch_1
        assert _get_common_parent(ch_1, ch_3) == ch_1
        assert _get_common_parent(ch_3, ch_1) == ch_1
        assert _get_common_parent(ch_4, ch_3) == ch_3
        assert _get_common_parent(ch_3, ch_4) == ch_3
        assert _get_common_parent(ch_1, ch_4) == ch_1
        assert _get_common_parent(root, ch_4) == root

    def test_branching(self):
        root = MockState(parent=None)

        left = MockState(parent=root)
        left_A = MockState(parent=left)
        left_B = MockState(parent=left)

        middle = MockState(parent=root)
        middle_A = MockState(parent=middle)

        right = MockState(parent=root)
        right_A = MockState(parent=right)
        right_A_1 = MockState(parent=right_A)
        right_A_2 = MockState(parent=right_A)

        right_B = MockState(parent=right)
        right_B_1 = MockState(parent=right_B)

        assert _get_common_parent(left, middle) == root
        assert _get_common_parent(middle, left) == root
        assert _get_common_parent(left, right) == root
        assert _get_common_parent(middle, right) == root
        assert _get_common_parent(middle, root) == root
        assert _get_common_parent(left_A, root) == root
        assert _get_common_parent(root, left_A) == root
        assert _get_common_parent(left_A, left) == left
        assert _get_common_parent(left_A, left_B) == left
        assert _get_common_parent(left_A, middle) == root
        assert _get_common_parent(right_A, right_B) == right
        assert _get_common_parent(right_A, left_A) == root
        assert _get_common_parent(right_A_1, middle_A) == root
        assert _get_common_parent(right_A_1, right_B) == right
        assert _get_common_parent(right_A_1, right_A_2) == right_A
        assert _get_common_parent(right_A_1, right_B_1) == right

    def test_after_reformat(self):
        states = {
            'root': State({
                'left': State({
                    'left_A': State(),
                    'left_B': State(),
                }),
                'middle': State({
                    'middle_A': State(),
                    'middle_B': State(),
                    'middle_C': State(),
                }),
                'right': State({
                    'right_A': State({
                        'right_A_1':  State(),
                        'right_A_2': State(),
                    }),
                    'right_B': State(),
                })
            })
        }

        flattened = HSM(states, {}, skip_validation=True).flattened

        left_A = _get_state_by_name(('left_A',), flattened)
        left_B = _get_state_by_name(('left_B',), flattened)
        right_A_1 = _get_state_by_name(('right_A_1',), flattened)
        right_B = _get_state_by_name(('right_B',), flattened)

        assert _get_common_parent(left_A, left_B).name[0] == 'left'
        assert _get_common_parent(left_A, right_A_1).name[0] == 'root'
        assert _get_common_parent(right_A_1, right_B).name[0] == 'right'



class Test_find_duplicates(object):

    def test_empty(self):
        assert _find_duplicates(None) == []
        assert _find_duplicates([]) == []

    def test_no_duplicates(self):
        assert _find_duplicates([1]) == []
        assert _find_duplicates([1, 2, 3, 4]) == []

    def test_one_duplicate(self):
        assert _find_duplicates([1, 1]) == [1]
        assert _find_duplicates([1, 1, 2]) == [1]
        assert _find_duplicates([1, 2, 1]) == [1]
        assert _find_duplicates([2, 1, 1]) == [1]
        assert _find_duplicates(list('abCdefgChi')) == ['C']

    def test_multiple_duplicates(self):
        dups = _find_duplicates(list('abC_dEfgCh_iEjE__k'))
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
        dups = [name[0] for name in _find_duplicate_names(hsm.flattened)]
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
                'ortho': State(  # unreachable
                    [
                        ({ 'sub1': State(), }, {} ),  # TODO: implement logic
                        ({ 'sub2': State(), }, {} ),  # for unreachable in orth
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

    def test_get_state_by_name(self):
        f = lambda nice: _get_state_by_name((nice,), self.hsm.flattened)
        assert f('top').name == ('top',)
        assert f('left').name == ('left',)
        assert f('mid_A').name == ('mid_A',)
        assert f('right_B').name == ('right_B',)

    def test_get_state_by_name_in_orthogonal(self):
        f = lambda tup: _get_state_by_name(tup, self.hsm.flattened)
        assert f(('ortho',)).name == ('ortho',)
        assert f(('ortho', 0, 'sub1')).name == ('ortho', 0, 'sub1')
        assert f(('ortho', 1, 'sub2')).name == ('ortho', 1, 'sub2')


    def test_get_incoming_trans(self):
        # exclude Transition objects from result tuples for cleaner checks
        def f(name, include_loops):
            res = [(src[0], evt) for src, evt, _tran
                   in _get_incoming_transitions((name,), self.hsm.trans,
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
        t = _find_nonexistent_transition_sources(self.hsm.flattened,
                                                 self.hsm.trans)
        assert sorted(t) == sorted([('bad_source_1',), ('bad_source_2',)])


    def test_find_nonexistent_transition_targets(self):
        t = _find_nonexistent_transition_targets(self.hsm.flattened,
                                                 self.hsm.trans)
        assert sorted(t) == sorted([('bad_target_1',), ('bad_target_2',)])


    def test_find_missing_initial_transitions(self):
        func = _find_missing_initial_transitions
        names = [st.name[0] for st in func(self.hsm.flattened, self.hsm.trans)]
        assert sorted(names) == sorted(['left', 'bad'])


    def test_find_invalid_initial_transitions(self):
        func = _find_invalid_initial_transitions
        names = [st.name[0] for st in func(self.hsm.flattened, self.hsm.trans)]
        assert sorted(names) == sorted(['top', 'middle', 'right'])


    def test_find_invalid_local_transitions(self):
        res_tuples = [(src[0], evt, tran.target[0]) for src, evt, tran
                      in _find_invalid_local_transitions(self.hsm.flattened,
                                                         self.hsm.trans)]
        assert sorted(res_tuples) == sorted([
            ('left_B', A, 'left_A'),
            ('right', A, 'left_A'),
            ('right', B, 'right'),
        ])


    def test_find_unreachable_states(self):
        names = [st.name[-1]  # first element of tuple
                 for st in _find_unreachable_states(self.hsm.root,
                                                    self.hsm.flattened,
                                                    self.hsm.trans)]
        assert sorted(names) == sorted(['middle', 'mid_A', 'right_A',
                                        'right_B', 'bad', 'bad1', 'ortho',
                                        'sub1', 'sub2'])


class Test_get_events(object):

    def test_miro_machine_events(self):
        states, trans = make_miro_machine(use_logging=False)
        hsm = HSM(states, trans)
        event_set = _get_events(hsm.flattened, trans)
        assert event_set == set([A, B, C, D, E, F, G, H, I, TERMINATE])

    def test_nested_machine_events(self):
        states, trans = make_nested_machine(False)
        hsm = HSM(states, trans)
        event_set = _get_events(hsm.flattened, trans)
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
        event_set = _get_events(self.hsm.flattened, self.trans)
        # RootEventB shouldn't appear in event_set since nobody explicitly
        # listens to it, only its subclasses
        assert event_set == set([RootEventA, RootEventC, A1, A2, B1, C1, C2,
                                 C11, C12, C21, C22])


class Test_flatten(object):
    def test_single_empty(self):
        assert _flatten([]) == []

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
        names = [st.name for st in _flatten(states)]
        expected = ['a', 'submachines', 'sub1', 'sub11', 'sub12', 'sub121',
                    'sub122', 'sub2', 'sub21', 'sub22', 'sub221', 'sub222',
                    'b', 'b1', 'c', 'c1', 'c2']
        assert len(names) == len(expected)
        assert set(names) == set(expected)

    def test_flatten_miro_machine(self):
        states, trans = make_miro_machine(use_logging=False)

        hsm = HSM(states, trans)
        names = [st.name[-1] for st in hsm.flattened]
        assert sorted(names) == sorted(['top', 'final', 's', 's1', 's11', 's2',
                                        's21', 's211'])


def get_state(kind, name, states):
    st = State(states)
    st.name = name
    st.kind = kind
    return st

orthogonal = lambda name, states: get_state('orthogonal', name, states)
composite = lambda name, states: get_state('composite', name, states)
leaf = lambda name: get_state('leaf', name, [])


class Test_reformat(object):
    def test_empty(self):
        assert _reformat({}, {}) == ([], {})

    def test_empty_with_prefix(self):
        assert _reformat({}, {}, prefix=('pfx', 1)) == ([], {})

    def test_reformat_states_shallow(self):
        states = {
            'a': State(),
        }
        expected_states = [ leaf(('a',)) ]
        assert _reformat(states, {}) == (expected_states, {})

    def test_reformat_states_shallow_with_prefix(self):
        states = {
            'a': State(),
        }
        exp_states = [ leaf(('pfx', 1, 'a',)) ]
        assert _reformat(states, {}, prefix=('pfx', 1)) == (exp_states, {})

    def test_renamed_transition_sources_and_targets(self):
        action = lambda a: a
        trans = {
            'a': {
                Initial: T('blah'),
                A: Local('blah2'),
            },
            'b': {
                A: T('c', action=action)
            }
        }
        expected_trans = {
            ('a',): {
                Initial: T(('blah',)),
                A: Local(('blah2',)),
            },
            ('b',): {
                A: T(('c',), action=action)
            }
        }
        assert _reformat({}, trans) == ([], expected_trans)

    def test_renamed_transition_sources_and_targets_with_prefix(self):
        action = lambda a: a
        trans = {
            'a': {
                Initial: T('blah'),
                A: Local('blah2'),
            },
            'b': {
                A: T('c', action=action)
            }
        }
        expected_trans = {
            ('pfx', 1, 'a',): {
                Initial: T(('pfx', 1, 'blah',)),
                A: Local(('pfx', 1, 'blah2',)),
            },
            ('pfx', 1, 'b',): {
                A: T(('pfx', 1, 'c',), action=action)
            }
        }
        assert _reformat({}, trans, prefix=('pfx', 1)) == ([], expected_trans)

    def test_reformat_simple_submachine(self):
        states = {
            'a': State(
                [
                    ({ 'sub1': State({
                        'x': State() }) },
                     { } ),

                    ({ 'sub2': State({
                        'y': State({
                            'deep': State() })})},
                     { } ),
                ])
        }
        exp_states = [
            orthogonal(('a',), [

                composite(('a', 0, 'sub1'), [
                    leaf(('a', 0, 'x')) ]),

                composite(('a', 1, 'sub2'), [
                    composite(('a', 1, 'y'),  [
                        leaf(('a', 1, 'deep'))
                    ]) ])
            ])
        ]

        assert _reformat(states, {}) == (exp_states, {})

    def test_reformat_nested_submachines(self):
        states = {
            'a': State({
                'a1': State({
                    'a11': State(),
                }),
                'a2': State({
                    'a12': State(),
                }),
            }),
            'b': State(
            [
                (
                    {
                        'sub1': State({
                            'sub1a': State(),
                            'sub1_ortho': State(
                            [
                                ({ 'deep1': State({ 'deep2': State() }), },
                                    {}),
                                ({ 'deep1': State({ 'deep2': State() }), },
                                    {}),
                            ]),
                        }),
                    },
                    { }),

                (
                    { 'sub2': State({
                        'sub2a': State(),
                        'sub2b': State({
                            'deep': State()
                        }),
                    })},
                    { }
                ),
            ])
        }
        exp_states = [
            composite(('a',), [
                composite(('a1',), [
                    leaf(('a11',)),
                ]),
                composite(('a2',), [
                    leaf(('a12',)),
                ]),
            ]),
            orthogonal(('b',), [
                composite(('b', 0, 'sub1'), [
                    leaf(('b', 0, 'sub1a')),
                    orthogonal(('b', 0, 'sub1_ortho'), [
                        composite(('b', 0, 'sub1_ortho', 0, 'deep1'), [
                            leaf(('b', 0, 'sub1_ortho', 0, 'deep2')) ]),
                        composite(('b', 0, 'sub1_ortho', 1, 'deep1'), [
                            leaf(('b', 0, 'sub1_ortho', 1, 'deep2')) ]),
                    ]),

                ]),
                composite(('b', 1, 'sub2'), [
                    leaf(('b', 1, 'sub2a')),
                    composite(('b', 1, 'sub2b'), [
                        leaf(('b', 1, 'deep'))
                    ]),
                ]),
            ])
        ]

        assert _reformat(states, {}) == (exp_states, {})

    def test_submachine_transitions_merged_to_main_trans_dict(self):
        # this will branch 4 times
        deep_trans = {
            'top': {
                Initial: T('nested_deep_2'),
            },
            'nested_deep_1': {
                A: T('renaming is dumb'),
            }
        }

        # this will branch twice
        mid = {
            'top': {
                'nested_mid':
                [
                    ({}, deep_trans),  # don't care about states
                    ({}, deep_trans),
                ]
            }
        }
        mid_trans = {
            'top': {
                Initial: T('blah'),
            },
            'nested_mid': {
                A: Local('fff'),
            }
        }

        # root
        states = {
            'top': {
                'nested':
                [
                    (mid, mid_trans),
                    (mid, mid_trans),
                ],
                'dumb': {}
            }
        }
        trans = {
            'top': {
                Initial: T('nested'),
            },
            'dumb': {
                A: Local('top')
            }
        }


        expected_trans = {  # all transition dicts are flattened into one
            ('top',): {
                Initial: T(('nested',)),
            },
            ('dumb',): {
                A: Local(('top',))
            },
            ('nested', 0, 'nested_mid', 0, 'top'): {
                Initial: T(('nested', 0, 'nested_mid', 0, 'nested_deep_2')),
            },
            ('nested', 0, 'nested_mid', 0, 'nested_deep_1'): {
                A: T(('nested', 0, 'nested_mid', 0, 'renaming is dumb')),
            },
            ('nested', 0, 'top'): {
                Initial: T(('nested', 0, 'blah')),
            },
            ('nested', 0, 'nested_mid'): {
                A: Local(('nested', 0, 'fff')),
            },
            ('nested', 1, 'top'): {
                Initial: T(('nested', 1, 'blah')),
            },
            ('nested', 1, 'nested_mid'): {
                A: Local(('nested', 1, 'fff')),
            },
            ('nested', 0, 'nested_mid', 1, 'top'): {
                Initial: T(('nested', 0, 'nested_mid', 1, 'nested_deep_2')),
            },
            ('nested', 0, 'nested_mid', 1, 'nested_deep_1'): {
                A: T(('nested', 0, 'nested_mid', 1, 'renaming is dumb')),
            },
            ('nested', 1, 'nested_mid', 0, 'top'): {
                Initial: T(('nested', 1, 'nested_mid', 0, 'nested_deep_2')),
            },
            ('nested', 1, 'nested_mid', 0, 'nested_deep_1'): {
                A: T(('nested', 1, 'nested_mid', 0, 'renaming is dumb')),
            },
            ('nested', 1, 'nested_mid', 1, 'top'): {
                Initial: T(('nested', 1, 'nested_mid', 1, 'nested_deep_2')),
            },
            ('nested', 1, 'nested_mid', 1, 'nested_deep_1'): {
                A: T(('nested', 1, 'nested_mid', 1, 'renaming is dumb')),
            }
        }

        _, renamed_trans = _reformat(states, trans)
        assert renamed_trans == expected_trans


    def test_reformat_miro_machine(self):
        states, _ = _reformat(*make_miro_machine(use_logging=False))
        expected_states = [
            composite(('top',), [
                composite(('s',), [
                    composite(('s1',), [
                        leaf(('s11',))
                    ]),
                    composite(('s2',), [
                        composite(('s21',), [
                            leaf(('s211',))
                        ])
                    ])
                ]),
                leaf(('final',))
            ])
        ]
        assert states == expected_states




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
        s1.states = [leaf(1), leaf(2), leaf(3)]
        s2.states = [leaf(1), leaf(2), leaf(3)]
        assert s1 == s2
        s2.states = [leaf(3), leaf(1), leaf(2)]
        assert s1 == s2
        s2.states = [leaf(3), leaf(999), leaf(2)]
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
            composite('A', [leaf(1), leaf(2)]),
            composite('B', [leaf(3), leaf(4)]),
        ]
        s2.states = [
            composite('A', [leaf(2), leaf(1)]),
            composite('B', [leaf(4), leaf(3)]),
        ]
        assert s1 == s2
        s2.states = [
            composite('B', [leaf(4), leaf(3)]),
            composite('A', [leaf(2), leaf(1)]),
        ]
        assert s1 == s2
        s2.states = [
            composite('B', [leaf(4), leaf(3)]),
            composite('A', [leaf(999), leaf(1)]),
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
