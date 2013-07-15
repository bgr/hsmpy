from hsmpy import HSM, EventBus
from hsmpy.statemachine import _rename, _rename_transitions
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
        expected_mid_0_deep_0_trans = {
            ('nested', 0, 'nested_mid', 0, 'top'): {
                Initial: T(('nested', 0, 'nested_mid', 0, 'nested_deep_2')),
            },
            ('nested', 0, 'nested_mid', 0, 'nested_deep_1'): {
                A: T(('nested', 0, 'nested_mid', 0, 'renaming is dumb')),
            }
        }
        expected_mid_0_deep_1_trans = {
            ('nested', 0, 'nested_mid', 1, 'top'): {
                Initial: T(('nested', 0, 'nested_mid', 1, 'nested_deep_2')),
            },
            ('nested', 0, 'nested_mid', 1, 'nested_deep_1'): {
                A: T(('nested', 0, 'nested_mid', 1, 'renaming is dumb')),
            }
        }
        expected_mid_1_deep_0_trans = {
            ('nested', 1, 'nested_mid', 0, 'top'): {
                Initial: T(('nested', 1, 'nested_mid', 0, 'nested_deep_2')),
            },
            ('nested', 1, 'nested_mid', 0, 'nested_deep_1'): {
                A: T(('nested', 1, 'nested_mid', 0, 'renaming is dumb')),
            }
        }
        expected_mid_1_deep_1_trans = {
            ('nested', 1, 'nested_mid', 1, 'top'): {
                Initial: T(('nested', 1, 'nested_mid', 1, 'nested_deep_2')),
            },
            ('nested', 1, 'nested_mid', 1, 'nested_deep_1'): {
                A: T(('nested', 1, 'nested_mid', 1, 'renaming is dumb')),
            }
        }


        expected_mid_0 = {
            ('nested', 0, 'top'): {
                ('nested', 0, 'nested_mid'):
                [
                    (expected_mid_0_deep_0, expected_mid_0_deep_0_trans),
                    (expected_mid_0_deep_1, expected_mid_0_deep_1_trans)
                ]
            }
        }

        expected_mid_1 = {
            ('nested', 1, 'top'): {
                ('nested', 1, 'nested_mid'):
                [
                    (expected_mid_1_deep_0, expected_mid_1_deep_0_trans),
                    (expected_mid_1_deep_1, expected_mid_1_deep_1_trans)
                ]
            }
        }
        expected_mid_0_trans = {
            ('nested', 0, 'top'): {
                Initial: T(('nested', 0, 'blah')),
            },
            ('nested', 0, 'nested_mid'): {
                A: Local(('nested', 0, 'fff')),
            }
        }
        expected_mid_1_trans = {
            ('nested', 1, 'top'): {
                Initial: T(('nested', 1, 'blah')),
            },
            ('nested', 1, 'nested_mid'): {
                A: Local(('nested', 1, 'fff')),
            }
        }

        self.expected_states = {
            ('top',): {
                ('nested',):
                [
                    (expected_mid_0, expected_mid_0_trans),
                    (expected_mid_1, expected_mid_1_trans),
                ],
                ('dumb',): {}
            }
        }
        self.expected_trans = {
            ('top',): {
                Initial: T(('nested',)),
            },
            ('dumb',): {
                A: Local(('top',))
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

responding = [
    # left's submachine in left state - responds to A and TERMINATE
    (('left', ['left']), TERMINATE,
     [('left', 0, 'top')],
     [('left', 0, 'final')]),

    (('left', ['left']), A, 'left',
     [('left', 0, 'left')],
     [('left', 0, 'right')]),

    # left's submachine in right state - ditto
    (('left', ['right']), TERMINATE,
     [('left', 0, 'right')],
     [('left', 0, 'final')]),

    (('left', ['right']), A,
     [('left', 0, 'right')],
     [('left', 0, 'left')]),

    # left's submachine is in final state - doesn't respond to A
    (('left', ['final']), A,
     ['left'],
     ['right']),  # toplevel left responds, transitions to right

    (('left', ['left']), B,  # only toplevel left responds to B
     ['left'],
     ['right']),

    (('left', ['left']), F,  # nobody responds to F
     [],
     []),

    (('subs', ['left', 'left']), A,  # both submachines are in 'left' state
     [('subs', 0, 'left'), ('subs', 1, 'left')],  # states that responded
     [('subs', 0, 'right'), ('subs', 1, 'right')]),  # states to transition to

    (('subs', ['left', 'right']), A,
     [('subs', 0, 'left'), ('subs', 1, 'right')],
     [('subs', 0, 'right'), ('subs', 1, 'left')]),

    (('subs', ['left', 'final']), A,
     [('subs', 0, 'left')],  # only first responds
     [('subs', 0, 'right')]),

    (('subs', ['final', 'right']), A,
     [('subs', 1, 'right')],  # only second responds
     [('subs', 1, 'left')]),

    (('subs', ['final', 'final']), A,
     ['subs'],  # submachines don't respond, 'subs' transitions to 'dumb'
     ['dumb']),

    ('dumb', A,
     ['right'],
     ['left']),
]


#class Test_get_response_submachines(object):

    #def setup_class(self):
        #self.states, self.trans = make_miro_machine()
        #self.hsm = HSM(self.states, self.trans)

    #@pytest.mark.parametrize(('from_state', 'on_event',
                              #'expected_responding_state',
                              #'expected_transition_target'),
                             #responding_reguardless)
    #def test_run(self, from_state, on_event, expected_responding_state,
                 #expected_transition_target):
        #mock_hsm = MockHSM()
        #from_state = _get_state_by_name(from_state, self.hsm.flattened)

        #resp_state, tran = _get_response(from_state, on_event(),
                                         #self.trans, mock_hsm)

        #assert resp_state.name == expected_responding_state
        #assert tran.target == expected_transition_target

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
