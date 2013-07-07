from hsmpy.statemachine import (_path_from_root, _common_parent,
                                _find_duplicates)

from hsmpy.statemachine import Transition as T
from hsmpy.statemachine import LocalTransition as Local


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
        assert _find_duplicates(list('abC_dEfgCh_iEjE__k')) == ['C', 'E', '_']
        # should have used a set here


#class Test_find_incoming_trans(object):
    #def setup_class(self):
        #A = object()
        #B = object()
        #C = object()
        #self.trans = {
            #'a': {
                #A: T('b'),
                #B: T('a'),  # loop
            #},
            #'b': {
                #A: Local('a'),  # not valid in general, test this later
                #B: T('b'),  # loop
                #C: T('a'),
            #}
        #}
        ## TODO: check both with and without loops
