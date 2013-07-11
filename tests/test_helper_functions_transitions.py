import pytest
from hsmpy import HSM, Event
from hsmpy.statemachine import (_get_transition_sequence, _get_response,
                                _get_state_by_name)
from predefined_machines import make_miro_machine, make_nested_machine
from predefined_machines import (A, B, C, D, E, F, G, H, I, TERMINATE, AB_ex,
                                 AC_ex, BC_ex, AB_loc, AC_loc, BC_loc, BA_ex,
                                 CA_ex, CB_ex, BA_loc, CA_loc, CB_loc)


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

        resp_state, tran = _get_response(from_state, on_event,
                                         self.trans, mock_hsm)

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

miro_exits_and_entries = [
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

nested_exits_and_entries = [
    ('top', 'initial', _, _,
     [],
     ['top-init', 'A-entry', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    # A responding to its events
    ('A', A, _, _,
     ['A-exit'],
     ['A-A', 'A-entry', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    ('A', AB_loc, _, _,
     [],
     ['A-AB_loc', 'B-entry', 'B-init', 'C-entry']),
    ('A', AB_ex, _, _,
     ['A-exit'],
     ['A-AB_ex', 'A-entry', 'B-entry', 'B-init', 'C-entry']),

    ('A', AC_loc, _, _,
     [],
     ['A-AC_loc', 'B-entry', 'C-entry']),

    ('A', AC_ex, _, _,
     ['A-exit'],
     ['A-AC_ex', 'A-entry', 'B-entry', 'C-entry']),

    # B responding to its events
    ('B', B, _, _,
     ['B-exit'],
     ['B-B', 'B-entry', 'B-init', 'C-entry']),

    ('B', BC_loc, _, _,
     [],
     ['B-BC_loc', 'C-entry']),

    ('B', BC_ex, _, _,
     ['B-exit'],
     ['B-BC_ex', 'B-entry', 'C-entry']),

    ('B', BA_loc, _, _,
     ['B-exit'],
     ['B-BA_loc', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    ('B', BA_ex, _, _,
     ['B-exit', 'A-exit'],
     ['B-BA_ex', 'A-entry', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    # C responding to its events
    ('C', C, _, _,
     ['C-exit'],
     ['C-C', 'C-entry']),

    ('C', CA_loc, _, _,
     ['C-exit', 'B-exit'],
     ['C-CA_loc', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    ('C', CA_ex, _, _,
     ['C-exit', 'B-exit', 'A-exit'],
     ['C-CA_ex', 'A-entry', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    ('C', CB_loc, _, _,
     ['C-exit'],
     ['C-CB_loc', 'B-init', 'C-entry']),

    ('C', CB_ex, _, _,
     ['C-exit', 'B-exit'],
     ['C-CB_ex', 'B-entry', 'B-init', 'C-entry']),

    # responding to A's events while in B
    ('B', A, _, _,
     ['B-exit', 'A-exit'],
     ['A-A', 'A-entry', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    ('B', AB_loc, _, _,
     ['B-exit'],
     ['A-AB_loc', 'B-entry', 'B-init', 'C-entry']),

    ('B', AB_ex, _, _,
     ['B-exit', 'A-exit'],
     ['A-AB_ex', 'A-entry', 'B-entry', 'B-init', 'C-entry']),

    ('B', AC_loc, _, _,
     ['B-exit'],
     ['A-AC_loc', 'B-entry', 'C-entry']),

    ('B', AC_ex, _, _,
     ['B-exit', 'A-exit'],
     ['A-AC_ex', 'A-entry', 'B-entry', 'C-entry']),

    # responding to A's events while in C
    ('C', A, _, _,
     ['C-exit', 'B-exit', 'A-exit'],
     ['A-A', 'A-entry', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    ('C', AB_loc, _, _,
     ['C-exit', 'B-exit'],
     ['A-AB_loc', 'B-entry', 'B-init', 'C-entry']),

    ('C', AB_ex, _, _,
     ['C-exit', 'B-exit', 'A-exit'],
     ['A-AB_ex', 'A-entry', 'B-entry', 'B-init', 'C-entry']),

    ('C', AC_loc, _, _,
     ['C-exit', 'B-exit'],
     ['A-AC_loc', 'B-entry', 'C-entry']),

    ('C', AC_ex, _, _,
     ['C-exit', 'B-exit', 'A-exit'],
     ['A-AC_ex', 'A-entry', 'B-entry', 'C-entry']),

    # responding to B's events while in C
    ('C', B, _, _,
     ['C-exit', 'B-exit'],
     ['B-B', 'B-entry', 'B-init', 'C-entry']),

    ('C', BC_loc, _, _,
     ['C-exit'],
     ['B-BC_loc', 'C-entry']),

    ('C', BC_ex, _, _,
     ['C-exit', 'B-exit'],
     ['B-BC_ex', 'B-entry', 'C-entry']),

    ('C', BA_loc, _, _,
     ['C-exit', 'B-exit'],
     ['B-BA_loc', 'A-init', 'B-entry', 'B-init', 'C-entry']),

    ('C', BA_ex, _, _,
     ['C-exit', 'B-exit', 'A-exit'],
     ['B-BA_ex', 'A-entry', 'A-init', 'B-entry', 'B-init', 'C-entry']),
]


def prepend_machine_params(make_machine_func, list_of_tuples):
    states, trans = make_machine_func()
    hsm = HSM(states, trans)
    return [(states, trans, hsm) + tup for tup in list_of_tuples]

miro_params = prepend_machine_params(make_miro_machine,
                                     miro_exits_and_entries)

nested_params = prepend_machine_params(make_nested_machine,
                                       nested_exits_and_entries)

all_params = miro_params + nested_params


class Test_transition_sequences(object):

    @pytest.mark.parametrize(('states', 'trans', 'hsm',
                              'from_state', 'on_event', 'foo_before',
                              'foo_after', 'expected_exits',
                              'expected_entries'),
                             all_params)
    def test_run(self, states, trans, hsm, from_state, on_event, foo_before,
                 foo_after, expected_exits, expected_entries):
        mock_hsm = MockHSM()
        mock_hsm.data.foo = foo_before
        from_state = _get_state_by_name(from_state, hsm.flattened)
        exits, entries = _get_transition_sequence(from_state, on_event,
                                                  hsm.flattened, trans,
                                                  mock_hsm)
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
