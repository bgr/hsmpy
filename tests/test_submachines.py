from hsmpy import HSM, EventBus, Initial
from hsmpy import Transition as T
from hsmpy import LocalTransition as Local
from predefined_machines import A, TERMINATE
from predefined_machines import (LoggingCompositeState, LoggingState,
                                 LoggingSubmachinesState)


# machine testing "orthogonal" regions, aka SubmachinesState
# it has two regular CompositeStates: 'left' and 'right'
# left contains SubmachinesState with one submachine
# right contains SubmachinesState with two submachines
# submachines respond to events A and TERMINATE
# submachines are allowed to have states with same names as parent machine,
# since submachines' states are renamed to be unique


class Test_orthogonal(object):
    def setup_class(self):
        submachines = []
        for i in range(3):  # make a couple of identical machines
            sub_states = {
                'top': LoggingCompositeState({
                    'left': LoggingState(),
                    'right': LoggingState(),
                    'final': LoggingState(),
                })
            }
            sub_trans = {
                'top': {
                    Initial: T('left'),
                    TERMINATE: Local('final'),
                },
                'left': {
                    A: T('right'),
                },
                'right': {
                    A: Local('left'),  # should fail validation
                }
            }
            submachines += [(sub_states, sub_trans)]

        # TODO: make HSM non-destructive to prevent duplication like this

        states = {
            'top': LoggingCompositeState({
                'left': LoggingSubmachinesState([
                    submachines[0],
                ]),
                'right': LoggingCompositeState({
                    'dumb': LoggingState(),
                    'subs': LoggingSubmachinesState([
                        submachines[1],
                        submachines[2],
                    ]),
                }),
            })
        }

        trans = {
            'top': {
                Initial: T('left'),
            },
            'left': {
                A: T('right'),
            },
            'right': {
                Initial: T('subs'),
                A: T('left'),  # dumb will ignore A thus transitioning to left
            },
            'subs': {
                A: T('dumb'),  # shouldn't fire if submachine responds
            }
        }

        self.hsm = HSM(states, trans)
        self.eb = EventBus()

    def test_enters_submachines_after_start(self):
        self.hsm.start(self.eb)
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,
        }

    def test_event_A_captured_by_left_submachine(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,

            'left[0].left_exit': 1,
            'left[0].right_enter': 1,
        }

    def test_terminate_left_submachine(self):
        self.eb.dispatch(TERMINATE())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,
            'left[0].left_exit': 1,
            'left[0].right_enter': 1,

            'left[0].right_exit': 1,
            'left[0].final_enter': 1,
        }

    def test_event_A_transitions_to_right(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,
            'left[0].left_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,

            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[0].left_enter': 1,
            'subs[1].top_enter': 1,
            'subs[1].left_enter': 1,
        }

    def test_event_A_captured_by_right_submachines(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,
            'left[0].left_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,
            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[0].left_enter': 1,
            'subs[1].top_enter': 1,
            'subs[1].left_enter': 1,

            'subs[0].left_exit': 1,
            'subs[0].right_enter': 1,
            'subs[1].left_exit': 1,
            'subs[1].right_enter': 1,
        }
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,
            'left[0].left_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,
            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[1].top_enter': 1,
            'subs[0].left_exit': 1,
            'subs[0].right_enter': 1,
            'subs[1].left_exit': 1,
            'subs[1].right_enter': 1,

            'subs[0].right_exit': 1,
            'subs[0].left_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].left_enter': 2,
        }

    def test_terminate_right_submachine(self):
        self.eb.dispatch(TERMINATE())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,
            'left[0].left_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,
            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[1].top_enter': 1,
            'subs[0].right_enter': 1,
            'subs[1].right_enter': 1,
            'subs[0].right_exit': 1,
            'subs[0].left_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].left_enter': 2,

            'subs[0].left_exit': 2,
            'subs[1].final_enter': 1,
            'subs[1].left_exit': 2,
            'subs[1].final_enter': 1,
        }

    def test_event_A_transitions_to_dumb(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].left_enter': 1,
            'left[0].left_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,
            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[1].top_enter': 1,
            'subs[0].right_enter': 1,
            'subs[1].right_enter': 1,
            'subs[0].right_exit': 1,
            'subs[0].left_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].left_enter': 2,
            'subs[0].left_exit': 2,
            'subs[1].final_enter': 1,
            'subs[1].left_exit': 2,
            'subs[1].final_enter': 1,

            'subs[0].final_exit': 1,
            'subs[0].top_exit': 1,
            'subs[1].final_exit': 1,
            'subs[1].top_exit': 1,
            'subs_exit': 1,
            'dumb_enter': 1,
        }

    def test_event_A_transitions_to_left_again(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left[0].left_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,
            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[1].top_enter': 1,
            'subs[0].right_enter': 1,
            'subs[1].right_enter': 1,
            'subs[0].right_exit': 1,
            'subs[0].left_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].left_enter': 2,
            'subs[0].left_exit': 2,
            'subs[1].final_enter': 1,
            'subs[1].left_exit': 2,
            'subs[1].final_enter': 1,
            'subs[0].final_exit': 1,
            'subs[0].top_exit': 1,
            'subs[1].final_exit': 1,
            'subs[1].top_exit': 1,
            'subs_exit': 1,
            'dumb_enter': 1,

            'dumb_exit': 1,
            'right_exit': 1,
            'left_enter': 2,
            'left[0].top_enter': 2,
            'left[0].left_enter': 2,
        }
