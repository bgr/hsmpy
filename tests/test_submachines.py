import pytest
from hsmpy import HSM  # , EventBus
from hsmpy.statemachine import (_rename, _rename_transitions, _get_response,
                                _get_state_by_name)
from hsmpy import Initial
from hsmpy import Transition as T
from hsmpy import LocalTransition as Local
from predefined_machines import make_submachines_machine, A, B, F, TERMINATE


class Test_renaming_transitions():
    def test_with_prefix(self):
        trans = {
            'top': {
                Initial: T('blah'),
                A: T('something'),
            },
            'left': {
                B: T('right'),
            }
        }

        expected_trans = {
            ('prefix', 0, 'top'): {
                Initial: T(('prefix', 0, 'blah')),
                A: T(('prefix', 0, 'something')),
            },
            ('prefix', 0, 'left'): {
                B: T(('prefix', 0, 'right')),
            }
        }

        res = _rename_transitions(trans, ('prefix', 0))
        assert res == expected_trans


class Test_renaming(object):
    def setup_class(self):
        # this will branch 4 times
        deep = {
            'top': {
                'nested_deep_1': {
                    'nested_deepest': {}
                },
                'nested_deep_2': {},
            }
        }
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
                    (deep, deep_trans),
                    (deep, deep_trans),
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


        expected_mid_0_deep_0 = {
            ('nested', 0, 'nested_mid', 0, 'top'): {
                ('nested', 0, 'nested_mid', 0, 'nested_deep_1'): {
                    ('nested', 0, 'nested_mid', 0, 'nested_deepest'): {}
                },
                ('nested', 0, 'nested_mid', 0, 'nested_deep_2'): {},
            }
        }
        expected_mid_0_deep_1 = {
            ('nested', 0, 'nested_mid', 1, 'top'): {
                ('nested', 0, 'nested_mid', 1, 'nested_deep_1'): {
                    ('nested', 0, 'nested_mid', 1, 'nested_deepest'): {}
                },
                ('nested', 0, 'nested_mid', 1, 'nested_deep_2'): {},
            }
        }
        expected_mid_1_deep_0 = {
            ('nested', 1, 'nested_mid', 0, 'top'): {
                ('nested', 1, 'nested_mid', 0, 'nested_deep_1'): {
                    ('nested', 1, 'nested_mid', 0, 'nested_deepest'): {}
                },
                ('nested', 1, 'nested_mid', 0, 'nested_deep_2'): {},
            }
        }
        expected_mid_1_deep_1 = {
            ('nested', 1, 'nested_mid', 1, 'top'): {
                ('nested', 1, 'nested_mid', 1, 'nested_deep_1'): {
                    ('nested', 1, 'nested_mid', 1, 'nested_deepest'): {}
                },
                ('nested', 1, 'nested_mid', 1, 'nested_deep_2'): {},
            }
        }

        expected_mid_0 = {
            ('nested', 0, 'top'): {
                ('nested', 0, 'nested_mid'):
                [
                    expected_mid_0_deep_0, expected_mid_0_deep_1
                ]
            }
        }

        expected_mid_1 = {
            ('nested', 1, 'top'): {
                ('nested', 1, 'nested_mid'):
                [
                    expected_mid_1_deep_0, expected_mid_1_deep_1
                ]
            }
        }


        self.expected_states = {
            ('top',): {
                ('nested',):
                [
                    expected_mid_0, expected_mid_1
                ],
                ('dumb',): {}
            }
        }
        self.expected_trans = {  # all transition dicts are flattened into one
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

        self.renamed_states, self.renamed_trans = _rename(states, trans)


    def test_renamed_transitions(self):
        assert self.renamed_trans == self.expected_trans

    def test_renamed_states(self):
        assert self.renamed_states == self.expected_states



# collective state description format:
# state_descr = state_name:str | submachines_state:tuple
# submachines_state = (state_name, state_descr, state_descr, ...)

# single state addressing format:
# state_addr = state_name:str | submachine_addr:tuple
# submachine_addr = (state_name, index, addr)

responding_submachines = [
    # element format:
    # ( [list, of, states], EVENT,
    #   [list, of, responding, states],
    #   [list, of, transition, targets] )

    # 'left's submachine is in 'start' state - responds to A and TERMINATE
    ([('left', 0, 'start')], TERMINATE,
     [('left', 0, 'top')],
     [('left', 0, 'final')]),

    ([('left', 0, 'start')], A,
     [('left', 0, 'start')],
     [('left', 0, 'right')]),

    # 'left's submachine is in 'right' state - ditto
    ([('left', 0, 'right')], TERMINATE,
     [('left', 0, 'right')],
     [('left', 0, 'final')]),

    ([('left', 0, 'right')], A,
     [('left', 0, 'right')],
     [('left', 0, 'start')]),

    # 'left's submachine is in 'final' state - doesn't respond to A
    ([('left', 0, 'final')], A,
     [('left',)],  # toplevel 'left' responds, transitions to 'right'
     [('right',)]),

    ([('left', 0, 'start')], B,  # only toplevel 'left' responds to B
     [('left',)],
     [('right',)]),

    ([('left', 0, 'start')], F,  # nobody responds to F
     [],
     []),

    # 'subs' has two submachines
    ([('subs', 0, 'start'), ('subs', 1, 'start')], A,
     [('subs', 0, 'start'), ('subs', 1, 'start')],  # states that responded
     [('subs', 0, 'right'), ('subs', 1, 'right')]),  # states to transition to

    ([('subs', 0, 'start'), ('subs', 1, 'right')], A,
     [('subs', 0, 'start'), ('subs', 1, 'right')],
     [('subs', 0, 'right'), ('subs', 1, 'start')]),

    ([('subs', 0, 'start'), ('subs', 1, 'final')], A,
     [('subs', 0, 'start')],  # only first responds
     [('subs', 0, 'right')]),

    ([('subs', 0, 'final'), ('subs', 1, 'right')], A,
     [('subs', 1, 'right')],  # only second responds
     [('subs', 1, 'start')]),

    ([('subs', 0, 'final'), ('subs', 1, 'final')], A,
     [('subs',)],  # submachines don't respond, 'subs' transitions to 'dumb'
     [('dumb',)]),

    ([('dumb',)], A,
     [('right',)],
     [('left',)]),
]


class Test_get_response_submachines(object):

    def setup_class(self):
        states, trans = make_submachines_machine()
        self.hsm = HSM(states, trans)

    @pytest.mark.parametrize(('from_states', 'EventType',
                              'expected_responding_states',
                              'expected_transition_targets'),
                             responding_submachines)
    def test_run(self, from_states, EventType, expected_responding_states,
                 expected_transition_targets):
        starting_states = [_get_state_by_name(state_id, self.hsm.flattened)
                           for state_id in from_states]

        resp_states, trans = _get_response(starting_states, EventType(),
                                           self.hsm.trans, None)

        assert len(resp_states) == len(expected_responding_states)
        resp_ids = set([st.id for st in resp_states])
        assert resp_ids == set(expected_responding_states)

        assert len(trans) == len(expected_transition_targets)
        target_ids = set([tr.target for tr in trans])
        assert target_ids == set(expected_transition_targets)

#class Test_submachines_transition_sequence(object):
    #def setup_class(self):
        #states, trans = make_submachines_machine()
        #self.hsm = HSM(states, trans)


#class Test_submachines_working(object):
    #def setup_class(self):
        #states, trans = make_submachines_machine()
        #self.hsm = HSM(states, trans)
        #self.eb = EventBus()

    #def test_enters_submachines_after_start(self):
        #self.hsm.start(self.eb)
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,
        #}

    #def test_event_A_captured_by_left_submachine(self):
        #self.eb.dispatch(A())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,

            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,
        #}

    #def test_terminate_left_submachine(self):
        #self.eb.dispatch(TERMINATE())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,
            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,

            #'left[0].right_exit': 1,
            #'left[0].final_enter': 1,
        #}

    #def test_event_A_transitions_to_right(self):
        #self.eb.dispatch(A())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,
            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,
            #'left[0].right_exit': 1,
            #'left[0].final_enter': 1,

            #'left[0].final_exit': 1,
            #'left[0].top_exit': 1,
            #'left_exit': 1,
            #'right_enter': 1,
            #'subs_enter': 1,
            #'subs[0].top_enter': 1,
            #'subs[0].left_enter': 1,
            #'subs[1].top_enter': 1,
            #'subs[1].left_enter': 1,
        #}

    #def test_event_A_captured_by_right_submachines(self):
        #self.eb.dispatch(A())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,
            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,
            #'left[0].right_exit': 1,
            #'left[0].final_enter': 1,
            #'left[0].final_exit': 1,
            #'left[0].top_exit': 1,
            #'left_exit': 1,
            #'right_enter': 1,
            #'subs_enter': 1,
            #'subs[0].top_enter': 1,
            #'subs[0].left_enter': 1,
            #'subs[1].top_enter': 1,
            #'subs[1].left_enter': 1,

            #'subs[0].left_exit': 1,
            #'subs[0].right_enter': 1,
            #'subs[1].left_exit': 1,
            #'subs[1].right_enter': 1,
        #}
        #self.eb.dispatch(A())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,
            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,
            #'left[0].right_exit': 1,
            #'left[0].final_enter': 1,
            #'left[0].final_exit': 1,
            #'left[0].top_exit': 1,
            #'left_exit': 1,
            #'right_enter': 1,
            #'subs_enter': 1,
            #'subs[0].top_enter': 1,
            #'subs[1].top_enter': 1,
            #'subs[0].left_exit': 1,
            #'subs[0].right_enter': 1,
            #'subs[1].left_exit': 1,
            #'subs[1].right_enter': 1,

            #'subs[0].right_exit': 1,
            #'subs[0].left_enter': 2,
            #'subs[1].right_exit': 1,
            #'subs[1].left_enter': 2,
        #}

    #def test_terminate_right_submachine(self):
        #self.eb.dispatch(TERMINATE())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,
            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,
            #'left[0].right_exit': 1,
            #'left[0].final_enter': 1,
            #'left[0].final_exit': 1,
            #'left[0].top_exit': 1,
            #'left_exit': 1,
            #'right_enter': 1,
            #'subs_enter': 1,
            #'subs[0].top_enter': 1,
            #'subs[1].top_enter': 1,
            #'subs[0].right_enter': 1,
            #'subs[1].right_enter': 1,
            #'subs[0].right_exit': 1,
            #'subs[0].left_enter': 2,
            #'subs[1].right_exit': 1,
            #'subs[1].left_enter': 2,

            #'subs[0].left_exit': 2,
            #'subs[1].final_enter': 1,
            #'subs[1].left_exit': 2,
            #'subs[1].final_enter': 1,
        #}

    #def test_event_A_transitions_to_dumb(self):
        #self.eb.dispatch(A())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left_enter': 1,
            #'left[0].top_enter': 1,
            #'left[0].left_enter': 1,
            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,
            #'left[0].right_exit': 1,
            #'left[0].final_enter': 1,
            #'left[0].final_exit': 1,
            #'left[0].top_exit': 1,
            #'left_exit': 1,
            #'right_enter': 1,
            #'subs_enter': 1,
            #'subs[0].top_enter': 1,
            #'subs[1].top_enter': 1,
            #'subs[0].right_enter': 1,
            #'subs[1].right_enter': 1,
            #'subs[0].right_exit': 1,
            #'subs[0].left_enter': 2,
            #'subs[1].right_exit': 1,
            #'subs[1].left_enter': 2,
            #'subs[0].left_exit': 2,
            #'subs[1].final_enter': 1,
            #'subs[1].left_exit': 2,
            #'subs[1].final_enter': 1,

            #'subs[0].final_exit': 1,
            #'subs[0].top_exit': 1,
            #'subs[1].final_exit': 1,
            #'subs[1].top_exit': 1,
            #'subs_exit': 1,
            #'dumb_enter': 1,
        #}

    #def test_event_A_transitions_to_left_again(self):
        #self.eb.dispatch(A())
        #assert self.hsm.data._log == {
            #'top_enter': 1,
            #'left[0].left_exit': 1,
            #'left[0].right_enter': 1,
            #'left[0].right_exit': 1,
            #'left[0].final_enter': 1,
            #'left[0].final_exit': 1,
            #'left[0].top_exit': 1,
            #'left_exit': 1,
            #'right_enter': 1,
            #'subs_enter': 1,
            #'subs[0].top_enter': 1,
            #'subs[1].top_enter': 1,
            #'subs[0].right_enter': 1,
            #'subs[1].right_enter': 1,
            #'subs[0].right_exit': 1,
            #'subs[0].left_enter': 2,
            #'subs[1].right_exit': 1,
            #'subs[1].left_enter': 2,
            #'subs[0].left_exit': 2,
            #'subs[1].final_enter': 1,
            #'subs[1].left_exit': 2,
            #'subs[1].final_enter': 1,
            #'subs[0].final_exit': 1,
            #'subs[0].top_exit': 1,
            #'subs[1].final_exit': 1,
            #'subs[1].top_exit': 1,
            #'subs_exit': 1,
            #'dumb_enter': 1,

            #'dumb_exit': 1,
            #'right_exit': 1,
            #'left_enter': 2,
            #'left[0].top_enter': 2,
            #'left[0].left_enter': 2,
        #}
