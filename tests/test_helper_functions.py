from hsmpy.statemachine import (_get_path_from_root,
                                _get_common_parent,
                                _get_children,
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
                                )

from hsmpy import Transition as T
from hsmpy import LocalTransition as Local
from hsmpy import State, CompositeState, HSM


class MockState(object):
    def __init__(self, parent):
        self._parent = parent


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
        state_names = [state.name for state in _get_path_from_root(deep)]
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
        assert _get_common_parent(left, right) == root
        assert _get_common_parent(middle, right) == root
        assert _get_common_parent(middle, root) == root
        assert _get_common_parent(left_A, root) == root
        assert _get_common_parent(left_A, left) == left
        assert _get_common_parent(left_A, left_B) == left
        assert _get_common_parent(left_A, middle) == root
        assert _get_common_parent(right_A, right_B) == right
        assert _get_common_parent(right_A, left_A) == root
        assert _get_common_parent(right_A_1, middle_A) == root
        assert _get_common_parent(right_A_1, right_B) == right
        assert _get_common_parent(right_A_1, right_A_2) == right_A
        assert _get_common_parent(right_A_1, right_B_1) == right

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
        assert _get_common_parent(left_A, left_B).name == 'left'
        assert _get_common_parent(left_A, right_A_1).name == 'root'
        assert _get_common_parent(right_A_1, right_B).name == 'right'


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
            'top': CompositeState({  # bad initial transition (local)
                'left': CompositeState({  # no initial transition
                    'left_A': State(),
                    'left_B': State(),
                    'bad': CompositeState({}),  # unreachable; missing initial
                                                # transition; no substates
                }),
                'middle': CompositeState({  # bad initial transition (outside)
                    'mid_A': State(),       # both unreachable
                }),
                'right': CompositeState({  # bad initial transition (loop)
                    'right_A': State(),  # unreachable (incoming also unreach.)
                    'right_B': State(),  # unreachable; only has self loop
                }),
            })
        }

        self.trans = {
            'top': {
                'initial': Local('left_B'),  # initial trans cannot be local
            },
            'left': {  # no initial transition
                A: T('right'),
                B: T('left'),  # loop
            },
            'right': {
                A: Local('left_A'),  # invalid (target not local)
                B: Local('right'),  # invalid loop (loop cannot be local)
                C: T('bad_target_1'),
                'initial': T('right'),  # inital transition cannot be loop
            },
            'middle': {
                'initial': T('top'),  # initial transition cannot go outside
                A: T('right_A'),  # this shouldn't make right_A reachable
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
        self.hsm = HSM(self.states, self.trans)


    def test_get_children(self):
        names = lambda state: sorted([ch.name for ch in _get_children(state)])

        assert names(self.states['top']) == sorted([
            'left', 'right', 'left_A', 'left_B', 'bad', 'right_A', 'right_B',
            'middle', 'mid_A'])

        assert names(self.states['top']['left']) == sorted([
            'left_A', 'left_B', 'bad'])

        assert names(self.states['top']['middle']) == ['mid_A']

        assert names(self.states['top']['right']) == sorted([
            'right_A', 'right_B'])

        assert names(self.states['top']['right']['right_A']) == []

    def test_get_state_by_name(self):
        f = lambda name: _get_state_by_name(name, self.hsm.flattened)
        assert f('top') == self.states['top']
        assert f('left') == self.states['top']['left']
        assert f('mid_A') == self.states['top']['middle']['mid_A']
        assert f('right_B') == self.states['top']['right']['right_B']

    def test_get_incoming_trans(self):
        # exclude Transition objects from result tuples for cleaner checks
        def f(name, include_loops):
            res = [(src, evt) for src, evt, _tran
                   in _get_incoming_transitions(name, self.trans,
                                                include_loops)]
            return sorted(res)

        assert f('top', False) == sorted([
            ('right_A', 'B'),
            ('middle', 'initial')])

        assert f('top', True) == sorted([
            ('right_A', 'B'),
            ('middle', 'initial')])

        assert f('left', False) == sorted([
            ('bad_source_2', 'A'),
            ('left_A', 'B')])

        assert f('left', True) == sorted([
            ('bad_source_2', 'A'),
            ('left_A', 'B'),
            ('left', 'B')])

        assert f('right_B', False) == []
        assert f('right_B', True) == [('right_B', 'A')]

    def test_find_nonexistent_transition_sources(self):
        t = _find_nonexistent_transition_sources(self.hsm.flattened,
                                                 self.trans)
        assert sorted(t) == sorted(['bad_source_1', 'bad_source_2'])

    def test_find_nonexistent_transition_targets(self):
        t = _find_nonexistent_transition_targets(self.hsm.flattened,
                                                 self.trans)
        assert sorted(t) == sorted(['bad_target_1', 'bad_target_2'])

    def test_find_missing_initial_transitions(self):
        func = _find_missing_initial_transitions
        names = [st.name for st in func(self.hsm.flattened, self.trans)]
        assert sorted(names) == sorted(['left', 'bad'])

    def test_find_invalid_initial_transitions(self):
        func = _find_invalid_initial_transitions
        names = [st.name for st in func(self.hsm.flattened, self.trans)]
        assert sorted(names) == sorted(['top', 'middle', 'right'])

    def test_find_invalid_local_transitions(self):
        res_tuples = [(src, evt, tran.target) for src, evt, tran
                      in _find_invalid_local_transitions(self.hsm.flattened,
                                                         self.trans)]
        assert sorted(res_tuples) == sorted([
            ('left_B', 'A', 'left_A'),
            ('right', 'A', 'left_A'),
            ('right', 'B', 'right'),
        ])

    def test_find_unreachable_states(self):
        names = [st.name for st in _find_unreachable_states(self.states['top'],
                                                            self.hsm.flattened,
                                                            self.trans)]
        assert sorted(names) == sorted(['middle', 'mid_A', 'right_A',
                                        'right_B', 'bad'])
