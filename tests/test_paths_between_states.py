from hsmpy.logic import (get_path,
                         get_path_from_root,
                         get_common_parent,
                         get_state_by_sig)

from hsmpy import State, HSM


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

        assert get_path(root, root) == ([], root, [])
        assert get_path(left, left) == ([], left, [])
        assert get_path(left_A, left_B) == ([left_A], left, [left_B])
        assert get_path(left_B, left_A) == ([left_B], left, [left_A])
        assert get_path(middle, root) == ([middle], root, [])
        assert get_path(root, middle) == ([], root, [middle])
        assert get_path(middle_A, left_A) == ([middle_A, middle],
                                              root, [left, left_A])
        assert get_path(right_A_1, left) == ([right_A_1, right_A, right],
                                             root, [left])
        assert get_path(right_A_2, left_B) == ([right_A_2, right_A, right],
                                               root, [left, left_B])
        assert get_path(left_B, right_A_2) == ([left_B, left], root,
                                               [right, right_A, right_A_2])
        assert get_path(right_A, root) == ([right_A, right], root, [])
        assert get_path(root, right_A) == ([], root, [right, right_A])

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

        left_B = get_state_by_sig(('left_B',), flattened)
        deep = get_state_by_sig(('deep',), flattened)

        exits, parent, entries = get_path(deep, left_B)
        exits = [st.name for st in exits]
        entries = [st.name for st in entries]

        assert exits == ['deep', 'right_A', 'right']
        assert parent.name == 'root'
        assert entries == ['left', 'left_B']


class Test_get_path_from_root(object):

    def test_single_node(self):
        root = MockState(parent=None)
        assert get_path_from_root(root) == [root]

    def test_one_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        assert get_path_from_root(root) == [root]
        assert get_path_from_root(ch_1) == [root, ch_1]

    def test_multiple_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        ch_2 = MockState(parent=ch_1)
        ch_3 = MockState(parent=ch_2)
        ch_4 = MockState(parent=ch_3)
        assert get_path_from_root(root) == [root]
        assert get_path_from_root(ch_1) == [root, ch_1]
        assert get_path_from_root(ch_2) == [root, ch_1, ch_2]
        assert get_path_from_root(ch_3) == [root, ch_1, ch_2, ch_3]
        assert get_path_from_root(ch_4) == [root, ch_1, ch_2, ch_3, ch_4]

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

        assert get_path_from_root(left) == [root, left]
        assert get_path_from_root(left_A) == [root, left, left_A]
        assert get_path_from_root(left_B) == [root, left, left_B]
        assert get_path_from_root(middle) == [root, middle]
        assert get_path_from_root(middle_A) == [root, middle, middle_A]
        assert get_path_from_root(middle_B) == [root, middle, middle_B]
        assert get_path_from_root(middle_C) == [root, middle, middle_C]
        assert get_path_from_root(right) == [root, right]
        assert get_path_from_root(right_A) == [root, right, right_A]
        assert get_path_from_root(right_B) == [root, right, right_B]
        assert get_path_from_root(right_A_1) == [root, right, right_A,
                                                 right_A_1]
        assert get_path_from_root(right_A_2) == [root, right, right_A,
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
        deep = get_state_by_sig(('deep',), flattened)
        state_names = [state.name for state in get_path_from_root(deep)]
        assert state_names == ['root', 'right', 'right_A', 'deep']


class Test_get_common_parent(object):

    def test_single_node(self):
        root = MockState(parent=None)
        assert get_common_parent(root, root) == root

    def test_one_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        assert get_common_parent(root, ch_1) == root
        assert get_common_parent(ch_1, root) == root
        assert get_common_parent(ch_1, ch_1) == ch_1

    def test_multiple_nested(self):
        root = MockState(parent=None)
        ch_1 = MockState(parent=root)
        ch_2 = MockState(parent=ch_1)
        ch_3 = MockState(parent=ch_2)
        ch_4 = MockState(parent=ch_3)
        assert get_common_parent(root, ch_2) == root
        assert get_common_parent(ch_2, root) == root
        assert get_common_parent(ch_1, ch_2) == ch_1
        assert get_common_parent(ch_2, ch_1) == ch_1
        assert get_common_parent(ch_1, ch_3) == ch_1
        assert get_common_parent(ch_3, ch_1) == ch_1
        assert get_common_parent(ch_4, ch_3) == ch_3
        assert get_common_parent(ch_3, ch_4) == ch_3
        assert get_common_parent(ch_1, ch_4) == ch_1
        assert get_common_parent(root, ch_4) == root

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

        assert get_common_parent(left, middle) == root
        assert get_common_parent(middle, left) == root
        assert get_common_parent(left, right) == root
        assert get_common_parent(middle, right) == root
        assert get_common_parent(middle, root) == root
        assert get_common_parent(left_A, root) == root
        assert get_common_parent(root, left_A) == root
        assert get_common_parent(left_A, left) == left
        assert get_common_parent(left_A, left_B) == left
        assert get_common_parent(left_A, middle) == root
        assert get_common_parent(right_A, right_B) == right
        assert get_common_parent(right_A, left_A) == root
        assert get_common_parent(right_A_1, middle_A) == root
        assert get_common_parent(right_A_1, right_B) == right
        assert get_common_parent(right_A_1, right_A_2) == right_A
        assert get_common_parent(right_A_1, right_B_1) == right

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

        left_A = get_state_by_sig(('left_A',), flattened)
        left_B = get_state_by_sig(('left_B',), flattened)
        right_A_1 = get_state_by_sig(('right_A_1',), flattened)
        right_B = get_state_by_sig(('right_B',), flattened)

        assert get_common_parent(left_A, left_B).name == 'left'
        assert get_common_parent(left_A, right_A_1).name == 'root'
        assert get_common_parent(right_A_1, right_B).name == 'right'
