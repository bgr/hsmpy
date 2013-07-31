from hsmpy.logic import reformat
from hsmpy import State, Initial, Local
from reusable import leaf, composite, orthogonal, make_miro_machine, A, T


class Test_reformat:
    def test_empty(self):
        assert reformat({}, {}) == ([], {})

    def test_empty_with_prefix(self):
        assert reformat({}, {}, prefix=('pfx', 1)) == ([], {})

    def test_reformat_states_shallow(self):
        states = {
            'a': State(),
        }
        expected_states = [ leaf('a') ]
        assert reformat(states, {}) == (expected_states, {})

    def test_reformat_states_shallow_with_prefix(self):
        states = {
            'a': State(),
        }
        exp_states = [ leaf('pfx[1].a') ]
        assert reformat(states, {}, prefix=('pfx', 1)) == (exp_states, {})

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
        assert reformat({}, trans) == ([], expected_trans)

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
        assert reformat({}, trans, prefix=('pfx', 1)) == ([], expected_trans)

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
            orthogonal('a', [

                composite('a[0].sub1', [
                    leaf('a[0].x') ]),

                composite('a[1].sub2', [
                    composite('a[1].y',  [
                        leaf('a[1].deep')
                    ]) ])
            ])
        ]

        assert reformat(states, {}) == (exp_states, {})

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
            composite('a', [
                composite('a1', [
                    leaf('a11'),
                ]),
                composite('a2', [
                    leaf('a12'),
                ]),
            ]),
            orthogonal('b', [
                composite('b[0].sub1', [
                    leaf('b[0].sub1a'),
                    orthogonal('b[0].sub1_ortho', [
                        composite('b[0].sub1_ortho[0].deep1', [
                            leaf('b[0].sub1_ortho[0].deep2') ]),
                        composite('b[0].sub1_ortho[1].deep1', [
                            leaf('b[0].sub1_ortho[1].deep2') ]),
                    ]),

                ]),
                composite('b[1].sub2', [
                    leaf('b[1].sub2a'),
                    composite('b[1].sub2b', [
                        leaf('b[1].deep')
                    ]),
                ]),
            ])
        ]

        assert reformat(states, {}) == (exp_states, {})

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

        _, renamed_trans = reformat(states, trans)
        assert renamed_trans == expected_trans


    def test_reformat_miro_machine(self):
        states, _ = reformat(*make_miro_machine(use_logging=False))
        expected_states = [
            composite('top', [
                composite('s', [
                    composite('s1', [
                        leaf('s11')
                    ]),
                    composite('s2', [
                        composite('s21', [
                            leaf('s211')
                        ])
                    ])
                ]),
                leaf('final')
            ])
        ]
        assert states == expected_states
