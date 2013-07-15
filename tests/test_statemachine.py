from hsmpy import HSM, State, CompositeState, EventBus, Event, Initial
from hsmpy import Transition as T
from predefined_machines import make_miro_machine
from predefined_machines import A, C, D, E, G, I
from predefined_machines import (LoggingCompositeState, LoggingState,
                                 LoggingSubmachinesState)


def get_callback(key):
    def func(evt, hsm):
        hsm.data[key] += 1
    return func

# simple machine with two states and two transitions


class Closed(State):
    def enter(self, evt, hsm):
        hsm.data['closed_enter'] += 1

    def exit(self, evt, hsm):
        hsm.data['closed_exit'] += 1


class Opened(State):
    def enter(self, evt, hsm):
        hsm.data['opened_enter'] += 1

    def exit(self, evt, hsm):
        hsm.data['opened_exit'] += 1


class CloseDoor(Event):
    pass


class OpenDoor(Event):
    pass


class Test_simple_two_state_door_machine():
    def setup_class(self):
        self.eb = EventBus()
        hsmdata = {
            'initial': 0,
            'closed_enter': 0,
            'closed_exit': 0,
            'opened_enter': 0,
            'opened_exit': 0,
            'trans_opening': 0,
            'trans_closing': 0,
        }

        self.closed = Closed()
        self.opened = Opened()

        self.states = {
            'top': CompositeState({
                'closed': self.closed,
                'opened': self.opened,
            })
        }

        self.trans = {
            'top': {
                Initial: T('closed', action=get_callback('initial')),
            },
            'closed': {
                OpenDoor: T('opened', action=get_callback('trans_opening'))
            },
            'opened': {
                CloseDoor: T('closed', action=get_callback('trans_closing'))
            }
        }
        self.hsm = HSM(self.states, self.trans)
        self.hsm.data = hsmdata

    def test_doesnt_respond_to_events_before_starting(self):
        assert all([v == 0 for v in self.hsm.data.values()])
        self.eb.dispatch(OpenDoor())
        self.eb.dispatch(CloseDoor())
        assert all([v == 0 for v in self.hsm.data.values()])

    def test_in_closed_state_after_starting(self):
        self.hsm.start(self.eb)
        assert self.hsm._current_state == self.closed
        assert self.hsm.data['initial'] == 1
        assert self.hsm.data['closed_enter'] == 1
        assert self.hsm.data.values().count(0) == 5

    def test_ignores_close_while_closed(self):
        self.eb.dispatch(CloseDoor())
        assert self.hsm._current_state == self.closed
        assert self.hsm.data['initial'] == 1
        assert self.hsm.data['closed_enter'] == 1
        assert self.hsm.data.values().count(0) == 5

    def test_transition_to_opened(self):
        self.eb.dispatch(OpenDoor())
        assert self.hsm._current_state == self.opened
        assert self.hsm.data['initial'] == 1
        assert self.hsm.data['closed_enter'] == 1
        assert self.hsm.data['closed_exit'] == 1  # changed
        assert self.hsm.data['opened_enter'] == 1  # changed
        assert self.hsm.data['opened_exit'] == 0
        assert self.hsm.data['trans_opening'] == 1  # changed
        assert self.hsm.data['trans_closing'] == 0

    def test_ignores_open_while_opened(self):
        self.eb.dispatch(OpenDoor())
        assert self.hsm._current_state == self.opened
        assert self.hsm.data['closed_enter'] == 1
        assert self.hsm.data['closed_exit'] == 1
        assert self.hsm.data['opened_enter'] == 1
        assert self.hsm.data['opened_exit'] == 0
        assert self.hsm.data['trans_opening'] == 1
        assert self.hsm.data['trans_closing'] == 0

    def test_transition_to_closed(self):
        self.eb.dispatch(CloseDoor())
        assert self.hsm._current_state == self.closed
        assert self.hsm.data['closed_enter'] == 2  # changed
        assert self.hsm.data['closed_exit'] == 1
        assert self.hsm.data['opened_enter'] == 1
        assert self.hsm.data['opened_exit'] == 1  # changed
        assert self.hsm.data['trans_opening'] == 1
        assert self.hsm.data['trans_closing'] == 1  # changed

    def test_ignores_close_while_closed_again(self):
        self.eb.dispatch(CloseDoor())
        assert self.hsm._current_state == self.closed
        assert self.hsm.data['closed_enter'] == 2
        assert self.hsm.data['closed_exit'] == 1
        assert self.hsm.data['opened_enter'] == 1
        assert self.hsm.data['opened_exit'] == 1
        assert self.hsm.data['trans_opening'] == 1
        assert self.hsm.data['trans_closing'] == 1

    def test_transition_to_opened_again(self):
        self.eb.dispatch(OpenDoor())
        assert self.hsm._current_state == self.opened
        assert self.hsm.data['closed_enter'] == 2
        assert self.hsm.data['closed_exit'] == 2  # changed
        assert self.hsm.data['opened_enter'] == 2  # changed
        assert self.hsm.data['opened_exit'] == 1
        assert self.hsm.data['trans_opening'] == 2  # changed
        assert self.hsm.data['trans_closing'] == 1

    def test_transition_to_closed_again(self):
        self.eb.dispatch(CloseDoor())
        assert self.hsm._current_state == self.closed
        assert self.hsm.data['initial'] == 1
        assert self.hsm.data['closed_enter'] == 3  # changed
        assert self.hsm.data['closed_exit'] == 2
        assert self.hsm.data['opened_enter'] == 2
        assert self.hsm.data['opened_exit'] == 2  # changed
        assert self.hsm.data['trans_opening'] == 2
        assert self.hsm.data['trans_closing'] == 2  # changed

    def test_doesnt_respond_to_events_after_stopping(self):
        self.hsm.stop()
        self.eb.dispatch(CloseDoor())
        self.eb.dispatch(OpenDoor())
        assert self.hsm.data['initial'] == 1
        assert self.hsm.data['closed_enter'] == 3  # changed
        assert self.hsm.data['closed_exit'] == 2
        assert self.hsm.data['opened_enter'] == 2
        assert self.hsm.data['opened_exit'] == 2  # changed
        assert self.hsm.data['trans_opening'] == 2
        assert self.hsm.data['trans_closing'] == 2  # changed


