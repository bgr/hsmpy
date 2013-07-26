import pytest
from hsmpy import HSM, State
from hsmpy.logic import get_responses, get_state_by_sig, tree_from_state_set
from reusable import (A, B, C, D, E, F, G, H, I, TERMINATE,
                      make_submachines_machine, make_submachines_async_machine,
                      make_miro_machine, MockHSM)


_ = 'ignored'


responding_miro_machine = [

    # guards won't be checked for these cases:
    ('s', TERMINATE, _, _, 's', 'final'),
    ('s11', TERMINATE, _, _, 's', 'final'),
    ('s211', TERMINATE, _, _, 's', 'final'),
    #('top', Initial, _, _, 'top', 's2'),
    #('s', Initial, _, _, 's', 's11'),
    #('s1', Initial, _, _, 's1', 's11'),
    #('s2', Initial, _, _, 's2', 's211'),
    #('s21', Initial, _, _, 's21', 's211'),
    ('s211', H, _, _, 's211', 's'),
    ('s211', G, _, _, 's21', 's1'),
    ('s211', C, _, _, 's2', 's1'),
    ('s11', E, _, _, 's', 's11'),
    ('s211', A, _, _, 's21', 's21'),
    ('s21', A, _, _, 's21', 's21'),
    ('s11', G, _, _, 's11', 's211'),
    ('s11', F, _, _, 's1', 's211'),
    ('s11', B, _, _, 's1', 's11'),

    # guards are relevant:
    #('top', Initial, False, False, 'top', 's2'),
    #('top', Initial, True, False, 'top', 's2'),
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
    ('s21', I, True, False, 's', None),
    ('s21', I, False, True, 's2', None),
    ('s2', I, True, False, 's', None),
    ('s2', I, False, True, 's2', None),
    ('s', I, True, False, 's', None),
    ('s', I, False, False, None, None),
    ('top', I, True, True, None, None),
    ('top', I, False, False, None, None),
    ('final', I, True, True, None, None),
    ('final', I, False, False, None, None),
]


class Test_get_response_considering_guards(object):

    def setup_class(self):
        states, trans = make_miro_machine(use_logging=True)
        self.hsm = HSM(states, trans)

    @pytest.mark.parametrize(('state_name', 'Event', 'foo_before',
                              'foo_expected', 'exp_responding_state',
                              'exp_transition_target'),
                             responding_miro_machine)
    def test_run(self, state_name, Event, foo_before, foo_expected,
                 exp_responding_state, exp_transition_target):
        mock_hsm = MockHSM()
        mock_hsm.data.foo = foo_before
        state = get_state_by_sig((state_name,), self.hsm.flattened)
        tree = tree_from_state_set(set([state]))

        resps = get_responses(tree, Event(), self.hsm.trans, mock_hsm)

        if exp_responding_state is None:
            assert resps == []
        else:
            assert len(resps) == 1  # no orthogonal regions in this HSM
            resp_subtrees, trans = zip(*resps)
            assert resp_subtrees[0][0].name == exp_responding_state
            tran = trans[0]

            if exp_transition_target is not None:
                assert State.sig_to_name(tran.target) == exp_transition_target
            else:
                assert tran.target is None

            tran.action(None, mock_hsm)  # this call might change 'foo' value
                                         # event is not relevant

        if foo_expected != 'ignored':
            assert mock_hsm.data.foo == foo_expected




############# test get_responses on machines that have submachines ############


def check(hsm, states, Event, exp_resp_states, exp_tran_targets):
    state_set = set([get_state_by_sig(sig, hsm.flattened) for sig in states])
    tree = tree_from_state_set(state_set)
    resps = get_responses(tree, Event(), hsm.trans, None)

    if exp_resp_states or exp_tran_targets:
        resp_subtrees, trans = zip(*resps)
        assert len(resp_subtrees) == len(exp_resp_states)
        resp_sigs = set([st.sig for st, _ in resp_subtrees])
        assert resp_sigs == set(exp_resp_states)

        assert len(trans) == len(exp_tran_targets)
        target_ids = set([tr.target for tr in trans])
        assert target_ids == set(exp_tran_targets)
    else:
        assert resps == []


responding_submachines_machine = [
    # element format:
    # ( [list of states machine is in], EVENT,
    #   [list of states that should respond to EVENT],
    #   [list of transition targets] )

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


class Test_get_response_submachines_machine(object):

    def setup_class(self):
        states, trans = make_submachines_machine(use_logging=False)
        self.hsm = HSM(states, trans)

    @pytest.mark.parametrize(
        ('states', 'Event', 'exp_resp_states', 'exp_tran_targets'),
        responding_submachines_machine)
    def test_run(self, states, Event, exp_resp_states, exp_tran_targets):
        check(self.hsm, states, Event, exp_resp_states, exp_tran_targets)




responding_submachines_async_machine = [
    ([('subs', 0, 'left'), ('subs', 1, 'left')], A,
     [('subs', 0, 'left')],
     [('subs', 0, 'right')]),

    ([('subs', 0, 'left'), ('subs', 1, 'left')], B,
     [('subs', 1, 'left')],
     [('subs', 1, 'right')]),
]


class Test_get_response_submachines_async_machine(object):

    def setup_class(self):
        states, trans = make_submachines_async_machine(use_logging=False)
        self.hsm = HSM(states, trans)

    @pytest.mark.parametrize(
        ('states', 'Event', 'exp_resp_states', 'exp_tran_targets'),
        responding_submachines_async_machine)
    def test_run(self, states, Event, exp_resp_states, exp_tran_targets):
        check(self.hsm, states, Event, exp_resp_states, exp_tran_targets)
