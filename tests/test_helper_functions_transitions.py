import pytest
from hsmpy import HSM, _get_transition_sequence, _get_internal_actions
from predefined_machines import make_miro_machine
from predefined_machines import A, B, C, D, E, F, G, H, I, TERMINATE


class MockHSM(object):
    def __init__(self):
        class Dump(object):
            pass
        self.data = Dump()

_ = 'ignored'  # where used, it means the value is not important

transitions_params = [
    ('s11', D, False, True
     ['s11-exit', 's1-exit'],
     ['s-initial', 's1-entry', 's11-entry']),

    ('s11', D, True, False,
     ['s11-exit'],
     ['s1-initial', 's11-entry']),

    ('s11', TERMINATE, _, _,
     ['s11-exit', 's1-exit', 's-exit'],
     ['final-entry']),

    ('s11', A, _, _,
     ['s11-exit', 's1-exit'],
     ['s1-entry', 's1-initial', 's11-entry']),

    ('top', 'initial', _, False,
     ['top-initial', 's-entry', 's2-entry', 's2-initial', 's21-entry',
      's211-entry'],
     []),

    ('s21', H, _, _,
     [],
     []),

    ('s211', H, _, _,
     ['s211-exit', 's21-exit', 's2-exit'],
     ['s-initial', 's1-entry', 's11-entry']),

    ('s211', G, _, _,
     ['s211-exit', 's21-exit', 's2-exit'],
     ['s1-entry', 's1-initial', 's11-entry']),

    ('s211', A, _, _,
     ['s211-exit', 's21-exit'],
     ['s21-entry', 's21-initial', 's211-entry']),
]


class Test_transition_sequences(object):

    def setup_class(self):
        self.states, self.trans = make_miro_machine()
        self.hsm = HSM(self.states, self.trans)


    @pytest.mark.parametrize(('from_state', 'on_event', 'foo_before',
                              'foo_after', 'expected_exits',
                              'expected_entries'), transitions_params)
    def test_run(self, from_state, on_event, foo_before, foo_after,
                 expected_exits, expected_entries):
        mock_hsm = MockHSM()
        mock_hsm.data.foo = foo_before
        exits, entries = _get_transition_sequence(from_state, on_event,
                                                  mock_hsm)
        assert exits == expected_exits
        assert entries == expected_entries
        if foo_after != _:
            assert mock_hsm.data.foo == foo_after



internal_transitions_params = [
    ('s11', I, True,  True,  ['s1-I']),
    ('s11', I, False, False, ['s1-I']),
    ('s211', I, False, True, ['s-I']),
    ('s211', I, True, False, ['s-I']),
    ('top', I, True, True, []),
    ('top', I, False, False, []),
    ('final', I, True, True, []),
    ('final', I, False, False, []),
]


class Test_internal_transitions(object):

    def setup_class(self):
        self.states, self.trans = make_miro_machine()
        self.hsm = HSM(self.states, self.trans)


    @pytest.mark.parametrize(('from_state', 'on_event', 'foo_before',
                              'foo_after', 'expected_actions_taken'),
                             internal_transitions_params)
    def test_run(self, from_state, on_event, foo_before, foo_after,
                 expected_actions_taken):
        mock_hsm = MockHSM()
        mock_hsm.data.foo = foo_before
        actions = _get_internal_actions(from_state, on_event, mock_hsm)
        assert actions == expected_actions_taken
        assert mock_hsm.data.foo == foo_after
