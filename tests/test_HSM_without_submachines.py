import pytest
xfail = pytest.mark.xfail

from hsmpy import HSM, EventBus, Event, Initial
from hsmpy.logic import get_path_from_root, get_state_by_sig
from reusable import make_miro_machine, logging, A, B, C, D, E, G, I

S, T, Local, Internal, Choice = logging


def assert_curr_state(hsm, leaf_name):
    """Check that HSM's state set is same as set of states from root to leaf"""
    exp_set = set(
        get_path_from_root(
            get_state_by_sig((leaf_name,), hsm.flattened)))
    assert hsm.current_state_set == exp_set


# simple machine with two states and two transitions


class Closed(S): pass  # note that S is LoggingState
class Opened(S): pass

class CloseDoor(Event): pass
class OpenDoor(Event): pass


class Test_simple_two_state_door_machine:
    def setup_class(self):
        self.eb = EventBus()

        self.states = {
            'top': S({
                'closed': Closed(),
                'opened': Opened(),
            })
        }

        self.trans = {
            'top': {
                Initial: T('closed'),
            },
            'closed': {
                OpenDoor: T('opened'),
            },
            'opened': {
                CloseDoor: T('closed'),
            }
        }
        self.hsm = HSM(self.states, self.trans)

    def test_doesnt_respond_to_events_before_starting(self):
        assert not hasattr(self.hsm.data, '_log')
        self.eb.dispatch(OpenDoor())
        self.eb.dispatch(CloseDoor())
        assert not hasattr(self.hsm.data, '_log')

    def test_in_closed_state_after_starting(self):
        self.hsm.start(self.eb)
        assert_curr_state(self.hsm, 'closed')
        assert self.hsm.data._log == [
            'top-entry',
            'top-Initial',
            'closed-entry',
        ]

    def test_ignores_close_while_closed(self):
        self.hsm.data._log = []
        self.eb.dispatch(CloseDoor())
        assert_curr_state(self.hsm, 'closed')
        assert self.hsm.data._log == [
            # no change
        ]

    def test_transition_to_opened(self):
        self.hsm.data._log = []
        self.eb.dispatch(OpenDoor())
        assert_curr_state(self.hsm, 'opened')
        assert self.hsm.data._log == [
            'closed-exit',
            'closed-OpenDoor',
            'opened-entry',
        ]

    def test_ignores_open_while_opened(self):
        self.hsm.data._log = []
        self.eb.dispatch(OpenDoor())
        assert_curr_state(self.hsm, 'opened')
        assert self.hsm.data._log == [
            # no change
        ]

    def test_transition_to_closed(self):
        self.hsm.data._log = []  # TODO: do this in setup_method
        self.eb.dispatch(CloseDoor())
        assert_curr_state(self.hsm, 'closed')
        assert self.hsm.data._log == [
            'opened-exit',
            'opened-CloseDoor',
            'closed-entry',
        ]

    def test_ignores_close_while_closed_again(self):
        self.hsm.data._log = []
        self.eb.dispatch(CloseDoor())
        assert_curr_state(self.hsm, 'closed')
        assert self.hsm.data._log == [
            # no change
        ]

    def test_transition_to_opened_again(self):
        self.hsm.data._log = []
        self.eb.dispatch(OpenDoor())
        assert_curr_state(self.hsm, 'opened')
        assert self.hsm.data._log == [
            'closed-exit',
            'closed-OpenDoor',
            'opened-entry',
        ]

    def test_transition_to_closed_again(self):
        self.hsm.data._log = []
        self.eb.dispatch(CloseDoor())
        assert_curr_state(self.hsm, 'closed')
        assert self.hsm.data._log == [
            'opened-exit',
            'opened-CloseDoor',
            'closed-entry',
        ]

    def test_doesnt_respond_to_events_after_stopping(self):
        self.hsm.data._log = []
        self.hsm.stop()
        self.eb.dispatch(CloseDoor())
        self.eb.dispatch(OpenDoor())
        assert self.hsm.data._log == [
            # no change
        ]


