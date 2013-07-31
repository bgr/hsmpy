import pytest
from hsmpy import HSM
from hsmpy.logic import (get_merged_sequences, get_state_by_sig,
                         get_path_from_root)
from reusable import (make_miro_machine, make_nested_machine, MockHSM,
                      A, B, C, D, E, F, G, H, I, TERMINATE, AB_ex, AC_ex,
                      BC_ex, AB_loc, AC_loc, BC_loc, BA_ex, CA_ex, CB_ex,
                      BA_loc, CA_loc, CB_loc)


def check(hsm, state_name, Event, foo_before, foo_expected,
          expected_leaf_state, expected_exits, expected_entries):
    mock_hsm = MockHSM()
    mock_hsm.data.foo = foo_before
    # state set and expected state set are not specified in the parameters list
    # so we'll build them on the fly - knowing the leaf states, state set is
    # path from root to that leaf state
    state_set = set(
        get_path_from_root(
            get_state_by_sig((state_name,), hsm.flattened)))
    expected_state_set = set(
        get_path_from_root(
            get_state_by_sig((expected_leaf_state,), hsm.flattened)))

    exit_actions, entry_actions, new_state_set = get_merged_sequences(
        state_set, Event(), hsm.trans, hsm.flattened, mock_hsm)

    exit_action_names = [str(act) for act in exit_actions]
    entry_action_names = [str(act) for act in entry_actions]

    assert exit_action_names == expected_exits
    assert entry_action_names == expected_entries
    assert new_state_set  == expected_state_set

    # perform actions to update 'foo' value in mock_hsm.data
    [exit_act(None, mock_hsm) for exit_act in exit_actions]
    [entry_act(None, mock_hsm) for entry_act in entry_actions]

    if foo_expected != _:  # only if we care about the value of 'foo'
        assert mock_hsm.data.foo == foo_expected



_ = 'ignored'  # where used, it means the value is not important

miro_machine_sequences = [
    ('s11', D, False, True, 's11',
     ['s11-exit', 's1-exit'],
     ['s1-D', 's-Initial', 's1-entry', 's11-entry']),

    ('s11', D, True, False, 's11',
     ['s11-exit'],
     ['s11-D', 's1-Initial', 's11-entry']),

    ('s11', TERMINATE, _, _, 'final',
     ['s11-exit', 's1-exit', 's-exit'],
     ['s-TERMINATE', 'final-entry']),

    ('s11', A, _, _, 's11',
     ['s11-exit', 's1-exit'],
     ['s1-A', 's1-entry', 's1-Initial', 's11-entry']),

    # not a valid way to handle Initial transitions
    #('top', Initial, _, False, 's211',
    # [],
    # ['top-Initial', 's-entry', 's2-entry', 's2-Initial', 's21-entry',
    #  's211-entry']),

    ('s211', H, _, _, 's11',
     ['s211-exit', 's21-exit', 's2-exit'],
     ['s211-H', 's-Initial', 's1-entry', 's11-entry']),

    ('s211', G, _, _, 's11',
     ['s211-exit', 's21-exit', 's2-exit'],
     ['s21-G', 's1-entry', 's1-Initial', 's11-entry']),

    ('s211', A, _, _, 's211',
     ['s211-exit', 's21-exit'],
     ['s21-A', 's21-entry', 's21-Initial', 's211-entry']),

    ('s11', B, _, _, 's11',
     ['s11-exit'],
     ['s1-B', 's11-entry']),

    ('s211', B, _, _, 's211',
     ['s211-exit'],
     ['s21-B', 's211-entry']),

    ('s211', E, _, _, 's11',
     ['s211-exit', 's21-exit', 's2-exit'],
     ['s-E', 's1-entry', 's11-entry']),

    ('s21', H, _, _, 's21',
     [],
     []),

    ('s211', AC_ex, True, True, 's211',  # HSM won't know about this event
     [],
     []),

    ('s211', AC_ex, False, False, 's211',
     [],
     []),

    ('top', AC_ex, False, False, 'top',
     [],
     []),
]


class Test_transition_sequences_miro_machine:

    def setup_class(self):
        states, trans = make_miro_machine(use_logging=False)
        self.hsm = HSM(states, trans)

    @pytest.mark.parametrize(('state_name', 'Event', 'foo_before',
                              'foo_expected', 'expected_leaf_state',
                              'expected_exits', 'expected_entries'),
                             miro_machine_sequences)
    def test_run(self, state_name, Event, foo_before, foo_expected,
                 expected_leaf_state, expected_exits, expected_entries):
        check(self.hsm, state_name, Event, foo_before, foo_expected,
              expected_leaf_state, expected_exits, expected_entries)






