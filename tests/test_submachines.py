import pytest
from hsmpy import HSM, EventBus
from hsmpy.statemachine import get_responses, get_state_by_sig
from hsmpy import Initial
from hsmpy import Transition as T
from hsmpy import LocalTransition as Local
from predefined_machines import make_submachines_machine, A, B, F, TERMINATE




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
     [('left', 0, 'top')],
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
        states, trans = make_submachines_machine(use_logging=False)
        self.hsm = HSM(states, trans)

    @pytest.mark.parametrize(('from_states', 'Event',
                              'expected_responding_states',
                              'expected_transition_targets'),
                             responding_submachines)
    def test_run(self, from_states, Event, expected_responding_states,
                 expected_transition_targets):
        starting_states = [get_state_by_sig(sig, self.hsm.flattened)
                           for sig in from_states]
        resps = get_responses(starting_states, Event(), self.hsm.trans, None)

        if expected_responding_states or expected_transition_targets:
            _, resp_states, trans = zip(*resps)
            assert len(resp_states) == len(expected_responding_states)
            resp_sigs = set([st.sig for st in resp_states])
            assert resp_sigs == set(expected_responding_states)

            assert len(trans) == len(expected_transition_targets)
            target_ids = set([tr.target for tr in trans])
            assert target_ids == set(expected_transition_targets)
        else:
            assert resps == []


class Test_submachines_working(object):
    def setup_class(self):
        states, trans = make_submachines_machine(use_logging=True)
        self.hsm = HSM(states, trans)
        self.eb = EventBus()

    def test_enters_submachines_after_start(self):
        self.hsm.start(self.eb)
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].start_enter': 1,
        }

    def test_event_A_captured_by_left_submachine(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].start_enter': 1,

            'left[0].start_exit': 1,
            'left[0].right_enter': 1,
        }

    def test_terminate_left_submachine(self):
        self.eb.dispatch(TERMINATE())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].start_enter': 1,
            'left[0].start_exit': 1,
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
            'left[0].start_enter': 1,
            'left[0].start_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,

            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[0].start_enter': 1,
            'subs[1].top_enter': 1,
            'subs[1].start_enter': 1,
        }

    def test_event_A_captured_by_right_submachines(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].start_enter': 1,
            'left[0].start_exit': 1,
            'left[0].right_enter': 1,
            'left[0].right_exit': 1,
            'left[0].final_enter': 1,
            'left[0].final_exit': 1,
            'left[0].top_exit': 1,
            'left_exit': 1,
            'right_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[0].start_enter': 1,
            'subs[1].top_enter': 1,
            'subs[1].start_enter': 1,

            'subs[0].start_exit': 1,
            'subs[0].right_enter': 1,
            'subs[1].start_exit': 1,
            'subs[1].right_enter': 1,
        }

    def test_event_A_captured_by_right_submachines_again(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].start_enter': 1,
            'left[0].start_exit': 1,
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
            'subs[0].start_exit': 1,
            'subs[0].right_enter': 1,
            'subs[1].start_exit': 1,
            'subs[1].right_enter': 1,

            'subs[0].right_exit': 1,
            'subs[0].start_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].start_enter': 2,
        }

    def test_terminate_right_submachine(self):
        self.eb.dispatch(TERMINATE())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].start_enter': 1,
            'left[0].start_exit': 1,
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
            'subs[0].start_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].start_enter': 2,

            'subs[0].start_exit': 2,
            'subs[0].final_enter': 1,
            'subs[1].start_exit': 2,
            'subs[1].final_enter': 1,
        }

    def test_event_A_transitions_to_dumb(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].start_enter': 1,
            'left[0].start_exit': 1,
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
            'subs[0].start_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].start_enter': 2,
            'subs[0].start_exit': 2,
            'subs[0].final_enter': 1,
            'subs[1].start_exit': 2,
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
            'left[0].start_exit': 1,
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
            'subs[0].start_enter': 2,
            'subs[1].right_exit': 1,
            'subs[1].start_enter': 2,
            'subs[0].start_exit': 2,
            'subs[0].final_enter': 1,
            'subs[1].start_exit': 2,
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
            'left[0].start_enter': 2,
        }
