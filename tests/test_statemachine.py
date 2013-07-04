from hsmpy.statemachine import State, StateMachine
from hsmpy.statemachine import Transition as T
from hsmpy.eventbus import EventBus


class Test_simple_two_state_door_machine():
    def setup_class(self):
        self.eb = EventBus()
        check = {
            'closed_enter': 0,
            'closed_exit': 0,
            'opened_enter': 0,
            'opened_exit': 0,
            'trans_opening': 0,
            'trans_closing': 0,
        }
        self.check = check

        def get_callback(key):
            def func():
                self.check[key] += 1
            return func

        # simple machine with two states and two transitions

        class Closed(State):
            def enter(self):
                check['closed_enter'] += 1

            def exit(self):
                check['closed_exit'] += 1

        class Opened(State):
            def enter(self):
                check['opened_enter'] += 1

            def exit(self):
                check['opened_exit'] += 1

        closed = Closed()
        opened = Opened()

        self.trans_map = {
            closed: [
                T('open', opened, get_callback('trans_opening')) ],
            opened: [
                T('close', closed, get_callback('trans_closing')) ],
        }
        self.closed = closed
        self.opened = opened
        self.fsm = StateMachine(self.trans_map, self.closed, self.eb)

    def test_transitions_not_allowed_before_start(self):
        assert self.fsm.current_state == 'NullState'
        assert all([v == 0 for v in self.check.values()])
        assert not self.fsm.can_transition('close')
        assert not self.fsm.can_transition('open')

    def test_in_closed_state_after_starting(self):
        self.fsm.start()
        assert self.fsm.current_state == 'Closed'
        assert self.check['closed_enter'] == 1
        assert self.check.values().count(0) == 5
        assert not self.fsm.can_transition('close')
        assert self.fsm.can_transition('open')

    def test_transition_to_opened(self):
        self.eb.dispatch('open')
        assert self.fsm.current_state == 'Opened'
        assert self.check['closed_enter'] == 1
        assert self.check['closed_exit'] == 1  # changed
        assert self.check['opened_enter'] == 1  # changed
        assert self.check['opened_exit'] == 0
        assert self.check['trans_opening'] == 1  # changed
        assert self.check['trans_closing'] == 0
        assert self.fsm.can_transition('close')
        assert not self.fsm.can_transition('open')

    def test_ignores_open_when_already_opened(self):
        self.eb.dispatch('open')
        assert self.fsm.current_state == 'Opened'
        assert self.check['closed_enter'] == 1
        assert self.check['closed_exit'] == 1
        assert self.check['opened_enter'] == 1
        assert self.check['opened_exit'] == 0
        assert self.check['trans_opening'] == 1
        assert self.check['trans_closing'] == 0
        assert self.fsm.can_transition('close')
        assert not self.fsm.can_transition('open')

    def test_transition_to_closed(self):
        self.eb.dispatch('close')
        assert self.fsm.current_state == 'Closed'
        assert self.check['closed_enter'] == 2  # changed
        assert self.check['closed_exit'] == 1
        assert self.check['opened_enter'] == 1
        assert self.check['opened_exit'] == 1  # changed
        assert self.check['trans_opening'] == 1
        assert self.check['trans_closing'] == 1  # changed
        assert not self.fsm.can_transition('close')
        assert self.fsm.can_transition('open')

    def test_ignores_close_when_already_closed(self):
        self.eb.dispatch('close')
        assert self.fsm.current_state == 'Closed'
        assert self.check['closed_enter'] == 2
        assert self.check['closed_exit'] == 1
        assert self.check['opened_enter'] == 1
        assert self.check['opened_exit'] == 1
        assert self.check['trans_opening'] == 1
        assert self.check['trans_closing'] == 1
        assert not self.fsm.can_transition('close')
        assert self.fsm.can_transition('open')

    def test_transition_to_opened_again(self):
        self.eb.dispatch('open')
        assert self.fsm.current_state == 'Opened'
        assert self.check['closed_enter'] == 2
        assert self.check['closed_exit'] == 2  # changed
        assert self.check['opened_enter'] == 2  # changed
        assert self.check['opened_exit'] == 1
        assert self.check['trans_opening'] == 2  # changed
        assert self.check['trans_closing'] == 1
        assert self.fsm.can_transition('close')
        assert not self.fsm.can_transition('open')

    def test_transition_to_closed_again(self):
        self.eb.dispatch('close')
        assert self.fsm.current_state == 'Closed'
        assert self.check['closed_enter'] == 3  # changed
        assert self.check['closed_exit'] == 2
        assert self.check['opened_enter'] == 2
        assert self.check['opened_exit'] == 2  # changed
        assert self.check['trans_opening'] == 2
        assert self.check['trans_closing'] == 2  # changed
        assert not self.fsm.can_transition('close')
        assert self.fsm.can_transition('open')


