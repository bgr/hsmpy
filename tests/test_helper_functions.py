from hsmpy.statemachine import (_path_from_root, _common_parent, _get_children,
                                _find_duplicates, _find_duplicate_names,
                                _find_incoming_transitions,
                                _find_nonexistent_transition_sources,
                                _find_nonexistent_transition_targets,
                                _find_missing_initial_transitions,
                                _find_invalid_initial_transitions,
                                _find_invalid_local_transitions,
                                _find_unreachable_states,
                                )

from hsmpy import Transition as T
from hsmpy import LocalTransition as Local
from hsmpy import State, CompositeState, HSM


class MockState(object):
    def __init__(self, parent):
        self._parent = parent


class Test_path_from_root(object):

    def test_single_node(self):
        root = MockState(parent=None)
        assert _path_from_root(root) == [root]

    def test_one_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        assert _path_from_root(root) == [root]
        assert _path_from_root(ch_1) == [root, ch_1]

    def test_multiple_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        ch_2 = MockState(parent=ch_1)
        ch_3 = MockState(parent=ch_2)
        ch_4 = MockState(parent=ch_3)
        assert _path_from_root(root) == [root]
        assert _path_from_root(ch_1) == [root, ch_1]
        assert _path_from_root(ch_2) == [root, ch_1, ch_2]
        assert _path_from_root(ch_3) == [root, ch_1, ch_2, ch_3]
        assert _path_from_root(ch_4) == [root, ch_1, ch_2, ch_3, ch_4]

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

        assert _path_from_root(left) == [root, left]
        assert _path_from_root(left_A) == [root, left, left_A]
        assert _path_from_root(left_B) == [root, left, left_B]
        assert _path_from_root(middle) == [root, middle]
        assert _path_from_root(middle_A) == [root, middle, middle_A]
        assert _path_from_root(middle_B) == [root, middle, middle_B]
        assert _path_from_root(middle_C) == [root, middle, middle_C]
        assert _path_from_root(right) == [root, right]
        assert _path_from_root(right_A) == [root, right, right_A]
        assert _path_from_root(right_B) == [root, right, right_B]
        assert _path_from_root(right_A_1) == [root, right, right_A, right_A_1]
        assert _path_from_root(right_A_2) == [root, right, right_A, right_A_2]

    def test_with_HSM_instance(self):
        deep = State()
        states = {
            'root': CompositeState({
                'left': CompositeState({
                    'left_A': State(),
                    'left_B': State(),
                }),
                'middle': CompositeState({
                    'middle_A': State(),
                    'middle_B': State(),
                    'middle_C': State(),
                }),
                'right': CompositeState({
                    'right_A': CompositeState({
                        'right_A_1': State(),
                        'deep': deep,
                        'right_A_2': State(),
                    }),
                    'right_B': State(),
                })
            })
        }

        HSM(states, {})  # wire up the state tree
        state_names = [state.name for state in _path_from_root(deep)]
        assert state_names == ['root', 'right', 'right_A', 'deep']


class Test_common_parent(object):

    def test_single_node(self):
        root = MockState(parent=None)
        assert _common_parent(root, root) == root

    def test_one_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        assert _common_parent(root, ch_1) == root
        assert _common_parent(ch_1, root) == root
        assert _common_parent(ch_1, ch_1) == ch_1

    def test_multiple_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        ch_2 = MockState(parent=ch_1)
        ch_3 = MockState(parent=ch_2)
        ch_4 = MockState(parent=ch_3)
        assert _common_parent(root, ch_2) == root
        assert _common_parent(ch_2, root) == root
        assert _common_parent(ch_1, ch_2) == ch_1
        assert _common_parent(ch_2, ch_1) == ch_1
        assert _common_parent(ch_1, ch_3) == ch_1
        assert _common_parent(ch_3, ch_1) == ch_1
        assert _common_parent(ch_4, ch_3) == ch_3
        assert _common_parent(ch_3, ch_4) == ch_3
        assert _common_parent(ch_1, ch_4) == ch_1
        assert _common_parent(root, ch_4) == root

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

        assert _common_parent(left, middle) == root
        assert _common_parent(left, right) == root
        assert _common_parent(middle, right) == root
        assert _common_parent(middle, root) == root
        assert _common_parent(left_A, root) == root
        assert _common_parent(left_A, left) == left
        assert _common_parent(left_A, left_B) == left
        assert _common_parent(left_A, middle) == root
        assert _common_parent(right_A, right_B) == right
        assert _common_parent(right_A, left_A) == root
        assert _common_parent(right_A_1, middle_A) == root
        assert _common_parent(right_A_1, right_B) == right
        assert _common_parent(right_A_1, right_A_2) == right_A
        assert _common_parent(right_A_1, right_B_1) == right

    def test_with_HSM_instance(self):
        left_A = State()
        left_B = State()
        right_A_1 = State()
        right_B = State()
        states = {
            'root': CompositeState({
                'left': CompositeState({
                    'left_A': left_A,
                    'left_B': left_B,
                }),
                'middle': CompositeState({
                    'middle_A': State(),
                    'middle_B': State(),
                    'middle_C': State(),
                }),
                'right': CompositeState({
                    'right_A': CompositeState({
                        'right_A_1':  right_A_1,
                        'right_A_2': State(),
                    }),
                    'right_B': right_B,
                })
            })
        }

        HSM(states, {})  # wire up the state tree
        assert _common_parent(left_A, left_B).name == 'left'
        assert _common_parent(left_A, right_A_1).name == 'root'
        assert _common_parent(right_A_1, right_B).name == 'right'


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

    def test_single_duplicate_state_instance(self):
        duplicate = State()
        states = {
            'top': CompositeState({
                'left': CompositeState({
                    'left_A': duplicate,
                    'left_B': State(),
                }),
                'right': CompositeState({
                    'right_A': State(),
                    'right_B': duplicate,
                }),
            })
        }
        hsm = HSM(states, {})
        dups = _find_duplicates(hsm.flattened)
        assert dups == [duplicate]

    def test_multiple_duplicate_state_instances(self):
        duplicate_1 = State()
        duplicate_2 = State()
        composite_dupl = CompositeState({
            'a': duplicate_1,
            'b': CompositeState({
                'l': duplicate_1,
                'r': duplicate_2,
            })
        })
        states = {
            'top': CompositeState({
                'left': CompositeState({
                    'left_A': duplicate_1,
                    'left_B': composite_dupl
                }),
                'right': CompositeState({
                    'right_A': duplicate_2,
                    'right_B': composite_dupl,
                }),
            })
        }
        hsm = HSM(states, {})
        print hsm.flattened
        dups = _find_duplicates(hsm.flattened)
        print dups
        assert sorted(dups) == sorted([duplicate_1, duplicate_2,
                                       composite_dupl['b'], composite_dupl])

    def test_duplicate_state_names(self):
        states = {
            'top': CompositeState({
                'left': CompositeState({
                    'left_A': State(),
                    'right': State(),
                    'left_B': State(),
                    'left': State(),
                }),
                'right': CompositeState({
                    'right_A': State(),
                    'right_B': State(),
                    'left': State(),
                }),
            }),
            'left_B': State(),
        }
        hsm = HSM(states, {})
        dups = _find_duplicate_names(hsm.flattened)
        assert sorted(dups) == sorted(['left', 'right', 'left_B'])


