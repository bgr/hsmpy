import pytest
from hsmpy.logic import (get_state_by_sig,
                         get_incoming_transitions,
                         duplicates)
from hsmpy.validation import (find_duplicate_sigs,
                              find_nonexistent_transition_sources,
                              find_nonexistent_transition_targets,
                              find_missing_initial_transitions,
                              find_invalid_initial_transitions,
                              find_invalid_local_transitions,
                              find_invalid_choice_transitions,
                              find_unreachable_states)
from hsmpy import State, HSM, T, Initial, Internal, Local, Choice
from reusable import A, B, C


class Test_find_duplicate_state_names:

    def test_empty(self):
        assert duplicates(None) == []
        assert duplicates([]) == []

    def test_no_duplicates(self):
        assert duplicates([1]) == []
        assert duplicates([1, 2, 3, 4]) == []

    def test_one_duplicate(self):
        assert duplicates([1, 1]) == [1]
        assert duplicates([1, 1, 2]) == [1]
        assert duplicates([1, 2, 1]) == [1]
        assert duplicates([2, 1, 1]) == [1]
        assert duplicates(list('abCdefgChi')) == ['C']

    def test_multiple_duplicates(self):
        dups = duplicates(list('abC_dEfgCh_iEjE__k'))
        assert sorted(dups) == sorted(['C', 'E', '_'])

    def test_duplicate_state_names(self):
        states = {
            'top': State({
                'left': State({
                    'left_A': State(),
                    'right': State(),
                    'left_B': State(),
                    'left': State(),
                }),
                'right': State({
                    'right_A': State(),
                    'right_B': State(),
                    'left': State(),
                }),
            }),
            'left_B': State(),
        }
        hsm = HSM(states, {}, skip_validation=True)
        # extract name from tuple
        dups = [name[-1] for name in find_duplicate_sigs(hsm.flattened)]
        assert sorted(dups) == sorted(['left', 'right', 'left_B'])



class Test_invalid_transitions:
    def test_Choice_raises_on_empty_switch_dict(self):
        with pytest.raises(ValueError):
            Choice({})

    def test_Choice_raises_on_switch_not_dict(self):
        with pytest.raises(TypeError):
            Choice([])

    def test_Internal_raises_when_no_target_specified(self):
        with pytest.raises(TypeError):
            Internal()



