from hsmpy import State, CompositeState, HSM, Event, EventBus
from hsmpy import Transition as T


class Top(CompositeState): pass
class Left(State): pass
class Right(State): pass

class MoveRight(Event): pass
class MoveLeft(Event): pass
class LoopInRight(Event): pass
class Ignored(Event): pass


class Test_basic_functionality(object):

    def setup_class(self):
        self.eb = EventBus()

    def test_can_instantiate(self):
        self.top = Top()
        self.left = Left()
        self.right = Right()

    def test_can_add_substates(self):
        returned = self.top(
            self.left,
            self.right
        )
        # states are callable and return self so they can be nested like this
        assert returned == self.top

    def test_can_access_substates(self):
        assert self.top.left == self.left
        assert self.top.right == self.right

    def test_can_set_transitions(self):
        self.top.initial(self.left)
        self.left.trans(
            T(MoveRight, self.right)
        )
        self.right.trans(
            T(LoopInRight, self.right),
            T(MoveLeft, self.left),
        )

    def test_can_create_HSM(self):
        self.hsm = HSM(self.top, self.eb)

    def test_has_internal_log(self):
        assert self.hsm._log == []

    def test_has_internal_data(self):
        assert self.hsm._data == {}

    def test_doesnt_respond_to_events_before_starting(self):
        assert not self.hsm.responds_to(MoveLeft)
        assert not self.hsm.responds_to(MoveRight)
        assert not self.hsm.responds_to(LoopInRight)
        assert not self.hsm.responds_to(Ignored)

    def test_not_in_any_state_before_starting(self):
        assert self.hsm._current_state == set([])

    def test_can_start(self):
        self.hsm.start()

    def test_in_initial_state_after_starting(self):
        self.hsm._current_state == set([Top, Left])

    def test_logged_starting(self):
        assert len(self.hsm._log) == 1
        assert self.hsm._log[-1] == ['Top-entry', 'Top-initial', 'Left-entry']

    def test_can_respond_to_events_after_starting(self):
        assert self.hsm.responds_to(MoveRight)
        assert not self.hsm.responds_to(MoveLeft)
        assert not self.hsm.responds_to(LoopInRight)
        assert not self.hsm.responds_to(Ignored)
        assert len(self.hsm._log) == 1  # respond_to doesn't have side-effects

    def test_transition_to_Right_on_event_dispatch(self):
        self.eb.dispatch(MoveRight())
        self.hsm._current_state == set([Top, Right])

    def test_logged_transition_to_Right(self):
        assert len(self.hsm._log) == 2
        assert self.hsm._log[-1] == ['Top-respond-MoveRight', 'Left-exit',
                                     'Right-entry']

    def test_responds_to_different_events_after_transition_to_Right(self):
        assert self.hsm.responds_to(MoveLeft)
        assert self.hsm.responds_to(LoopInRight)
        assert not self.hsm.responds_to(MoveRight)
        assert not self.hsm.responds_to(Ignored)
        assert len(self.hsm._log) == 2

    def test_loop_in_Right_on_event_dispatch(self):
        self.eb.dispatch(MoveRight())
        self.hsm._current_state == set([Top, Right])

    def test_logged_loop_in_Right(self):
        assert len(self.hsm._log) == 3
        assert self.hsm._log[-1] == ['Top-respond-LoopInRight', 'Right-exit',
                                     'Right-entry']

    def test_responds_to_same_events_after_loop_in_Right(self):
        assert self.hsm.responds_to(MoveLeft)
        assert self.hsm.responds_to(LoopInRight)
        assert not self.hsm.responds_to(MoveRight)
        assert not self.hsm.responds_to(Ignored)
        assert len(self.hsm._log) == 3

    def test_transition_to_Left_on_event_dispatch(self):
        self.eb.dispatch(MoveLeft())
        self.hsm._current_state == set([Top, Left])

    def test_logged_transition_to_Left(self):
        assert len(self.hsm._log) == 4
        assert self.hsm._log[-1] == ['Top-respond-MoveLeft', 'Right-exit',
                                     'Left-entry']

    def test_responds_to_different_events_after_transition_to_Left(self):
        assert self.hsm.responds_to(MoveRight)
        assert not self.hsm.responds_to(MoveLeft)
        assert not self.hsm.responds_to(LoopInRight)
        assert not self.hsm.responds_to(Ignored)
        assert len(self.hsm._log) == 4

# TODOs:
# substates can access shared hsm data
# substate._hsm == parent._hsm == hsm
# check transition actions (logging actions also?)
# check dispatching on transitions
# deferred events?
# dispatching events from substates
# final pseudostate?


class Test_erroneous(object):
    pass
    # loop cannot be local transition
    # local transition out of substate must end at parent
