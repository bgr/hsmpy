import pytest
from hsmpy import HSM, Event
from hsmpy.statemachine import (_get_transition_sequence, _get_response,
                                _get_state_by_name)
from predefined_machines import make_miro_machine
from predefined_machines import A, B, C, D, E, F, G, H, I, TERMINATE


class MockHSM(object):
    def __init__(self):
        class Dump(object):
            pass
        self.data = Dump()


class NONEXISTING_EVENT(Event):
    pass


responding_reguardless = [
    ('top', TERMINATE, 'top', 'final'),
    ('s', TERMINATE, 'top', 'final'),
    ('s11', TERMINATE, 'top', 'final'),
    ('s211', TERMINATE, 'top', 'final'),
    ('s', 'initial', 's', 's11'),
    ('s1', 'initial', 's1', 's11'),
    ('s2', 'initial', 's2', 's211'),
    ('s21', 'initial', 's21', 's211'),
    ('s211', H, 's211', 's'),
    ('s211', G, 's21', 's1'),
    ('s211', C, 's2', 's1'),
    ('s11', E, 's', 's11'),
    ('s211', A, 's21', 's21'),
    ('s11', G, 's11', 's211'),
    ('s11', F, 's1', 's211'),
    ('s11', B, 's1', 's11'),
]


class Test_get_response_guards_irrelevant(object):

    def setup_class(self):
        self.states, self.trans = make_miro_machine()
        self.hsm = HSM(self.states, self.trans)

    @pytest.mark.parametrize(('from_state', 'on_event',
                              'expected_responding_state',
                              'expected_transition_target'),
                             responding_reguardless)
    def test_run(self, from_state, on_event, expected_responding_state,
                 expected_transition_target):
        mock_hsm = MockHSM()
        from_state = _get_state_by_name(from_state, self.hsm.flattened)

        resp_state, tran = _get_response(from_state, on_event, self.trans,
                                         mock_hsm)

        assert resp_state.name == expected_responding_state
        assert tran.target == expected_transition_target



responding_considering_guards = [
    ('top', 'initial', False, False, 'top', 's2'),
    ('top', 'initial', True, False, 'top', 's2'),
    ('s11', D, True, False, 's11', 's1'),
    ('s11', D, False, True, 's1', 's'),
    ('s1', D, False, True, 's1', 's'),
    ('s1', D, True, True, None, None),
    ('s21', D, True, True, None, None),
    ('s21', D, False, False, None, None),
    ('top', D, True, True, None, None),
    ('top', D, False, False, None, None),
    ('s11', I, True,  True, 's1', None),
    ('s11', I, False, False, 's1', None),
    ('s1', I, True,  True, 's1', None),
    ('s1', I, False, False, 's1', None),
    ('s211', I, True, False, 's', None),
    ('s211', I, False, True, 's2', None),
    ('top', I, True, True, None, None),
    ('top', I, False, False, None, None),
    ('final', I, True, True, None, None),
    ('final', I, False, False, None, None),
]


class Test_get_response_considering_guards(object):

    def setup_class(self):
        self.states, self.trans = make_miro_machine()
        self.hsm = HSM(self.states, self.trans)

    @pytest.mark.parametrize(('from_state', 'on_event', 'foo_before',
                              'foo_expected', 'expected_responding_state',
                              'expected_transition_target'),
                             responding_considering_guards)
    def test_run(self, from_state, on_event, foo_before, foo_expected,
                 expected_responding_state, expected_transition_target):
        mock_hsm = MockHSM()
        mock_hsm.data.foo = foo_before
        from_state = _get_state_by_name(from_state, self.hsm.flattened)

        resp_state, tran = _get_response(from_state, on_event,
                                         self.trans, mock_hsm)

        if expected_responding_state is None:
            assert resp_state is None
            assert tran is None  # if no state responds tran must be None
        else:
            assert resp_state.name == expected_responding_state
            assert tran.target is expected_transition_target
            tran.action(mock_hsm)  # this call might change the value of 'foo'

        assert mock_hsm.data.foo == foo_expected



_ = 'ignored'  # where used, it means the value is not important

exits_and_entries = [
    ('s11', D, False, True, True,
     ['s11', 's1'],
     ['s1', 's11']),

    ('s11', D, True, False, True,
     ['s11'],
     ['s11']),

    ('s11', TERMINATE, _, _, True,
     ['s11', 's1', 's'],
     ['final']),

    ('s11', A, _, _, True,
     ['s11', 's1'],
     ['s1', 's11']),

    ('top', 'initial', _, False, True,
     [],
     ['s', 's2', 's21', 's211']),

    ('s211', H, _, _, True,
     ['s211', 's21', 's2'],
     ['s1', 's11']),

    ('s211', G, _, _, True,
     ['s211', 's21', 's2'],
     ['s1', 's11']),

    ('s211', A, _, _, True,
     ['s211', 's21'],
     ['s21', 's211']),

    ('s11', B, _, _, True,
     ['s11'],
     ['s11']),

    ('s21', H, _, _, False,
     [],
     []),

    ('s211', NONEXISTING_EVENT, True, True, False,
     [],
     []),

    ('s211', NONEXISTING_EVENT, False, False, False,
     [],
     []),
]


class Test_transition_sequences(object):

    def setup_class(self):
        self.states, self.trans = make_miro_machine()
        self.hsm = HSM(self.states, self.trans)


    @pytest.mark.parametrize(('from_state', 'on_event', 'foo_before',
                              'foo_after', 'has_action', 'expected_exits',
                              'expected_entries'), exits_and_entries)
    def test_run(self, from_state, on_event, foo_before, foo_after,
                 has_action, expected_exits, expected_entries):
        mock_hsm = MockHSM()
        mock_hsm.data.foo = foo_before
        exits, entries, action = _get_transition_sequence(from_state, on_event,
                                                          self.states,
                                                          self.trans, mock_hsm)
        exits = [st.name for st in exits]
        entries = [st.name for st in entries]
        assert exits == expected_exits
        assert entries == expected_entries

        if has_action:
            assert action is not None
            action(mock_hsm)

        if foo_after != _:
            assert mock_hsm.data.foo == foo_after