# machine that has two possible transitions from 'start' to 'goal'
# a loop from 'goal' to itself, and external transition to top state


class Start(State):
    def enter(self, evt, hsm):
        hsm.data['start_enter'] += 1

    def exit(self, evt, hsm):
        hsm.data['start_exit'] += 1


class Goal(State):
    def enter(self, evt, hsm):
        hsm.data['goal_enter'] += 1

    def exit(self, evt, hsm):
        hsm.data['goal_exit'] += 1


class MoveLeft(Event):
    pass


class MoveRight(Event):
    pass


class Loop(Event):
    pass


class Restart(Event):
    pass


class Test_loops_and_multiple_paths_machine():

    def setup_class(self):
        self.eb = EventBus()
        hsmdata = {
            'initial': 0,
            'start_enter': 0,
            'start_exit': 0,
            'goal_enter': 0,
            'goal_exit': 0,
            'trans_left': 0,
            'trans_right': 0,
            'trans_loop': 0,
            'trans_restart': 0,
        }

        self.start = Start()
        self.goal = Goal()

        self.states = {
            'top': CompositeState({
                'start': self.start,
                'goal': self.goal,
            })
        }
        self.trans = {
            'top': {
                Initial: T('start', action=get_callback('initial')),
            },
            'start': {
                MoveLeft: T('goal', action=get_callback('trans_left')),
                MoveRight: T('goal', action=get_callback('trans_right')),
            },
            'goal': {
                Loop: T('goal', action=get_callback('trans_loop')),
                Restart: T('top', action=get_callback('trans_restart')),
            }
        }
        self.hsm = HSM(self.states, self.trans)
        self.hsm.data = hsmdata

    def test_doesnt_respond_to_events_before_starting(self):
        assert all([v == 0 for v in self.hsm.data.values()])
        self.eb.dispatch(MoveLeft())
        self.eb.dispatch(MoveRight())
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert all([v == 0 for v in self.hsm.data.values()])

    def test_in_start_state_after_starting(self):
        self.hsm.start(self.eb)
        assert self.hsm._current_state == self.start
        assert self.hsm.data['initial'] == 1
        assert self.hsm.data['start_enter'] == 1
        assert self.hsm.data.values().count(0) == 7

    def test_ignore_loop_and_restart_events_while_in_start(self):
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert self.hsm._current_state == self.start
        assert self.hsm.data['initial'] == 1
        assert self.hsm.data['start_enter'] == 1
        assert self.hsm.data.values().count(0) == 7

    def test_transition_to_goal_via_right(self):
        self.eb.dispatch(MoveRight())
        assert self.hsm._current_state == self.goal
        assert self.hsm.data['start_enter'] == 1
        assert self.hsm.data['start_exit'] == 1  # changed
        assert self.hsm.data['goal_enter'] == 1  # changed
        assert self.hsm.data['goal_exit'] == 0
        assert self.hsm.data['trans_left'] == 0
        assert self.hsm.data['trans_right'] == 1  # changed
        assert self.hsm.data['trans_loop'] == 0
        assert self.hsm.data['trans_restart'] == 0

    def test_ignore_left_and_right_events_while_in_goal(self):
        self.eb.dispatch(MoveLeft())
        self.eb.dispatch(MoveRight())
        assert self.hsm._current_state == self.goal
        assert self.hsm.data['start_enter'] == 1
        assert self.hsm.data['start_exit'] == 1
        assert self.hsm.data['goal_enter'] == 1
        assert self.hsm.data['goal_exit'] == 0
        assert self.hsm.data['trans_left'] == 0
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 0
        assert self.hsm.data['trans_restart'] == 0

    def test_loop_in_goal(self):
        self.eb.dispatch(Loop())
        assert self.hsm._current_state == self.goal
        assert self.hsm.data['start_enter'] == 1
        assert self.hsm.data['start_exit'] == 1
        assert self.hsm.data['goal_enter'] == 2  # changed
        assert self.hsm.data['goal_exit'] == 1  # changed
        assert self.hsm.data['trans_left'] == 0
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 1  # changed
        assert self.hsm.data['trans_restart'] == 0
        self.eb.dispatch(Loop())
        assert self.hsm._current_state == self.goal
        assert self.hsm.data['start_enter'] == 1
        assert self.hsm.data['start_exit'] == 1
        assert self.hsm.data['goal_enter'] == 3  # changed
        assert self.hsm.data['goal_exit'] == 2  # changed
        assert self.hsm.data['trans_left'] == 0
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 2  # changed
        assert self.hsm.data['trans_restart'] == 0
        self.eb.dispatch(Loop())
        assert self.hsm._current_state == self.goal
        assert self.hsm.data['start_enter'] == 1
        assert self.hsm.data['start_exit'] == 1
        assert self.hsm.data['goal_enter'] == 4  # changed
        assert self.hsm.data['goal_exit'] == 3  # changed
        assert self.hsm.data['trans_left'] == 0
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 3  # changed
        assert self.hsm.data['trans_restart'] == 0

    def test_restart(self):
        assert self.hsm.data['initial'] == 1
        self.eb.dispatch(Restart())
        assert self.hsm._current_state == self.start
        assert self.hsm.data['initial'] == 2  # changed
        assert self.hsm.data['start_enter'] == 2  # changed
        assert self.hsm.data['start_exit'] == 1
        assert self.hsm.data['goal_enter'] == 4
        assert self.hsm.data['goal_exit'] == 4  # changed
        assert self.hsm.data['trans_left'] == 0
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 3
        assert self.hsm.data['trans_restart'] == 1  # changed

    def test_ignore_loop_and_restart_events_while_in_start_2(self):
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert self.hsm.data['initial'] == 2
        assert self.hsm.data['start_enter'] == 2
        assert self.hsm.data['start_exit'] == 1
        assert self.hsm.data['goal_enter'] == 4
        assert self.hsm.data['goal_exit'] == 4
        assert self.hsm.data['trans_left'] == 0
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 3
        assert self.hsm.data['trans_restart'] == 1

    def test_transition_to_goal_via_left(self):
        self.eb.dispatch(MoveLeft())
        assert self.hsm._current_state == self.goal
        assert self.hsm.data['start_enter'] == 2
        assert self.hsm.data['start_exit'] == 2  # changed
        assert self.hsm.data['goal_enter'] == 5  # changed
        assert self.hsm.data['goal_exit'] == 4
        assert self.hsm.data['trans_left'] == 1  # changed
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 3
        assert self.hsm.data['trans_restart'] == 1

    def test_doesnt_respond_to_events_after_stopping(self):
        self.hsm.stop()
        self.eb.dispatch(MoveLeft())
        self.eb.dispatch(MoveRight())
        self.eb.dispatch(Loop())
        self.eb.dispatch(Restart())
        assert self.hsm.data['initial'] == 2
        assert self.hsm.data['start_enter'] == 2
        assert self.hsm.data['start_exit'] == 2
        assert self.hsm.data['goal_enter'] == 5
        assert self.hsm.data['goal_exit'] == 4
        assert self.hsm.data['trans_left'] == 1
        assert self.hsm.data['trans_right'] == 1
        assert self.hsm.data['trans_loop'] == 3
        assert self.hsm.data['trans_restart'] == 1