# machine that has two possible transitions from 'start' to 'goal'
# a loop from 'goal' to itself, and external transition to top state


class Start(S): pass
class Goal(S): pass

class MoveLeft(Event): pass
class MoveRight(Event): pass
class Loop(Event): pass
class Restart(Event): pass


class Test_loops_and_multiple_paths_machine():

    def setup_class(self):
        self.eb = EventBus()

        self.start = Start()
        self.goal = Goal()

        self.states = {
            'top': S({
                'start': self.start,
                'goal': self.goal,
            })
        }
        self.trans = {
            'top': {
                Initial: T('start'),
            },
            'start': {
                MoveLeft: T('goal'),
                MoveRight: T('goal'),
            },
            'goal': {
                Loop: T('goal'),
                Restart: T('top'),
            }
        }
        self.hsm = HSM(self.states, self.trans)

    def test_doesnt_respond_to_events_before_starting(self):
        assert not hasattr(self.hsm.data, '_log')
        self.eb.dispatch(MoveLeft())
        self.eb.dispatch(MoveRight())
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert not hasattr(self.hsm.data, '_log')

    def test_in_start_state_after_starting(self):
        self.hsm.start(self.eb)
        assert_curr_state(self.hsm, 'start')
        assert self.hsm.data._log == [
            'top-entry',
            'top-Initial',
            'start-entry',
        ]

    def test_ignore_loop_and_restart_events_while_in_start(self):
        self.hsm.data._log = []
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert_curr_state(self.hsm, 'start')
        assert self.hsm.data._log == [
            # no change
        ]

    def test_transition_to_goal_via_right(self):
        self.hsm.data._log = []
        self.eb.dispatch(MoveRight())
        assert_curr_state(self.hsm, 'goal')
        assert self.hsm.data._log == [
            'start-exit',
            'start-MoveRight',
            'goal-entry',
        ]

    def test_ignore_left_and_right_events_while_in_goal(self):
        self.hsm.data._log = []
        self.eb.dispatch(MoveLeft())
        self.eb.dispatch(MoveRight())
        assert_curr_state(self.hsm, 'goal')
        assert self.hsm.data._log == [
            # no change
        ]

    def test_loop_in_goal(self):
        self.hsm.data._log = []
        self.eb.dispatch(Loop())
        assert_curr_state(self.hsm, 'goal')
        assert self.hsm.data._log == [
            'goal-exit',
            'goal-Loop',
            'goal-entry',
        ]

        self.hsm.data._log = []
        self.eb.dispatch(Loop())
        assert_curr_state(self.hsm, 'goal')
        assert self.hsm.data._log == [
            'goal-exit',
            'goal-Loop',
            'goal-entry',
        ]


    def test_restart(self):
        self.hsm.data._log = []
        self.eb.dispatch(Restart())
        assert_curr_state(self.hsm, 'start')
        assert self.hsm.data._log == [
            'goal-exit',
            'top-exit',
            'goal-Restart',
            'top-entry',
            'top-Initial',
            'start-entry',
        ]

    def test_ignore_loop_and_restart_events_while_in_start_2(self):
        self.hsm.data._log = []
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert self.hsm.data._log == [
            # no change
        ]

    def test_transition_to_goal_via_left(self):
        self.hsm.data._log = []
        self.eb.dispatch(MoveLeft())
        assert_curr_state(self.hsm, 'goal')
        assert self.hsm.data._log == [
            'start-exit',
            'start-MoveLeft',
            'goal-entry',
        ]

    def test_doesnt_respond_to_events_after_stopping(self):
        self.hsm.data._log = []
        self.hsm.stop()
        self.eb.dispatch(MoveLeft())
        self.eb.dispatch(MoveRight())
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert self.hsm.data._log == [
            # no change
        ]


# machine that dispatches events on its own causing infinite loop
# and stops after hsm.data.count >= 2000


class SteppingState(S):
    def enter(self, hsm):
        if hsm.data.count < 2000:
            hsm.eb.dispatch(Step())


class Step(Event):
    pass