class Test_loops_and_multiple_paths_machine():
    def setup_class(self):
        self.eb = EventBus()
        check = {
            'start_enter': 0,
            'start_exit': 0,
            'goal_enter': 0,
            'goal_exit': 0,
            'trans_left': 0,
            'trans_right': 0,
            'trans_loop': 0,
            'trans_restart': 0,
        }
        self.check = check

        def get_callback(key):
            def func():
                self.check[key] += 1
            return func

        # machine that has two possible transitions from 'start' to 'goal'
        # and also a loop from 'goal' to itself

        class Start(State):
            def enter(self):
                check['start_enter'] += 1

            def exit(self):
                check['start_exit'] += 1

        class Goal(State):
            def enter(self):
                check['goal_enter'] += 1

            def exit(self):
                check['goal_exit'] += 1

        start = Start()
        goal = Goal()

        self.trans_map = {
            start: [
                T('left', goal, get_callback('trans_left')),
                T('right', goal, get_callback('trans_right')), ],
            goal: [
                T('loop', goal, get_callback('trans_loop')),
                T('restart', start, get_callback('trans_restart')), ],
        }
        self.start = start
        self.goal = goal
        self.fsm = StateMachine(self.trans_map, self.start, self.eb)

    def test_transitions_not_allowed_before_start(self):
        assert self.fsm.current_state == 'NullState'
        assert all([v == 0 for v in self.check.values()])
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert not self.fsm.can_transition('loop')
        assert not self.fsm.can_transition('restart')

    def test_in_start_state_after_starting(self):
        self.fsm.start()
        assert self.fsm.current_state == 'Start'
        assert self.check['start_enter'] == 1
        assert self.check.values().count(0) == 7
        assert self.fsm.can_transition('left')
        assert self.fsm.can_transition('right')
        assert not self.fsm.can_transition('loop')
        assert not self.fsm.can_transition('restart')

    def test_transition_to_goal_via_right(self):
        self.eb.dispatch('right')
        assert self.fsm.current_state == 'Goal'
        assert self.check['start_enter'] == 1
        assert self.check['start_exit'] == 1  # changed
        assert self.check['goal_enter'] == 1  # changed
        assert self.check['goal_exit'] == 0
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1  # changed
        assert self.check['trans_loop'] == 0
        assert self.check['trans_restart'] == 0
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert self.fsm.can_transition('loop')
        assert self.fsm.can_transition('restart')

    def test_loop_in_goal(self):
        self.eb.dispatch('loop')
        assert self.fsm.current_state == 'Goal'
        assert self.check['start_enter'] == 1
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 2  # changed
        assert self.check['goal_exit'] == 1  # changed
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 1  # changed
        assert self.check['trans_restart'] == 0
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert self.fsm.can_transition('loop')
        assert self.fsm.can_transition('restart')
        self.eb.dispatch('loop')
        assert self.fsm.current_state == 'Goal'
        assert self.check['start_enter'] == 1
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 3  # changed
        assert self.check['goal_exit'] == 2  # changed
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 2  # changed
        assert self.check['trans_restart'] == 0
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert self.fsm.can_transition('loop')
        assert self.fsm.can_transition('restart')
        self.eb.dispatch('loop')
        assert self.fsm.current_state == 'Goal'
        assert self.check['start_enter'] == 1
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 4  # changed
        assert self.check['goal_exit'] == 3  # changed
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 3  # changed
        assert self.check['trans_restart'] == 0
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert self.fsm.can_transition('loop')
        assert self.fsm.can_transition('restart')

    def test_ignore_left_and_right_events_while_in_goal(self):
        self.eb.dispatch('left')
        assert self.fsm.current_state == 'Goal'
        assert self.check['start_enter'] == 1
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 4
        assert self.check['goal_exit'] == 3
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 3
        assert self.check['trans_restart'] == 0
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert self.fsm.can_transition('loop')
        assert self.fsm.can_transition('restart')
        self.eb.dispatch('right')
        assert self.fsm.current_state == 'Goal'
        assert self.check['start_enter'] == 1
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 4
        assert self.check['goal_exit'] == 3
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 3
        assert self.check['trans_restart'] == 0
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert self.fsm.can_transition('loop')
        assert self.fsm.can_transition('restart')

    def test_restart(self):
        self.eb.dispatch('restart')
        assert self.fsm.current_state == 'Start'
        assert self.check['start_enter'] == 2  # changed
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 4
        assert self.check['goal_exit'] == 4  # changed
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 3
        assert self.check['trans_restart'] == 1  # changed
        assert self.fsm.can_transition('left')
        assert self.fsm.can_transition('right')
        assert not self.fsm.can_transition('loop')
        assert not self.fsm.can_transition('restart')

    def test_ignore_loop_and_restart_events_while_in_start(self):
        self.eb.dispatch('loop')
        assert self.fsm.current_state == 'Start'
        assert self.check['start_enter'] == 2
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 4
        assert self.check['goal_exit'] == 4
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 3
        assert self.check['trans_restart'] == 1
        assert self.fsm.can_transition('left')
        assert self.fsm.can_transition('right')
        assert not self.fsm.can_transition('loop')
        assert not self.fsm.can_transition('restart')
        self.eb.dispatch('restart')
        assert self.fsm.current_state == 'Start'
        assert self.check['start_enter'] == 2
        assert self.check['start_exit'] == 1
        assert self.check['goal_enter'] == 4
        assert self.check['goal_exit'] == 4
        assert self.check['trans_left'] == 0
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 3
        assert self.check['trans_restart'] == 1
        assert self.fsm.can_transition('left')
        assert self.fsm.can_transition('right')
        assert not self.fsm.can_transition('loop')
        assert not self.fsm.can_transition('restart')

    def test_transition_to_goal_via_left(self):
        self.eb.dispatch('left')
        assert self.fsm.current_state == 'Goal'
        assert self.check['start_enter'] == 2
        assert self.check['start_exit'] == 2  # changed
        assert self.check['goal_enter'] == 5  # changed
        assert self.check['goal_exit'] == 4
        assert self.check['trans_left'] == 1  # changed
        assert self.check['trans_right'] == 1
        assert self.check['trans_loop'] == 3
        assert self.check['trans_restart'] == 1
        assert not self.fsm.can_transition('left')
        assert not self.fsm.can_transition('right')
        assert self.fsm.can_transition('loop')
        assert self.fsm.can_transition('restart')