# machine that dispatches events on its own causing infinite loop
# and stops after hsm.data.count >= 2000


class SteppingState(State):
    def enter(self, evt, hsm):
        if hsm.data.count < 2000:
            hsm.eb.dispatch(Step())


class Step(Event):
    pass


class Test_perpetual_machine(object):

    def setup_class(self):
        self.eb = EventBus()

        def increase(evt, hsm):
            hsm.data.count += 1

        self.states = {
            'top': CompositeState({
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


# testing that entry and exit actions are invoked




class Test_entry_exit_actions(object):
    def setup_class(self):
        self.states = {
            'top': LoggingCompositeState({
                'idle': LoggingState(),
                'drawing': LoggingCompositeState({
                    'drawing_rectangle': LoggingState(),
                    'drawing_circle': LoggingState(),
                })
            })
        }

        self.trans = {
            'top': {
                Initial: T('idle'),
            },
            'idle': {
                Step: T('drawing_rectangle'),
            },
            'drawing': {
                Initial: T('drawing_circle'),
                Step: T('idle'),
            },
        }

        self.eb = EventBus()
        self.hsm = HSM(self.states, self.trans)

    def test_in_idle_after_starting(self):
        self.hsm.start(self.eb)
        assert self.hsm._current_state.name == 'idle'

    def test_actions_invoked_after_starting(self):
        assert self.hsm.data._log == {
            'top_enter': 1,
            'idle_enter': 1,
        }

    def test_actions_invoked_after_dispatching_1(self):
        self.eb.dispatch(Step())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'idle_enter': 1,
            'idle_exit': 1,
            'drawing_enter': 1,
            'drawing_rectangle_enter': 1,
        }

    def test_actions_invoked_after_dispatching_2(self):
        self.eb.dispatch(Step())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'idle_enter': 2,
            'idle_exit': 1,
            'drawing_enter': 1,
            'drawing_rectangle_enter': 1,
            'drawing_rectangle_exit': 1,
            'drawing_exit': 1,
        }


# cycle Miro test machine with event sequence featured in the pdf example


class Test_miro_machine(object):
    def setup_class(self):
        self.states, self.trans = make_miro_machine()
        self.hsm = HSM(self.states, self.trans)
        self.eb = EventBus()

    def test_step_1_in_s211_after_starting(self):
        self.hsm.start(self.eb)
        assert self.hsm._current_state.name == 's211'
        assert self.hsm.data.foo is False

    def test_step_2_in_s11_after_G(self):
        self.eb.dispatch(G())
        assert self.hsm._current_state.name == 's11'

    def test_step_3_dont_change_foo_after_I(self):
        assert self.hsm.data.foo is False
        self.eb.dispatch(I())
        assert self.hsm.data.foo is False
        assert self.hsm._current_state.name == 's11'

    def test_step_4_in_s11_after_A(self):
        self.eb.dispatch(A())
        assert self.hsm._current_state.name == 's11'

    def test_step_5_in_s11_after_D(self):
        assert self.hsm.data.foo is False
        self.eb.dispatch(D())
        assert self.hsm.data.foo is True
        assert self.hsm._current_state.name == 's11'

    def test_step_6_in_s11_after_D(self):
        assert self.hsm.data.foo is True
        self.eb.dispatch(D())
        assert self.hsm.data.foo is False
        assert self.hsm._current_state.name == 's11'

    def test_step_7_in_s211_after_C(self):
        self.eb.dispatch(C())
        assert self.hsm._current_state.name == 's211'

    def test_step_8_in_s11_after_E(self):
        self.eb.dispatch(E())
        assert self.hsm._current_state.name == 's11'

    def test_step_9_in_s11_after_E(self):
        self.eb.dispatch(E())
        assert self.hsm._current_state.name == 's11'

    def test_step_10_in_s211_after_G(self):
        self.eb.dispatch(G())
        assert self.hsm._current_state.name == 's211'

    def test_step_11_s2_responds_to_I(self):
        assert self.hsm.data.foo is False
        self.eb.dispatch(I())
        assert self.hsm.data.foo is True

    def test_step_12_s_responds_to_I(self):
        assert self.hsm.data.foo is True
        self.eb.dispatch(I())
        assert self.hsm.data.foo is False