class Test_structural_analysis:

    def setup_class(self):
        states = {
            'top': State({  # bad initial transition (local)
                'left': State({  # no initial transition
                    'left_A': State(),
                    'left_B': State(),
                    'bad': State({ 'bad1': State() }),  # unreachable; missing
                                                        # initial transition
                }),
                'middle': State({  # bad initial transition (outside)
                    'mid_A': State(),       # both unreachable
                }),
                'ortho_unreachable': State([  # unreachable
                    ({ 'subunr1': State(), }, {} ),  # unreachable since
                    ({ 'subunr2': State(), }, {} ),  # parent is unreachable
                ]),
                'ortho': State([  # reachable (transition points to it)
                    ({ 'sub1': State(), }, {} ),  # reachable automaticlly
                    ({ 'sub2': State({ 'unr': State() }), }, {} ),  # unreach.
                ]),
                'right': State({  # bad initial transition (loop)
                    'right_A': State({  # unreachable since source is also unr.
                        'choice_test_1': State({  # ditto
                            'choice_placeholder_1': State(),  # ditto
                        }),
                    }),
                    'right_B': State({  # unreachable; only has self loop
                        'choice_placeholder_2': State(),  # also unreachable
                    }),
                }),
            })
        }

        trans = {
            'top': {
                Initial: Local('left_B'),  # initial trans cannot be local
                C: Local('ortho')
            },
            'left': {  # no initial transition
                A: T('right'),
                B: T('left'),  # loop
            },
            'right': {
                A: Local('left_A'),  # invalid (target not local)
                B: Local('right'),  # invalid loop (loop cannot be local)
                C: T('bad_target_1'),
                Initial: T('right'),  # inital transition cannot be loop
            },
            'middle': {
                Initial: T('top'),  # initial transition cannot go outside
                A: T('right_A'),  # this shouldn't make right_A reachable
            },
            'bad_source_1': {  # nonexistent source
                A: Local('bad_target_2'),  # invalid, but omitted in check
                                           # since source state doesn't exist
            },
            'bad_source_2': {  # also
                A: Local('left'),
            },
            'left_A': {
                A: T('left_A'),  # loop, ok
                B: T('left'),
            },
            'left_B': {
                A: Local('left_A')  # invalid (not a parent-child relationship)
            },
            'right_A': {
                Initial: Choice({ 2: 'left_A' }),  # no default target for init
                A: Choice({ 2: 'left_A', 3: 'bad_target_3', },  # nonx target
                          default='bad_target_4',  # nonexistent target
                          key=lambda evt, hsm: evt.data),
                B: Local('top'),
            },
            'right_B': {
                A: T('right_B'),  # loop, ok
                Initial: Choice({ 2: 'left_A' },
                                default='left_B'),  # target not a child
            },
            'choice_test_1': {
                Initial: Choice({ 2: 'left_A' },
                                default='bad_choice'),  # nonexistent target
                A: T('left'),
                B: T('right'),
            },
            'choice_placeholder_1': {
                A: Choice({ 2: 'bad_target' }),
                B: Choice({ 2: 'choice_test_1' }, default='bad_target'),
            }
        }
        self.hsm = HSM(states, trans, skip_validation=True)


    def test_get_state_by_sig(self):
        f = lambda nice: get_state_by_sig((nice,), self.hsm.flattened)
        assert f('top').name == 'top'
        assert f('left').name == 'left'
        assert f('mid_A').name == 'mid_A'
        assert f('right_B').name == 'right_B'

    def test_get_state_by_sig_in_orthogonal(self):
        f = lambda tup: get_state_by_sig(tup, self.hsm.flattened)
        assert f(('ortho',)).sig == ('ortho',)
        assert f(('ortho', 0, 'sub1')).sig == ('ortho', 0, 'sub1')
        assert f(('ortho', 1, 'sub2')).sig == ('ortho', 1, 'sub2')


    def test_get_incoming_trans(self):
        # exclude Transition objects from result tuples for cleaner checks
        def f(name, include_loops):
            res = [(src[-1], evt) for src, evt, _tran
                   in get_incoming_transitions((name,), self.hsm.trans,
                                               include_loops)]
            return sorted(res)

        assert f('top', False) == sorted([
            ('right_A', B),
            ('middle', Initial)])

        assert f('top', True) == sorted([
            ('right_A', B),
            ('middle', Initial)])

        assert f('left', False) == sorted([
            ('choice_test_1', A),
            ('bad_source_2', A),
            ('left_A', B)])

        assert f('left', True) == sorted([
            ('choice_test_1', A),
            ('bad_source_2', A),
            ('left_A', B),
            ('left', B)])

        # some of these below come from Choice transitions
        assert f('left_A', True) == sorted([
            ('left_A', A),  # self-loop
            ('right', A),
            ('left_B', A),  # tran is invalid but this function doesn't care
            ('right_B', Initial),
            ('choice_test_1', Initial),
            ('right_A', A),
            ('right_A', Initial)])

        assert f('left_B', True) == sorted([
            ('right_B', Initial),
            ('top', Initial) ])

        assert f('right_B', False) == []
        assert f('right_B', True) == [('right_B', A)]


    def test_find_nonexistent_transition_sources(self):
        t = find_nonexistent_transition_sources(self.hsm.flattened,
                                                self.hsm.trans)
        assert sorted(t) == sorted([('bad_source_1',), ('bad_source_2',)])


    def test_find_nonexistent_transition_targets(self):
        t = find_nonexistent_transition_targets(self.hsm.flattened,
                                                self.hsm.trans)
        assert sorted(t) == sorted([('bad_target_1',), ('bad_target_2',)])


    def test_find_missing_initial_transitions(self):
        func = find_missing_initial_transitions
        names = [s.name for s in func(self.hsm.flattened, self.hsm.trans)]
        assert sorted(names) == sorted(['left', 'bad', 'ortho[1].sub2'])


    def test_find_invalid_initial_transitions(self):
        func = find_invalid_initial_transitions
        names = [s.name for s, _ in func(self.hsm.flattened, self.hsm.trans)]
        assert sorted(names) == sorted(['top', 'middle', 'right', 'right_A',
                                        'right_B', 'choice_test_1'])


    def test_find_invalid_local_transitions(self):
        res_tuples = [(src[-1], evt, tran[-1]) for src, evt, tran
                      in find_invalid_local_transitions(self.hsm.flattened,
                                                        self.hsm.trans)]
        assert sorted(res_tuples) == sorted([
            ('left_B', A, 'left_A'),
            ('right', A, 'left_A'),
            ('right', B, 'right'),
        ])


    def test_find_invalid_choice_transitions(self):
        func = find_invalid_choice_transitions
        res = sorted((State.sig_to_name(sig), evt)
                     for sig, evt in func(self.hsm.flattened, self.hsm.trans))
        assert sorted(res) == sorted([
            ('choice_placeholder_1', A),
            ('choice_placeholder_1', B),
            ('right_A', A),
            ('choice_test_1', Initial),
            #('right_A', Initial),  # these two are valid Choices, but not
            #('right_B', Initial),  # valid initial transitions
        ])


    def test_find_unreachable_states(self):
        names = [st.name  # first element of tuple
                 for st in find_unreachable_states(self.hsm.root,
                                                   self.hsm.flattened,
                                                   self.hsm.trans)]
        expected = ['middle', 'mid_A', 'right_A', 'right_B', 'bad', 'bad1',
                    'ortho_unreachable', 'ortho_unreachable[0].subunr1',
                    'ortho_unreachable[1].subunr2', 'ortho[1].unr',
                    'choice_test_1', 'choice_placeholder_1',
                    'choice_placeholder_2']
        assert sorted(names) == sorted(expected)
