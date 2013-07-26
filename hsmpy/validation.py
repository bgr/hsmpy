"""Validation functions"""

import elements as e
import logic


def find_duplicate_sigs(flat_state_list):
    """
        Returns list of state **sigs** that occur more than once in the given
        flattened state list.
    """
    return logic.duplicates([st.sig for st in flat_state_list])


def find_nonexistent_transition_sources(flat_state_list, trans_dict):
    """
        Returns list of keys (state **instances**) found in transition map that
        don't have corresponding state in the states map.
    """
    state_names = [st.sig for st in flat_state_list]
    return [name for name in trans_dict.keys() if name not in state_names]


def find_nonexistent_transition_targets(flat_state_list, trans_dict):
    """
        Returns list of transition targets (state **names**) found in
        transition map that don't have corresponding state in the states map.
    """
    state_names = [st.sig for st in flat_state_list]
    return [tran.target
            for dct in trans_dict.values()  # transitions dict for state
            for tran in dct.values()  # transition in state's transitions dict
            if (not isinstance(tran, e._Internal)  # don't have targets
                and tran.target not in state_names)]  # no corresponding state


def find_missing_initial_transitions(flat_state_list, trans_dict):
    """
        Returns list of composite state **instances** that don't have initial
        transition defined in transitions map.
    """
    composites = [st for st in flat_state_list
                  if st.kind == 'composite']
    return [st for st in composites
            if (trans_dict.get(st.sig) is None or
                trans_dict.get(st.sig).get(e.Initial) is None)]


def find_invalid_initial_transitions(flat_state_list, trans_dict):
    """
        Returns list of composite state **instances** that have invalid initial
        transition defined.

        e.Initial transition is invalid if it's a self-loop, is defined as
        LocalTransition, has a target which is not a child of the state.
    """
    # TODO: OR have guards (implemented but untested)
    without = find_missing_initial_transitions(flat_state_list, trans_dict)
    composites = [st for st in flat_state_list
                  if st.kind == 'composite' and st not in without]

    is_local = lambda tran: isinstance(tran, e._Local)
    init_tran_of = lambda state: trans_dict[state.sig][e.Initial]
    init_tran_target_of = lambda state: logic.get_state_by_sig(
        init_tran_of(state).target, flat_state_list)

    return [st for st in composites if is_local(init_tran_of(st))
            or init_tran_of(st).target == st.sig
            or st not in logic.get_path_from_root(init_tran_target_of(st))
            or not init_tran_of(st).guard(None, None)]


def find_invalid_local_transitions(flat_state_list, trans_dict):
    """
        Returns list invalid local transitions.

        List elements are 3-tuples (state_sig, event, transition).
        To be valid, local transition must be must be from superstate to
        substate or vice versa (source and target must be in parent-child
        relationship), and cannot be a self-loop.
    """
    bad_sources = find_nonexistent_transition_sources(flat_state_list,
                                                      trans_dict)
    bad_targets = find_nonexistent_transition_targets(flat_state_list,
                                                      trans_dict)
    bad_state_sigs = bad_sources + bad_targets

    get_by_sig = lambda sig: logic.get_state_by_sig(sig, flat_state_list)
    common_parent = lambda sig_a, sig_b: logic.get_common_parent(
        get_by_sig(sig_a), get_by_sig(sig_b)).sig

    return [(st_sig, evt.__name__, tran.target)
            for st_sig, outgoing in trans_dict.items()
            for evt, tran in outgoing.items()
            if st_sig not in bad_state_sigs and
            isinstance(tran, e._Local) and (
            st_sig == tran.target or  # loop
            common_parent(st_sig, tran.target) not in [st_sig, tran.target])]


def find_unreachable_states(top_state, flat_state_list, trans_dict):
    """
        Returns list of state **instances** that are unreachable.

        It checks if state can be reached by recursively following all
        transitions going out from given state instance *top_state*. Any state
        that wasn't visited cannot be reached by any means.
    """
    def visit(state, visited=set()):  # instantiating should be ok in this case
        if state in visited:
            return set()
        visited.add(state)
        # if orthogonal is reachable, its states are automatically reachable
        if state.kind == 'orthogonal':
            [visit(st, visited) for st in state.states]
        # all state's parents are reachable
        # visit transition targets going out of every parent state
        for parent in logic.get_path_from_root(state):
            visit(parent, visited)
        # visit transition targets going out of current state
        for tran in trans_dict.get(state.sig, {}).values():
            target_state = logic.get_state_by_sig(tran.target, flat_state_list)
            if target_state is not None:  # nonexistent state in trans_dict
                visit(target_state, visited)  # will be checked by another func
        return visited

    reachable = visit(top_state)
    return [st for st in flat_state_list if st not in reachable]
