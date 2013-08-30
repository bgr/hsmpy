from hsmpy import HSM, EventBus, Initial
from reusable import (A, B, TERMINATE, make_submachines_machine,
                      make_submachines_async_machine, make_choice_machine,
                      LoggingState, LoggingChoice, LoggingT)


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
        assert self.hsm.data._log == [
            'top-entry',
            'top-Initial',
            'left-entry',
            'left[0].top-entry',
            'left[0].top-Initial',
            'left[0].start-entry',
        ]
        assert_names(self.hsm, 'left[0].start', 'left[0].top', 'left', 'top')

    def test_event_A_captured_by_left_submachine(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        assert self.hsm.data._log == [
            'left[0].start-exit',
            'left[0].start-A',
            'left[0].right-entry',
        ]
        assert_names(self.hsm, 'left[0].right', 'left[0].top', 'left', 'top')

    def test_terminate_left_submachine(self):
        self.hsm.data._log = []
        self.eb.dispatch(TERMINATE())
        assert self.hsm.data._log == [
            'left[0].right-exit',
            'left[0].top-TERMINATE',
            'left[0].final-entry',
        ]
        assert_names(self.hsm, 'left[0].final', 'left[0].top', 'left', 'top')

    def test_event_A_transitions_to_right(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        assert self.hsm.data._log == [
            'left[0].final-exit',
            'left[0].top-exit',
            'left-exit',
            'left-A',
            'right-entry',
            'right-Initial',
            'subs-entry',
            'subs[0].top-entry',
            'subs[0].top-Initial',
            'subs[0].start-entry',
            'subs[1].top-entry',
            'subs[1].top-Initial',
            'subs[1].start-entry',
        ]
        assert_names(self.hsm, 'subs[0].start', 'subs[0].top', 'subs',
                     'subs[1].start', 'subs[1].top', 'subs', 'right',
                     'top')

    def test_event_A_captured_by_right_submachines(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        # TODO: investigate if this order should be strictly (all submachine
        # exits, all submachine transitions, all submachine entries)
        a = ['subs[0].start-exit', 'subs[0].start-A', 'subs[0].right-entry']
        b = ['subs[1].start-exit', 'subs[1].start-A', 'subs[1].right-entry']
        assert self.hsm.data._log in [a + b,  b + a]
        assert_names(self.hsm, 'subs[0].right', 'subs[0].top', 'subs',
                     'subs[1].right', 'subs[1].top', 'subs', 'right',
                     'top')

    def test_event_A_captured_by_right_submachines_again(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        a = ['subs[0].right-exit', 'subs[0].right-A', 'subs[0].start-entry']
        b = ['subs[1].right-exit', 'subs[1].right-A', 'subs[1].start-entry']
        assert self.hsm.data._log in [a + b,  b + a]
        assert_names(self.hsm, 'subs[0].start', 'subs[0].top', 'subs',
                     'subs[1].start', 'subs[1].top', 'subs', 'right',
                     'top')

    def test_terminate_right_submachine(self):
        self.hsm.data._log = []
        self.eb.dispatch(TERMINATE())
        a = ['subs[0].start-exit', 'subs[0].top-TERMINATE',
             'subs[0].final-entry']
        b = ['subs[1].start-exit', 'subs[1].top-TERMINATE',
             'subs[1].final-entry']
        assert self.hsm.data._log in [a + b,  b + a]
        assert_names(self.hsm, 'subs[0].final', 'subs[0].top', 'subs',
                     'subs[1].final', 'subs[1].top', 'subs', 'right',
                     'top')

    def test_event_A_transitions_to_dumb(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        a = ['subs[0].final-exit', 'subs[0].top-exit']
        b = ['subs[1].final-exit', 'subs[1].top-exit']
        c = ['subs-exit', 'subs-A', 'dumb-entry']
        assert self.hsm.data._log in [a + b + c,  b + a + c]
        assert_names(self.hsm, 'dumb', 'right', 'top')

    def test_event_A_transitions_to_left_again(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        assert self.hsm.data._log == [
            'dumb-exit',
            'right-exit',
            'right-A',
            'left-entry',
            'left[0].top-entry',
            'left[0].top-Initial',
            'left[0].start-entry',
        ]
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
        a = ['top-entry', 'top-Initial', 'subs-entry']
        b = ['subs[0].top-entry', 'subs[0].top-Initial', 'subs[0].left-entry']
        c = ['subs[1].top-entry', 'subs[1].top-Initial', 'subs[1].left-entry']
        assert self.hsm.data._log in [a + b + c,  a + c + b]
        assert_names(self.hsm, 'subs[0].left', 'subs[0].top', 'subs[1].left',
                     'subs[1].top', 'subs', 'top')

    def test_first_responds_to_A(self):
        self.hsm.data._log = []
        self.eb.dispatch(A())
        assert self.hsm.data._log == [
            'subs[0].left-exit',
            'subs[0].left-A',
            'subs[0].right-entry',
        ]
        assert_names(self.hsm, 'subs[0].right', 'subs[0].top', 'subs[1].left',
                     'subs[1].top', 'subs', 'top')

    def test_second_responds_to_B(self):
        self.hsm.data._log = []
        self.eb.dispatch(B())
        assert self.hsm.data._log == [
            'subs[1].left-exit',
            'subs[1].left-B',
            'subs[1].right-entry',
        ]
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
                Initial: LoggingChoice({ 0: 'left', 1: 'right' },
                                       key=key, default='left'),
                B: LoggingT('top'),
            },
        }

        self.eb = EventBus()
        self.hsm = HSM(states, trans)

    def test_start_in_right_C_foo_3(self):
        self.hsm.data._log = []
        self.hsm.data.foo = 3
        self.hsm.start(self.eb)
        assert_names(self.hsm, 'top', 'right', 'right[0].top', 'right[0].A',
                     'right[0].B', 'right[0].C', 'right[1].top', 'right[1].A',
                     'right[1].B', 'right[1].C')
        a = ['top-entry', 'top-Initial', 'right-entry']
        b = ['right[0].top-entry', 'right[0].top-Initial', 'right[0].A-entry',
             'right[0].B-entry', 'right[0].C-entry']
        c = ['right[1].top-entry', 'right[1].top-Initial', 'right[1].A-entry',
             'right[1].B-entry', 'right[1].C-entry']
        assert self.hsm.data._log in [a + b + c,  a + c + b]

    def test_in_right_F_dispatch_A_5(self):
        self.hsm.data._log = []
        self.eb.dispatch(A(5))
        assert_names(self.hsm, 'top', 'right', 'right[0].top', 'right[0].D',
                     'right[0].E', 'right[0].F', 'right[1].top', 'right[1].D',
                     'right[1].E', 'right[1].F')

        a = ['right[0].C-exit', 'right[0].B-exit', 'right[0].A-exit',
             'right[0].C-A', 'right[0].D-entry', 'right[0].E-entry',
             'right[0].E-Initial', 'right[0].F-entry']
        b = ['right[1].C-exit', 'right[1].B-exit', 'right[1].A-exit',
             'right[1].C-A', 'right[1].D-entry', 'right[1].E-entry',
             'right[1].E-Initial', 'right[1].F-entry']
        assert self.hsm.data._log in [a + b,  b + a]

    def test_in_left_F_dispatch_B_foo_4(self):
        self.hsm.data._log = []
        self.hsm.data.foo = 4
        self.eb.dispatch(B())
        assert_names(self.hsm, 'top', 'left', 'left[0].top', 'left[0].D',
                     'left[0].E', 'left[0].F', 'left[1].top', 'left[1].D',
                     'left[1].E', 'left[1].F')
        a = ['right[0].F-exit', 'right[0].E-exit', 'right[0].D-exit',
             'right[0].top-exit']
        b = ['right[1].F-exit', 'right[1].E-exit', 'right[1].D-exit',
             'right[1].top-exit']

        c = ['right-exit', 'top-exit', 'top-B', 'top-entry', 'top-Initial',
             'left-entry']

        d = ['left[0].top-entry', 'left[0].top-Initial', 'left[0].D-entry',
             'left[0].D-Initial', 'left[0].E-entry', 'left[0].F-entry']
        e = ['left[1].top-entry', 'left[1].top-Initial', 'left[1].D-entry',
             'left[1].D-Initial', 'left[1].E-entry', 'left[1].F-entry']
        assert self.hsm.data._log in [a + b + c + d + e,  b + a + c + d + e,
                                      a + b + c + e + d,  b + a + c + e + d]
