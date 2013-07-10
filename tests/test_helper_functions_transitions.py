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
    ('s', TERMINATE, 's', 'final'),
    ('s11', TERMINATE, 's', 'final'),
    ('s211', TERMINATE, 's', 'final'),
    ('top', 'initial', 'top', 's2'),
    ('s', 'initial', 's', 's11'),
    ('s1', 'initial', 's1', 's11'),
    ('s2', 'initial', 's2', 's211'),
    ('s21', 'initial', 's21', 's211'),
    ('s211', H, 's211', 's'),
    ('s211', G, 's21', 's1'),
    ('s211', C, 's2', 's1'),
    ('s11', E, 's', 's11'),
    ('s211', A, 's21', 's21'),
    ('s21', A, 's21', 's21'),
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
    ('s11', D, False, True,
     ['s11-exit', 's1-exit'],
     ['s1-D', 's-init', 's1-entry', 's11-entry']),

    ('s11', D, True, False,
     ['s11-exit'],
     ['s11-D', 's1-init', 's11-entry']),

    ('s11', TERMINATE, _, _,
     ['s11-exit', 's1-exit', 's-exit'],
     ['s-TERMINATE', 'final-entry']),

    ('s11', A, _, _,
     ['s11-exit', 's1-exit'],
     ['s1-A', 's1-entry', 's1-init', 's11-entry']),

    ('top', 'initial', _, False,
     [],
     ['top-init', 's-entry', 's2-entry', 's2-init', 's21-entry',
      's211-entry']),

    ('s211', H, _, _,
     ['s211-exit', 's21-exit', 's2-exit'],
     ['s211-H', 's-init', 's1-entry', 's11-entry']),

    ('s211', G, _, _,
     ['s211-exit', 's21-exit', 's2-exit'],
     ['s21-G', 's1-entry', 's1-init', 's11-entry']),

    ('s211', A, _, _,
     ['s211-exit', 's21-exit'],
     ['s21-A', 's21-entry', 's21-init', 's211-entry']),

    ('s11', B, _, _,
     ['s11-exit'],
     ['s1-B', 's11-entry']),

    ('s211', B, _, _,
     ['s211-exit'],
     ['s21-B', 's211-entry']),

    ('s21', H, _, _,
     [],
     []),

    ('s211', NONEXISTING_EVENT, True, True,
     [],
     []),

    ('s211', NONEXISTING_EVENT, False, False,
     [],
     []),
]


class Test_transition_sequences(object):

    def setup_class(self):
        self.states, self.trans = make_miro_machine()
        self.hsm = HSM(self.states, self.trans)

    @pytest.mark.parametrize(('from_state', 'on_event', 'foo_before',
                              'foo_after', 'expected_exits',
                              'expected_entries'), exits_and_entries)
    def test_run(self, from_state, on_event, foo_before, foo_after,
                 expected_exits, expected_entries):
        mock_hsm = MockHSM()
        mock_hsm.data.foo = foo_before
        from_state = _get_state_by_name(from_state, self.hsm.flattened)
        exits, entries = _get_transition_sequence(from_state, on_event,
                                                  self.hsm.flattened,
                                                  self.trans, mock_hsm)
        exits_names = [str(act) for act in exits]
        entries_names = [str(act) for act in entries]
        print from_state, on_event
        print exits_names
        print entries_names
        assert exits_names == expected_exits
        assert entries_names == expected_entries

        # perform actions to update 'foo' value
        [exit(mock_hsm) for exit in exits]
        [enter(mock_hsm) for enter in entries]

        if foo_after != _:  # care about the value of 'foo'
            assert mock_hsm.data.foo == foo_after
