from hsmpy import HSM, EventBus
from reusable import (A, B, TERMINATE,
                      make_submachines_machine,
                      make_submachines_async_machine)


def assert_names(hsm, *state_names):
    hsm_names = [st.name for st in hsm.current_state_set]
    hsm_names_set = set(hsm_names)
    assert len(hsm_names) == len(hsm_names_set)
    assert hsm_names_set == set(state_names)


class Test_all_submachines_respond_to_event(object):
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
        assert_names(self.hsm, 'left[0].start', 'left[0].top', 'left', 'top')

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
        assert_names(self.hsm, 'left[0].right', 'left[0].top', 'left', 'top')

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
        assert_names(self.hsm, 'left[0].final', 'left[0].top', 'left', 'top')

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
        assert_names(self.hsm, 'subs[0].start', 'subs[0].top', 'subs',
                     'subs[1].start', 'subs[1].top', 'subs', 'right',
                     'top')

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
        assert_names(self.hsm, 'subs[0].right', 'subs[0].top', 'subs',
                     'subs[1].right', 'subs[1].top', 'subs', 'right',
                     'top')

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
        assert_names(self.hsm, 'subs[0].start', 'subs[0].top', 'subs',
                     'subs[1].start', 'subs[1].top', 'subs', 'right',
                     'top')

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
        assert_names(self.hsm, 'subs[0].final', 'subs[0].top', 'subs',
                     'subs[1].final', 'subs[1].top', 'subs', 'right',
                     'top')

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
        assert_names(self.hsm, 'dumb', 'right', 'top')

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
        assert_names(self.hsm, 'left[0].start', 'left[0].top', 'left', 'top')


# make sure that submachine remains in HSM state set even if it didin't
# respond to the event

class Test_submachines_some_respond(object):
    def setup_class(self):
        states, trans = make_submachines_async_machine(use_logging=True)
        self.hsm = HSM(states, trans)
        self.eb = EventBus()

    def test_enters_submachines_after_start(self):
        self.hsm.start(self.eb)
        assert self.hsm.data._log == {
            'top_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[0].left_enter': 1,
            'subs[1].top_enter': 1,
            'subs[1].left_enter': 1,
        }
        assert_names(self.hsm, 'subs[0].left', 'subs[0].top', 'subs[1].left',
                     'subs[1].top', 'subs', 'top')

    def test_first_responds_to_A(self):
        self.eb.dispatch(A())
        assert self.hsm.data._log == {
            'top_enter': 1,
            'subs_enter': 1,
            'subs[0].top_enter': 1,
            'subs[0].left_enter': 1,
            'subs[1].top_enter': 1,
            'subs[1].left_enter': 1,

            'subs[0].left_exit': 1,
            'subs[0].right_enter': 1,
        }
        assert_names(self.hsm, 'subs[0].right', 'subs[0].top', 'subs[1].left',
                     'subs[1].top', 'subs', 'top')

    def test_second_responds_to_B(self):
        self.eb.dispatch(B())
        assert self.hsm.data._log == {
            'top_enter': 1,
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
        assert_names(self.hsm, 'subs[0].right', 'subs[0].top', 'subs[1].right',
                     'subs[1].top', 'subs', 'top')
