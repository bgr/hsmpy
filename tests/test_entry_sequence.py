from hsmpy import HSM
from hsmpy.logic import entry_sequence, get_state_by_sig
from reusable import make_miro_machine, make_submachines_machine


class Test_entry_sequence_miro_machine:

    def setup_class(self):
        states, trans = make_miro_machine(use_logging=False)
        self.hsm = HSM(states, trans)

    def test_enter_top(self):
        expected_action_names = ['top-entry', 'top-Initial', 's-entry',
                                 's2-entry', 's2-Initial', 's21-entry',
                                 's211-entry']
        seq = entry_sequence(self.hsm.root, self.hsm.trans, self.hsm.flattened)
        assert [str(act) for act in seq] == expected_action_names

    def test_enter_s(self):
        expected_action_names = ['s-entry', 's-Initial', 's1-entry',
                                 's11-entry']
        s = get_state_by_sig(('s',), self.hsm.flattened)
        seq = entry_sequence(s, self.hsm.trans, self.hsm.flattened)
        assert [str(act) for act in seq] == expected_action_names

    def test_enter_s1(self):
        expected_action_names = ['s1-entry', 's1-Initial', 's11-entry']
        s1 = get_state_by_sig(('s1',), self.hsm.flattened)
        seq = entry_sequence(s1, self.hsm.trans, self.hsm.flattened)
        assert [str(act) for act in seq] == expected_action_names

    def test_enter_s2(self):
        expected_action_names = ['s2-entry', 's2-Initial', 's21-entry',
                                 's211-entry']
        s2 = get_state_by_sig(('s2',), self.hsm.flattened)
        seq = entry_sequence(s2, self.hsm.trans, self.hsm.flattened)
        assert [str(act) for act in seq] == expected_action_names



class Test_entry_sequence_submachines_machine:

    def setup_class(self):
        states, trans = make_submachines_machine(use_logging=False)
        self.hsm = HSM(states, trans)

    def test_enter_top(self):
        expected_action_names = ['top-entry', 'top-Initial', 'left-entry',
                                 'left[0].top-entry', 'left[0].top-Initial',
                                 'left[0].start-entry']
        seq = entry_sequence(self.hsm.root, self.hsm.trans, self.hsm.flattened)
        assert [str(act) for act in seq] == expected_action_names

    def test_enter_right(self):
        expected_action_names = ['right-entry', 'right-Initial', 'subs-entry',
                                 'subs[0].top-entry', 'subs[0].top-Initial',
                                 'subs[0].start-entry', 'subs[1].top-entry',
                                 'subs[1].top-Initial', 'subs[1].start-entry']
        right = get_state_by_sig(('right',), self.hsm.flattened)
        seq = entry_sequence(right, self.hsm.trans, self.hsm.flattened)
        assert [str(act) for act in seq] == expected_action_names
