from hsmpy import HSM
from hsmpy.logic import join_paths, tree_from_state_set, get_state_by_sig
from reusable import make_miro_machine, make_submachines_machine


class Test_join_paths:

    def test_empty(self):
        assert join_paths([]) == []

    def test_single_leaf(self):
        paths = ['a']
        expected = [ ('a', []) ]
        assert join_paths(paths) == expected

    def test_two_identical_leaves(self):
        paths = [['a'], ['a']]
        expected = [ ('a', []) ]
        assert join_paths(paths) == expected

    def test_two_different_leaves(self):
        paths = [['a'], ['b']]
        expected = [ ('a', []), ('b', []) ]
        assert join_paths(paths) == expected

    def test_single_composite_1_level(self):
        paths = [['a', 'a1']]
        expected = [ ('a', [ ('a1', []) ]) ]
        assert join_paths(paths) == expected

    def test_single_composite_3_levels(self):
        paths = [['a', 'a1', 'a2', 'a3']]
        expected = [ ('a', [ ('a1', [ ('a2', [ ('a3', []) ]) ]) ]) ]
        assert join_paths(paths) == expected

    def test_two_identical_composites(self):
        paths = [
            ['a', 'a1', 'a2', 'a3'],
            ['a', 'a1', 'a2', 'a3'],
        ]
        expected = [
            ('a', [ ('a1', [ ('a2', [ ('a3', []) ]) ]) ]),
        ]
        assert join_paths(paths) == expected

    # it's dumb, doesn't care about same names after it's already branched

    def test_two_different_composites(self):
        paths = [
            ['a', 'a1', 'a2', 'a3'],
            ['diff', 'a1', 'a2', 'a3'],
        ]
        expected = [
            ('a', [ ('a1', [ ('a2', [ ('a3', []) ]) ]) ]),
            ('diff', [ ('a1', [ ('a2', [ ('a3', []) ]) ]) ])
        ]
        assert join_paths(paths) == expected

    def test_two_composites_first_identical(self):
        paths = [
            ['a', 'a1', 'a2', 'a3'],
            ['a', 'diff', 'a2', 'a3'],
        ]
        expected = [
            ('a', [
                ('a1', [ ('a2', [ ('a3', []) ]) ]),
                ('diff', [ ('a2', [ ('a3', []) ]) ]),
            ]),
        ]
        assert join_paths(paths) == expected

    def test_two_composites_first_2_identical(self):
        paths = [
            ['a', 'a1', 'diff', 'a3'],
            ['a', 'a1', 'a2', 'a3'],
        ]
        expected = [
            ('a', [
                ('a1', [
                    ('a2', [ ('a3', []) ]),
                    ('diff', [ ('a3', []) ]),
                ]),
            ]),
        ]
        assert join_paths(paths) == expected

    def test_multiple_with_same_root(self):
        paths = [
            ['a', 'a2', 'a22'],
            ['a', 'a1', 'a12'],
            ['a', 'a1', 'a11', 'a111', 'a1111'],
            ['a', 'a1', 'a11'],
            ['a', 'a1', 'a12', 'a121'],
            ['a', 'a1', 'a12'],  # duplicate, should not matter
            ['a', 'a2', 'a21'],
        ]
        expected = [
            ('a', [
                ('a1', [
                    ('a11', [ ('a111', [ ('a1111', []) ]) ]),
                    ('a12', [ ('a121', []) ]),
                ]),
                ('a2', [
                    ('a21', []),
                    ('a22', []),
                ])
            ]),
        ]
        assert join_paths(paths) == expected

    def test_multiple_with_separate_roots(self):
        paths = [
            ['b', 'b1', 'b12'],
            ['a', 'a2', 'a22'],
            ['a', 'a1', 'a12'],
            ['a', 'a1', 'a11', 'a111', 'a1111'],
            ['a', 'a1', 'a11'],
            ['a', 'a1', 'a12', 'a121'],
            ['a', 'a1', 'a12'],
            ['a', 'a2', 'a21'],
            ['b', 'b1', 'b11', 'b111'],
            ['c', 'c1', 'c11', 'c111'],
            ['b', 'b2', 'b21'],
            ['b', 'b1', 'b11'],
        ]
        expected = [
            ('a', [
                ('a1', [
                    ('a11', [ ('a111', [ ('a1111', []) ]) ]),
                    ('a12', [ ('a121', []) ]),
                ]),
                ('a2', [
                    ('a21', []),
                    ('a22', []),
                ])
            ]),
            ('b', [
                ('b1', [
                    ('b11', [ ('b111', []) ]),
                    ('b12', []),
                ]),
                ('b2', [ ('b21', []) ]),
            ]),
            ('c', [ ('c1', [ ('c11', [ ('c111', []) ]) ]) ]),
        ]
        assert join_paths(paths) == expected



class Test_tree_from_state_set:

    def extract_names(self, tree_tuples):
        """Converts state in every tree node into state's string name."""
        return sorted(
            [(st.name, self.extract_names(subs)) for st, subs in tree_tuples])

    def test_miro_machine(self):
        states, trans = make_miro_machine(use_logging=False)
        hsm = HSM(states, trans)

        s1 = get_state_by_sig(('s11',), hsm.flattened)
        s211 = get_state_by_sig(('s211',), hsm.flattened)

        tree = tree_from_state_set( set([s1, s211]) )
        assert len(tree) == 1  # only one root node

        assert self.extract_names(tree) == [
            ('top', [
                ('s', [
                    ('s1', [
                        ('s11', [])
                    ]),
                    ('s2', [
                        ('s21', [
                            ('s211', []),
                        ])
                    ])
                ]),
                # ('final', []),  # final should NOT be in the tree
            ])
        ]

    def test_submachines_machine(self):
        states, trans = make_submachines_machine(use_logging=False)
        hsm = HSM(states, trans)

        l0_start = get_state_by_sig(('left', 0, 'start'), hsm.flattened)
        s0_top = get_state_by_sig(('subs', 0, 'top'), hsm.flattened)
        s1_final = get_state_by_sig(('subs', 1, 'final'), hsm.flattened)

        tree = tree_from_state_set( set([l0_start, s0_top, s1_final]) )
        assert len(tree) == 1  # only one root node

        assert self.extract_names(tree) == [
            ('top', [
                ('left', [
                    ('left[0].top', [
                        ('left[0].start', [])
                    ]),
                ]),
                ('right', [
                    ('subs', [
                        ('subs[0].top', []),
                        ('subs[1].top', [
                            ('subs[1].final', []),
                        ]),
                    ]),
                ])
            ]),
        ]