class Test_perpetual_machine:

    def setup_class(self):
        self.eb = EventBus()

        def increase(evt, hsm):
            hsm.data.count += 1

        self.states = {
            'top': S({
                'a': SteppingState(),
                'b': SteppingState(),
            })
        }
        self.trans = {
            'top': {
                Initial: T('a'),
            },
            'a': {
                Step: T('b', action=increase),
            },
            'b': {
                Step: T('a'),
            }
        }
        self.hsm = HSM(self.states, self.trans)
        self.hsm.data.count = 0

    def test_stops_after_2000_cycles(self):
        self.hsm.start(self.eb)
        assert self.hsm.data.count == 2000




# cycle Miro test machine with event sequence featured in the pdf example


class Test_miro_machine:
    def setup_class(self):
        self.states, self.trans = make_miro_machine(use_logging=True)
        self.hsm = HSM(self.states, self.trans)
        self.eb = EventBus()

    def test_step_1_in_s211_after_starting(self):
        self.hsm.start(self.eb)
        assert_curr_state(self.hsm, 's211')
        assert self.hsm.data.foo is False
        assert self.hsm.data._log == [
            'top-entry',
            'top-Initial',
            's-entry',
            's2-entry',
            's2-Initial',
            's21-entry',
            's211-entry',
        ]

    def test_step_2_in_s11_after_G(self):
        self.hsm.data._log = []
        self.eb.dispatch(G())
        assert_curr_state(self.hsm, 's11')
        assert self.hsm.data._log == [
            's211-exit',
            's21-exit',
            's2-exit',
            's21-G',
            's1-entry',
            's1-Initial',
            's11-entry',
        ]

    def test_step_3_dont_change_foo_after_I(self):
        self.hsm.data._log = []
        assert self.hsm.data.foo is False
        self.eb.dispatch(I())
        assert self.hsm.data.foo is False
        assert_curr_state(self.hsm, 's11')
        assert self.hsm.data._log == [
            's1-I',
        ]

    def test_step_4_in_s11_after_A(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        assert_curr_state(self.hsm, 's11')
        assert self.hsm.data._log == [
            's11-exit',
            's1-exit',
            's1-A',
            's1-entry',
            's1-Initial',
            's11-entry',
        ]


    def test_step_5_in_s11_after_D(self):
        self.hsm.data._log = []
        assert self.hsm.data.foo is False
        self.eb.dispatch(D())
        assert self.hsm.data.foo is True
        assert_curr_state(self.hsm, 's11')
        assert self.hsm.data._log == [
            's11-exit',
            's1-exit',
            's1-D',
            's-Initial',
            's1-entry',
            's11-entry',
        ]

    def test_step_6_in_s11_after_D(self):
        self.hsm.data._log = []
        assert self.hsm.data.foo is True
        self.eb.dispatch(D())
        assert self.hsm.data.foo is False
        assert_curr_state(self.hsm, 's11')
        assert self.hsm.data._log == [
            's11-exit',
            's11-D',
            's1-Initial',
            's11-entry',
        ]

    def test_step_7_in_s211_after_C(self):
        self.hsm.data._log = []
        self.eb.dispatch(C())
        assert_curr_state(self.hsm, 's211')
        assert self.hsm.data._log == [
            's11-exit',
            's1-exit',
            's1-C',
            's2-entry',
            's2-Initial',
            's21-entry',
            's211-entry',
        ]

    def test_step_8_in_s11_after_E(self):
        self.hsm.data._log = []
        self.eb.dispatch(E())
        assert_curr_state(self.hsm, 's11')
        assert self.hsm.data._log == [
            's211-exit',
            's21-exit',
            's2-exit',
            's-E',
            's1-entry',
            's11-entry',
        ]

    def test_step_9_in_s11_after_E(self):
        self.hsm.data._log = []
        self.eb.dispatch(E())
        assert_curr_state(self.hsm, 's11')
        assert self.hsm.data._log == [
            's11-exit',
            's1-exit',
            's-E',
            's1-entry',
            's11-entry',
        ]

    def test_step_10_in_s211_after_G(self):
        self.hsm.data._log = []
        self.eb.dispatch(G())
        assert_curr_state(self.hsm, 's211')
        assert self.hsm.data._log == [
            's11-exit',
            's1-exit',
            's11-G',
            's2-entry',
            's21-entry',
            's211-entry',
        ]

    def test_step_11_s2_responds_to_I(self):
        self.hsm.data._log = []
        assert self.hsm.data.foo is False
        self.eb.dispatch(I())
        assert self.hsm.data.foo is True
        assert self.hsm.data._log == [
            's2-I',
        ]

    def test_step_12_s_responds_to_I(self):
        self.hsm.data._log = []
        assert self.hsm.data.foo is True
        self.eb.dispatch(I())
        assert self.hsm.data.foo is False
        assert self.hsm.data._log == [
            's-I',
        ]



class Test_internal_transitions:

    def setup_class(self):
        states = {
            'top': S(states={
                'idle': S(),
                'working': S({
                    'leaf': S(),
                })
            })
        }

        self.foo = 0

        def increment_foo(evt, hsm):
            self.foo += 1

        trans = {
            'top': {
                Initial: T('idle'),
                A: Internal(action=increment_foo),
                B: Internal(action=increment_foo),
                C: Internal(action=increment_foo),
            },
            'idle': {
                Step: T('leaf'),
                A: Internal(action=increment_foo),
                B: Internal(action=increment_foo),
            },
            'working': {
                Initial: T('leaf'),
                A: Internal(action=increment_foo),
                B: Internal(action=increment_foo),
            },
            'leaf': {
                A: Internal(action=increment_foo),
            },
        }

        self.eb = EventBus()
        self.hsm = HSM(states, trans)

    def test_in_idle_after_starting(self):
        self.hsm.start(self.eb)
        assert_curr_state(self.hsm, 'idle')
        assert self.hsm.data._log == [
            'top-entry',
            'top-Initial',
            'idle-entry',
        ]
        assert self.foo == 0

    def test_idle_responds_to_A(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        assert self.hsm.data._log == ['idle-A']
        assert_curr_state(self.hsm, 'idle')
        assert self.foo == 1

    def test_idle_responds_to_B(self):
        self.hsm.data._log = []
        self.eb.dispatch(B())
        assert self.hsm.data._log == ['idle-B']
        assert_curr_state(self.hsm, 'idle')
        assert self.foo == 2

    def test_top_responds_to_C_from_idle(self):
        self.hsm.data._log = []
        self.eb.dispatch(C())
        assert self.hsm.data._log == ['top-C']
        assert_curr_state(self.hsm, 'idle')
        assert self.foo == 3

    def test_in_leaf_after_dispatching_Step(self):
        self.hsm.data._log = []
        self.eb.dispatch(Step())
        assert self.hsm.data._log == [
            'idle-exit',
            'idle-Step',
            'working-entry',
            'leaf-entry',
        ]
        assert_curr_state(self.hsm, 'leaf')
        assert self.foo == 3

    def test_leaf_responds_to_A(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        assert self.hsm.data._log == ['leaf-A']
        assert_curr_state(self.hsm, 'leaf')
        assert self.foo == 4

    def test_working_responds_to_B_from_leaf(self):
        self.hsm.data._log = []
        self.eb.dispatch(B())
        assert self.hsm.data._log == ['working-B']
        assert_curr_state(self.hsm, 'leaf')
        assert self.foo == 5

    def test_top_responds_to_C_from_leaf(self):
        self.hsm.data._log = []
        self.eb.dispatch(C())
        assert self.hsm.data._log == ['top-C']
        assert_curr_state(self.hsm, 'leaf')
        assert self.foo == 6



class Test_Choice_as_initial_transitions:
    def setup_class(self):
        states = {
            'top': S({
                'A': S(),
                'B': S(),
                'C': S({
                    'C_left': S(),
                    'C_right': S(),
                })
            })
        }

        key = lambda _, hsm: hsm.data.foo % 3

        trans = {
            'top': {
                Initial: Choice({ 0: 'A', 1: 'B', 2: 'C' },
                                key=key, default='B')
            },
            'A': {
                Step: Local('top'),
            },
            'B': {
                Step: T('top'),
            },
            'C': {
                Initial: Choice({ False: 'C_left', True: 'C_right' },
                                key=lambda _, hsm: hsm.data.foo % 2 == 0,
                                default='C_left'),
                Step: T('top'),
            },
        }

        self.eb = EventBus()
        self.hsm = HSM(states, trans)

    def test_start_in_B_foo_1(self):
        self.hsm.data.foo = 1
        self.hsm.start(self.eb)
        assert self.hsm.data._log == [
            'top-entry',
            'top-Initial',
            'B-entry',
        ]
        assert_curr_state(self.hsm, 'B')

    def test_in_A_foo_0(self):
        self.hsm.data._log = []
        self.hsm.data.foo = 0
        self.eb.dispatch(Step())
        assert self.hsm.data._log == [
            'B-exit',
            'top-exit',
            'B-Step',
            'top-entry',
            'top-Initial',
            'A-entry',
        ]
        assert_curr_state(self.hsm, 'A')

    def test_in_C_right_foo_2(self):
        self.hsm.data._log = []
        self.hsm.data.foo = 2
        self.eb.dispatch(Step())
        assert self.hsm.data._log == [
            'A-exit',
            'A-Step',
            'top-Initial',
            'C-entry',
            'C-Initial',
            'C_right-entry',
        ]
        assert_curr_state(self.hsm, 'C_right')

    def test_in_C_left_foo_5(self):
        self.hsm.data._log = []
        self.hsm.data.foo = 5
        self.eb.dispatch(Step())
        assert self.hsm.data._log == [
            'C_right-exit',
            'C-exit',
            'top-exit',
            'C-Step',
            'top-entry',
            'top-Initial',
            'C-entry',
            'C-Initial',
            'C_left-entry',
        ]
        assert_curr_state(self.hsm, 'C_left')

    def test_in_A_left_foo_6(self):
        self.hsm.data._log = []
        self.hsm.data.foo = 6
        self.eb.dispatch(Step())
        assert self.hsm.data._log == [
            'C_left-exit',
            'C-exit',
            'top-exit',
            'C-Step',
            'top-entry',
            'top-Initial',
            'A-entry',
        ]
        assert_curr_state(self.hsm, 'A')



class Test_Choice_transitions_change_and_read_in_same_step:
    # tests the case where action in sequence changes some variable's value,
    # and Choice transition that comes later in the sequence should be able to
    # see updated value during the SAME transition sequence

    def setup_class(self):
        def set_foo(hsm):
            hsm.data.foo = 0

        def update_foo(hsm):
            hsm.data.foo += 1

        states = {
            'top': S(on_enter=set_foo, states={
                'states': S(on_enter=update_foo, states={
                    'a': S(),
                    'b': S(),
                }),
            }),
        }

        trans = {
            'top': {
                Initial: T('states'),
            },
            'states': {
                Initial: Choice(
                    {
                        0: 'a',
                        1: 'b',
                    },
                    default='a',
                    key=lambda _, h: h.data.foo % 2
                ),
                A: T('states'),  # will reenter and update foo
            }
        }

        self.hsm = HSM(states, trans)
        self.eb = EventBus()

    def test_foo_is_1_and_state_is_b_after_start(self):
        assert self.hsm.data is not None
        self.hsm.start(self.eb)
        assert self.hsm.data.foo == 1
        assert_curr_state(self.hsm, 'b')

    def test_foo_is_2_and_state_is_a_after_dispatch(self):
        self.eb.dispatch(A())
        assert self.hsm.data.foo == 2
        assert_curr_state(self.hsm, 'a')

    def test_foo_is_3_and_state_is_a_after_dispatch(self):
        self.eb.dispatch(A())
        assert self.hsm.data.foo == 3
        assert_curr_state(self.hsm, 'b')