class Test_structural_analysis(object):
    def setup_class(self):
        A = 'A'  # mock events
        B = 'B'
        C = 'C'
        self.states = {
            'top': CompositeState({
                'left': CompositeState({  # no initial transition
                    'left_A': State(),
                    'left_B': State(),
                    'bad': CompositeState({}),  # unreachable, no initial tran,
                                                # no substates
                }),
                'right': CompositeState({  # initial transition goes outside
                    'right_A': State(),
                    'right_B': State(),  # unreachable, only has self loop
                }),
            })
        }

        self.trans = {
            'top': {
                'initial': Local('left_B'),
            },
            'left': {  # no initial transition
                A: T('right'),
                B: T('left'),  # loop
            },
            'right': {
                A: Local('left'),  # invalid, cannot be local
                B: Local('right'),  # loop, invalid (loop cannot be local)
                C: T('invalid_target_1'),
                'initial': T('right'),  # inital cannot be loop
            },
            'invalid_source_1': {
                A: Local('invalid_target_2'),
            },
            'left_A': {
                A: T('left_A'),  # loop
                B: T('left'),
            },
            'left_B': {
                A: Local('left_A')  # invalid, cannot be local
            },
            'right_A': {
                A: T('left_B'),
                B: Local('top'),
            },
            'right_B': {
                A: T('right_B'),  # loop
            },
            'invalid_source_2': {
                A: T('left'),
                B: T('right'),
            },
        }
        self.hsm = HSM(self.states, self.trans)


    def test_get_children(self):
        names = lambda state: sorted([ch.name for ch in _get_children(state)])

        assert names(self.states['top']) == sorted([
            'left', 'right', 'left_A', 'left_B', 'bad', 'right_A', 'right_B'])

        assert names(self.states['top']['left']) == sorted([
            'left_A', 'left_B', 'bad'])

        assert names(self.states['top']['right']) == sorted([
            'right_A', 'right_B'])

        assert names(self.states['top']['right']['right_A']) == []


    def test_find_incoming_trans(self):
        # exclude Transition objects from result tuples for cleaner checks
        def f(name, include_loops):
            res = [(src, evt) for src, evt, _tran
                   in _find_incoming_transitions(name, self.trans,
                                                 include_loops)]
            return sorted(res)

        assert f('top', False) == [('right_A', 'B')]
        assert f('top', True) == [('right_A', 'B')]

        assert f('left', False) == sorted([
            ('invalid_source_2', 'A'),
            ('right', 'A'),
            ('left_A', 'B'),
        ])
        assert f('left', True) == sorted([
            ('invalid_source_2', 'A'),
            ('right', 'A'),
            ('left_A', 'B'),
            ('left', 'B'),
        ])

        assert f('right_B', False) == []
        assert f('right_B', True) == [('right_B', 'A')]

    def test_find_nonexistent_transition_sources(self):
        t = _find_nonexistent_transition_sources(self.hsm.flattened,
                                                 self.trans)
        assert sorted(t) == sorted(['invalid_source_1', 'invalid_source_2'])

    def test_find_nonexistent_transition_targets(self):
        t = _find_nonexistent_transition_targets(self.hsm.flattened,
                                                 self.trans)
        assert sorted(t) == sorted(['invalid_target_1', 'invalid_target_2'])

    def test_find_missing_initial_transitions(self):
        t = _find_missing_initial_transitions(self.hsm.flattened, self.trans)
        assert sorted(t) == sorted(['left', 'bad'])

    def test_find_invalid_initial_transitions(self):
        #t = _find_invalid_initial_transitions(self.hsm.flattened, self.trans)
        # TODO
        #assert sorted(t) == sorted([])
        pass

    def test_find_invalid_local_transitions(self):
        #t = _find_invalid_local_transitions(self.hsm.flattened, self.trans)
        #t
        # TODO
        pass

    def test_find_unreachable_states(self):
        #t = _find_unreachable_states(self.hsm.flattened, self.trans)
        #t
        # TODO
        pass