nested_machine_sequences = [
    # not a valid way to handle Initial transitions
    #('top', Initial, _, _, 'C',
    # [],
    # ['top-Initial', 'A-entry', 'A-Initial', 'B-entry', 'B-Initial',
    #  'C-entry']),

    # A responding to its events
    ('A', A, _, _, 'C',
     ['A-exit'],
     ['A-A', 'A-entry', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('A', AB_loc, _, _, 'C',
     [],
     ['A-AB_loc', 'B-entry', 'B-Initial', 'C-entry']),

    ('A', AB_ex, _, _, 'C',
     ['A-exit'],
     ['A-AB_ex', 'A-entry', 'B-entry', 'B-Initial', 'C-entry']),

    ('A', AC_loc, _, _, 'C',
     [],
     ['A-AC_loc', 'B-entry', 'C-entry']),

    ('A', AC_ex, _, _, 'C',
     ['A-exit'],
     ['A-AC_ex', 'A-entry', 'B-entry', 'C-entry']),

    # B responding to its events
    ('B', B, _, _, 'C',
     ['B-exit'],
     ['B-B', 'B-entry', 'B-Initial', 'C-entry']),

    ('B', BC_loc, _, _, 'C',
     [],
     ['B-BC_loc', 'C-entry']),

    ('B', BC_ex, _, _, 'C',
     ['B-exit'],
     ['B-BC_ex', 'B-entry', 'C-entry']),

    ('B', BA_loc, _, _, 'C',
     ['B-exit'],
     ['B-BA_loc', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('B', BA_ex, _, _, 'C',
     ['B-exit', 'A-exit'],
     ['B-BA_ex', 'A-entry', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    # C responding to its events
    ('C', C, _, _, 'C',
     ['C-exit'],
     ['C-C', 'C-entry']),

    ('C', CA_loc, _, _, 'C',
     ['C-exit', 'B-exit'],
     ['C-CA_loc', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('C', CA_ex, _, _, 'C',
     ['C-exit', 'B-exit', 'A-exit'],
     ['C-CA_ex', 'A-entry', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('C', CB_loc, _, _, 'C',
     ['C-exit'],
     ['C-CB_loc', 'B-Initial', 'C-entry']),

    ('C', CB_ex, _, _, 'C',
     ['C-exit', 'B-exit'],
     ['C-CB_ex', 'B-entry', 'B-Initial', 'C-entry']),

    # responding to A's events while in B
    ('B', A, _, _, 'C',
     ['B-exit', 'A-exit'],
     ['A-A', 'A-entry', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('B', AB_loc, _, _, 'C',
     ['B-exit'],
     ['A-AB_loc', 'B-entry', 'B-Initial', 'C-entry']),

    ('B', AB_ex, _, _, 'C',
     ['B-exit', 'A-exit'],
     ['A-AB_ex', 'A-entry', 'B-entry', 'B-Initial', 'C-entry']),

    ('B', AC_loc, _, _, 'C',
     ['B-exit'],
     ['A-AC_loc', 'B-entry', 'C-entry']),

    ('B', AC_ex, _, _, 'C',
     ['B-exit', 'A-exit'],
     ['A-AC_ex', 'A-entry', 'B-entry', 'C-entry']),

    # responding to A's events while in C
    ('C', A, _, _, 'C',
     ['C-exit', 'B-exit', 'A-exit'],
     ['A-A', 'A-entry', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('C', AB_loc, _, _, 'C',
     ['C-exit', 'B-exit'],
     ['A-AB_loc', 'B-entry', 'B-Initial', 'C-entry']),

    ('C', AB_ex, _, _, 'C',
     ['C-exit', 'B-exit', 'A-exit'],
     ['A-AB_ex', 'A-entry', 'B-entry', 'B-Initial', 'C-entry']),

    ('C', AC_loc, _, _, 'C',
     ['C-exit', 'B-exit'],
     ['A-AC_loc', 'B-entry', 'C-entry']),

    ('C', AC_ex, _, _, 'C',
     ['C-exit', 'B-exit', 'A-exit'],
     ['A-AC_ex', 'A-entry', 'B-entry', 'C-entry']),

    # responding to B's events while in C
    ('C', B, _, _, 'C',
     ['C-exit', 'B-exit'],
     ['B-B', 'B-entry', 'B-Initial', 'C-entry']),

    ('C', BC_loc, _, _, 'C',
     ['C-exit'],
     ['B-BC_loc', 'C-entry']),

    ('C', BC_ex, _, _, 'C',
     ['C-exit', 'B-exit'],
     ['B-BC_ex', 'B-entry', 'C-entry']),

    ('C', BA_loc, _, _, 'C',
     ['C-exit', 'B-exit'],
     ['B-BA_loc', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('C', BA_ex, _, _, 'C',
     ['C-exit', 'B-exit', 'A-exit'],
     ['B-BA_ex', 'A-entry', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),
]


class Test_transition_sequences_nested_machine:

    def setup_class(self):
        states, trans = make_nested_machine(use_logging=False)
        self.hsm = HSM(states, trans)

    @pytest.mark.parametrize(('state_name', 'Event', 'foo_before',
                              'foo_expected', 'expected_leaf_state',
                              'expected_exits', 'expected_entries'),
                             nested_machine_sequences)
    def test_run(self, state_name, Event, foo_before, foo_expected,
                 expected_leaf_state, expected_exits, expected_entries):
        check(self.hsm, state_name, Event, foo_before, foo_expected,
              expected_leaf_state, expected_exits, expected_entries)
