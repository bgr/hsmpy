from hsmpy import HSM, EventBus, Initial, Choice, T
from reusable import (A, B, TERMINATE, make_submachines_machine,
                      make_submachines_async_machine, make_choice_machine,
                      LoggingState)


def assert_names(hsm, *state_names):
    hsm_names = [st.name for st in hsm.current_state_set]
    hsm_names_set = set(hsm_names)
    assert len(hsm_names) == len(hsm_names_set)
    assert hsm_names_set == set(state_names)


class Test_all_submachines_respond_to_event:
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

class Test_submachines_some_respond:
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



class Test_Choice_transitions:
    def setup_class(self):
        sub_states, sub_trans = make_choice_machine(use_logging=True)
        states = {
            'top': LoggingState({
                'left': LoggingState([
                    (sub_states, sub_trans),
                    (sub_states, sub_trans),
                ]),
                'right': LoggingState([
                    (sub_states, sub_trans),
                    (sub_states, sub_trans),
                ]),
            })
        }

        key = lambda _, hsm: hsm.data.foo % 2

        trans = {
            'top': {
                Initial: Choice({ 0: 'left', 1: 'right' },
                                key=key, default='left'),
                B: T('top'),
            },
        }

        self.eb = EventBus()
        self.hsm = HSM(states, trans)

    def test_start_in_right_C_foo_3(self):
        self.hsm.data.foo = 3
        self.hsm.start(self.eb)
        assert_names(self.hsm, 'top', 'right', 'right[0].top', 'right[0].A',
                     'right[0].B', 'right[0].C', 'right[1].top', 'right[1].A',
                     'right[1].B', 'right[1].C')
        assert self.hsm.data._log == {
            'top_enter': 1,
            'right_enter': 1,
            'right[0].top_enter': 1,
            'right[0].A_enter': 1,
            'right[0].B_enter': 1,
            'right[0].C_enter': 1,
            'right[1].top_enter': 1,
            'right[1].A_enter': 1,
            'right[1].B_enter': 1,
            'right[1].C_enter': 1,
        }

    def test_in_right_F_dispatch_A_5(self):
        self.eb.dispatch(A(5))
        assert_names(self.hsm, 'top', 'right', 'right[0].top', 'right[0].D',
                     'right[0].E', 'right[0].F', 'right[1].top', 'right[1].D',
                     'right[1].E', 'right[1].F')
        assert self.hsm.data._log == {
            'top_enter': 1,
            'right_enter': 1,
            'right[0].top_enter': 1,
            'right[0].A_enter': 1,
            'right[0].B_enter': 1,
            'right[0].C_enter': 1,
            'right[1].top_enter': 1,
            'right[1].A_enter': 1,
            'right[1].B_enter': 1,
            'right[1].C_enter': 1,

            'right[0].C_exit': 1,
            'right[0].B_exit': 1,
            'right[0].A_exit': 1,
            'right[0].D_enter': 1,
            'right[0].E_enter': 1,
            'right[0].F_enter': 1,
            'right[1].C_exit': 1,
            'right[1].B_exit': 1,
            'right[1].A_exit': 1,
            'right[1].D_enter': 1,
            'right[1].E_enter': 1,
            'right[1].F_enter': 1,
        }

    def test_in_left_F_dispatch_B_foo_4(self):
        self.hsm.data.foo = 4
        self.eb.dispatch(B())
        assert_names(self.hsm, 'top', 'left', 'left[0].top', 'left[0].D',
                     'left[0].E', 'left[0].F', 'left[1].top', 'left[1].D',
                     'left[1].E', 'left[1].F')
        assert self.hsm.data._log == {
            'right_enter': 1,
            'right[0].top_enter': 1,
            'right[0].A_enter': 1,
            'right[0].B_enter': 1,
            'right[0].C_enter': 1,
            'right[1].top_enter': 1,
            'right[1].A_enter': 1,
            'right[1].B_enter': 1,
            'right[1].C_enter': 1,
            'right[0].C_exit': 1,
            'right[0].B_exit': 1,
            'right[0].A_exit': 1,
            'right[0].D_enter': 1,
            'right[0].E_enter': 1,
            'right[0].F_enter': 1,
            'right[1].C_exit': 1,
            'right[1].B_exit': 1,
            'right[1].A_exit': 1,
            'right[1].D_enter': 1,
            'right[1].E_enter': 1,
            'right[1].F_enter': 1,

            'right[0].D_exit': 1,
            'right[0].E_exit': 1,
            'right[0].F_exit': 1,
            'right[0].top_exit': 1,
            'right[1].D_exit': 1,
            'right[1].E_exit': 1,
            'right[1].F_exit': 1,
            'right[1].top_exit': 1,
            'right_exit': 1,
            'top_exit': 1,
            'top_enter': 2,
            'left_enter': 1,
            'left[0].top_enter': 1,
            'left[0].D_enter': 1,
            'left[0].E_enter': 1,
            'left[0].F_enter': 1,
            'left[1].top_enter': 1,
            'left[1].D_enter': 1,
            'left[1].E_enter': 1,
            'left[1].F_enter': 1,
        }