class Test_listening_to_external_events_machine():
    def setup_class(self):
        eb = EventBus()
        check = {
            'value': 0,
            'added_total': 0,
            'subtracted_total': 0,
            'button_pressed': 0,
            'add_enter': 0,
            'add_exit': 0,
            'subtract_enter': 0,
            'subtract_exit': 0,
        }
        self.eb = eb
        self.check = check

        # machine that behaves like hysteresis
        # states will trigger switching by # dispatching 'full' and
        # 'empty' events when 'value' is >= 5 and <= 0

        class Adding(State):
            def __init__(self):
                self._interests = {
                    'button_pressed': self.add,
                }

            def enter(self):
                check['add_enter'] += 1

            def exit(self):
                check['add_exit'] += 1

            def add(self, evt, n):
                check['value'] += n
                check['added_total'] += n
                if check['value'] >= 5:
                    eb.dispatch('full')

        class Subtracting(State):
            def __init__(self):
                self._interests = {
                    'button_pressed': self.subtract,
                }

            def enter(self):
                check['subtract_enter'] += 1

            def exit(self):
                check['subtract_exit'] += 1

            def subtract(self, evt, n):
                check['value'] -= n
                check['subtracted_total'] += n
                if check['value'] <= 0:
                    eb.dispatch('empty')

        def on_button_pressed(evt, aux):
            check['button_pressed'] += 1

        def press_button(_, n):
            eb.dispatch('button_pressed', n)

        self.press_button = press_button
        eb.register('button_pressed', on_button_pressed)

        adding = Adding()
        subtracting = Subtracting()

        self.trans_map = {
            adding: [ T('full', subtracting), ],
            subtracting: [ T('empty', adding), ],
        }
        self.adding = adding
        self.subtracting = subtracting
        self.fsm = StateMachine(self.trans_map, self.adding, self.eb)

    def test_transitions_not_allowed_before_start(self):
        assert self.fsm.current_state == 'NullState'
        assert all([v == 0 for v in self.check.values()])
        assert not self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')

    def test_button_pressing_does_nothing_before_start(self):
        self.press_button(1)
        assert self.fsm.current_state == 'NullState'
        assert self.check['value'] == 0
        assert self.check['added_total'] == 0
        assert self.check['subtracted_total'] == 0
        assert self.check['button_pressed'] == 1  # changed
        assert self.check['add_enter'] == 0
        assert self.check['add_exit'] == 0
        assert self.check['subtract_enter'] == 0
        assert self.check['subtract_exit'] == 0
        assert not self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')
        self.press_button(3)
        assert self.fsm.current_state == 'NullState'
        assert self.check['value'] == 0
        assert self.check['added_total'] == 0
        assert self.check['subtracted_total'] == 0
        assert self.check['button_pressed'] == 2  # changed
        assert self.check['add_enter'] == 0
        assert self.check['add_exit'] == 0
        assert self.check['subtract_enter'] == 0
        assert self.check['subtract_exit'] == 0
        assert not self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')

    def test_in_adding_state_after_starting(self):
        self.fsm.start()
        assert self.fsm.current_state == 'Adding'
        assert self.check['value'] == 0
        assert self.check['added_total'] == 0
        assert self.check['subtracted_total'] == 0
        assert self.check['button_pressed'] == 2
        assert self.check['add_enter'] == 1  # changed
        assert self.check['add_exit'] == 0
        assert self.check['subtract_enter'] == 0
        assert self.check['subtract_exit'] == 0
        assert self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')

    def test_add_on_button_press(self):
        self.press_button(1)  # = 1
        assert self.fsm.current_state == 'Adding'
        assert self.check['value'] == 1  # changed
        assert self.check['added_total'] == 1  # changed
        assert self.check['subtracted_total'] == 0
        assert self.check['button_pressed'] == 3  # changed
        assert self.check['add_enter'] == 1
        assert self.check['add_exit'] == 0
        assert self.check['subtract_enter'] == 0
        assert self.check['subtract_exit'] == 0
        assert self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')
        self.press_button(3)  # = 4
        assert self.fsm.current_state == 'Adding'
        assert self.check['value'] == 4  # changed
        assert self.check['added_total'] == 4  # changed
        assert self.check['subtracted_total'] == 0
        assert self.check['button_pressed'] == 4  # changed
        assert self.check['add_enter'] == 1
        assert self.check['add_exit'] == 0
        assert self.check['subtract_enter'] == 0
        assert self.check['subtract_exit'] == 0
        assert self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')

    def test_switch_state_to_subtracting_on_next_button_press(self):
        self.press_button(2)  # = 6, switch since it's > 5
        assert self.fsm.current_state == 'Subtracting'
        assert self.check['value'] == 6  # changed
        assert self.check['added_total'] == 6  # changed
        assert self.check['subtracted_total'] == 0
        assert self.check['button_pressed'] == 5  # changed
        assert self.check['add_enter'] == 1
        assert self.check['add_exit'] == 1  # changed
        assert self.check['subtract_enter'] == 1  # changed
        assert self.check['subtract_exit'] == 0
        assert not self.fsm.can_transition('full')
        assert self.fsm.can_transition('empty')

    def test_subtract_on_button_press(self):
        self.press_button(1)  # = 5
        assert self.fsm.current_state == 'Subtracting'
        assert self.check['value'] == 5  # changed
        assert self.check['added_total'] == 6
        assert self.check['subtracted_total'] == 1  # changed
        assert self.check['button_pressed'] == 6  # changed
        assert self.check['add_enter'] == 1
        assert self.check['add_exit'] == 1
        assert self.check['subtract_enter'] == 1
        assert self.check['subtract_exit'] == 0
        assert not self.fsm.can_transition('full')
        assert self.fsm.can_transition('empty')
        self.press_button(4)  # = 1
        assert self.fsm.current_state == 'Subtracting'
        assert self.check['value'] == 1  # changed
        assert self.check['added_total'] == 6
        assert self.check['subtracted_total'] == 5  # changed
        assert self.check['button_pressed'] == 7  # changed
        assert self.check['add_enter'] == 1
        assert self.check['add_exit'] == 1
        assert self.check['subtract_enter'] == 1
        assert self.check['subtract_exit'] == 0
        assert not self.fsm.can_transition('full')
        assert self.fsm.can_transition('empty')

    def test_switch_state_to_adding_on_next_button_press(self):
        self.press_button(2)  # = -1, switch since it's < 0
        assert self.fsm.current_state == 'Adding'
        assert self.check['value'] == -1  # changed
        assert self.check['added_total'] == 6
        assert self.check['subtracted_total'] == 7  # changed
        assert self.check['button_pressed'] == 8  # changed
        assert self.check['add_enter'] == 2  # changed
        assert self.check['add_exit'] == 1
        assert self.check['subtract_enter'] == 1
        assert self.check['subtract_exit'] == 1  # changed
        assert self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')

    def test_again_add_on_button_press(self):
        self.press_button(1)  # = 0
        assert self.fsm.current_state == 'Adding'
        assert self.check['value'] == 0  # changed
        assert self.check['added_total'] == 7  # changed
        assert self.check['subtracted_total'] == 7
        assert self.check['button_pressed'] == 9  # changed
        assert self.check['add_enter'] == 2
        assert self.check['add_exit'] == 1
        assert self.check['subtract_enter'] == 1
        assert self.check['subtract_exit'] == 1
        assert self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')
        self.press_button(3)  # = 3
        assert self.fsm.current_state == 'Adding'
        assert self.check['value'] == 3  # changed
        assert self.check['added_total'] == 10  # changed
        assert self.check['subtracted_total'] == 7
        assert self.check['button_pressed'] == 10  # changed
        assert self.check['add_enter'] == 2
        assert self.check['add_exit'] == 1
        assert self.check['subtract_enter'] == 1
        assert self.check['subtract_exit'] == 1
        assert self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')

    def test_switch_state_again_to_subtracting_on_next_button_press(self):
        self.press_button(4)  # = 7, switch
        assert self.fsm.current_state == 'Subtracting'
        assert self.check['value'] == 7  # changed
        assert self.check['added_total'] == 14  # changed
        assert self.check['subtracted_total'] == 7
        assert self.check['button_pressed'] == 11  # changed
        assert self.check['add_enter'] == 2
        assert self.check['add_exit'] == 2  # changed
        assert self.check['subtract_enter'] == 2  # changed
        assert self.check['subtract_exit'] == 1
        assert not self.fsm.can_transition('full')
        assert self.fsm.can_transition('empty')

    def test_switch_state_again_to_adding_on_next_button_press(self):
        self.press_button(7)  # = 0, switch
        assert self.fsm.current_state == 'Adding'
        assert self.check['value'] == 0  # changed
        assert self.check['added_total'] == 14
        assert self.check['subtracted_total'] == 14  # changed
        assert self.check['button_pressed'] == 12  # changed
        assert self.check['add_enter'] == 3  # changed
        assert self.check['add_exit'] == 2
        assert self.check['subtract_enter'] == 2
        assert self.check['subtract_exit'] == 2  # changed
        assert self.fsm.can_transition('full')
        assert not self.fsm.can_transition('empty')
