import pytest
from hsmpy import HSM
from hsmpy.logic import enter, get_state_by_sig
from reusable import (make_miro_machine, make_submachines_machine,
                      make_choice_machine)


def check(hsm, root_state_name, expected_state_names, expected_log):
    root_state = get_state_by_sig((root_state_name,), hsm.flattened)
    states = enter(root_state, hsm.trans, hsm.flattened, hsm)
    state_names = [s.name for s in states]
    assert hsm.data._log == expected_log
    assert state_names == expected_state_names


@pytest.mark.parametrize(('root', 'exp_state_names', 'exp_log'), [
    ('top',
     ['top', 's', 's2', 's21', 's211'],
     ['top-entry', 'top-Initial', 's-entry', 's2-entry', 's2-Initial',
      's21-entry', 's211-entry']),

    ('s',
     ['s', 's1', 's11'],
     ['s-entry', 's-Initial', 's1-entry', 's11-entry']),

    ('s1',
     ['s1', 's11'],
     ['s1-entry', 's1-Initial', 's11-entry']),

    ('s2',
     ['s2', 's21', 's211'],
     ['s2-entry', 's2-Initial', 's21-entry', 's211-entry']),
])
def test_miro_machine(root, exp_state_names, exp_log):
    states, trans = make_miro_machine(use_logging=True)
    hsm = HSM(states, trans)
    check(hsm, root, exp_state_names, exp_log)



@pytest.mark.parametrize(('root', 'exp_state_names', 'exp_log'), [
    ('top',
     ['top', 'left', 'left[0].top', 'left[0].start'],
     ['top-entry', 'top-Initial', 'left-entry', 'left[0].top-entry',
      'left[0].top-Initial', 'left[0].start-entry']),

    ('right',
     ['right', 'subs', 'subs[0].top', 'subs[0].start', 'subs[1].top',
      'subs[1].start'],
     ['right-entry', 'right-Initial', 'subs-entry', 'subs[0].top-entry',
      'subs[0].top-Initial', 'subs[0].start-entry', 'subs[1].top-entry',
      'subs[1].top-Initial', 'subs[1].start-entry']),
])
def test_submachines_machine(root, exp_state_names, exp_log):
    states, trans = make_submachines_machine(use_logging=True)
    hsm = HSM(states, trans)
    check(hsm, root, exp_state_names, exp_log)



@pytest.mark.parametrize(('root', 'foo', 'exp_state_names', 'exp_log'), [
    ('top', 1,
     ['top', 'A', 'B', 'C'],
     ['top-entry', 'top-Initial', 'A-entry', 'A-Initial', 'B-entry',
      'C-entry']),

    ('top', 2,
     ['top', 'A', 'B', 'C'],
     ['top-entry', 'top-Initial', 'A-entry', 'B-entry', 'B-Initial',
      'C-entry']),
    ('top', 3,
     ['top', 'A', 'B', 'C'],
     ['top-entry', 'top-Initial', 'A-entry', 'B-entry', 'C-entry']),

    ('top', 'BLAH',
     ['top', 'A', 'B', 'C'],
     ['top-entry', 'top-Initial', 'A-entry', 'B-entry', 'C-entry']),

    ('top', 4,
     ['top', 'D', 'E', 'F'],
     ['top-entry', 'top-Initial', 'D-entry', 'D-Initial', 'E-entry',
      'F-entry']),

    ('top', 5,
     ['top', 'D', 'E', 'F'],
     ['top-entry', 'top-Initial', 'D-entry', 'E-entry', 'E-Initial',
      'F-entry']),

    ('top', 6,
     ['top', 'D', 'E', 'F'],
     ['top-entry', 'top-Initial', 'D-entry', 'E-entry', 'F-entry']),


    ('A', 2,
     ['A', 'B', 'C'],
     ['A-entry', 'A-Initial', 'B-entry', 'B-Initial', 'C-entry']),

    ('A', 1,
     ['A', 'B', 'C'],
     ['A-entry', 'A-Initial', 'B-entry', 'C-entry']),

    ('A', 3,
     ['A', 'B', 'C'],
     ['A-entry', 'A-Initial', 'B-entry', 'C-entry']),

    ('A', 4,
     ['A', 'B', 'C'],
     ['A-entry', 'A-Initial', 'B-entry', 'C-entry']),

    ('A', 5,
     ['A', 'B', 'C'],
     ['A-entry', 'A-Initial', 'B-entry', 'C-entry']),

    ('A', 6,
     ['A', 'B', 'C'],
     ['A-entry', 'A-Initial', 'B-entry', 'C-entry']),

    ('A', 'blah',
     ['A', 'B', 'C'],
     ['A-entry', 'A-Initial', 'B-entry', 'C-entry']),


    ('B', 3,
     ['B', 'C'],
     ['B-entry', 'B-Initial', 'C-entry']),

    ('B', 4,
     ['B', 'C'],
     ['B-entry', 'B-Initial', 'C-entry']),

    ('B', 'blah',
     ['B', 'C'],
     ['B-entry', 'B-Initial', 'C-entry']),
])
def test_choice_machine(root, foo, exp_state_names, exp_log):
    states, trans = make_choice_machine(use_logging=True)
    hsm = HSM(states, trans)
    hsm.data.foo = foo
    check(hsm, root, exp_state_names, exp_log)
