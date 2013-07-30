"""Validation functions"""

import elements as e
import logic as l


def find_duplicate_sigs(flat_state_list):
    """
        Returns list of state **sigs** that occur more than once in the given
        flattened state list.
    """
    return l.duplicates([st.sig for st in flat_state_list])


def find_nonexistent_transition_sources(flat_state_list, trans_dict):
    """
        Returns list of keys (state **instances**) found in transition map that
        don't have corresponding state in the states map.
    """
    state_names = [st.sig for st in flat_state_list]
    return [name for name in trans_dict.keys() if name not in state_names]


def find_nonexistent_transition_targets(flat_state_list, trans_dict):
    """
        Returns list of state signatures found in transition map that don't
        have corresponding state in the states map.
    """
    state_names = [st.sig for st in flat_state_list]
    return [tran.target
            for dct in trans_dict.values()  # transitions dict for state
            for tran in dct.values()  # transition in state's transitions dict
            if (not isinstance(tran, e._Internal)  # don't have targets
                and not isinstance(tran, e._Choice)  # handled separately
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
        Returns list of tuples (state_instance, string_describing_problem) for
        each problematic initial transition found.

        Initial transition is invalid if it's a self-loop, is defined as
        LocalTransition or InternalTransition, has a target which is not a
        child of the state, is a ChoiceTransition without default state, or has
        a guard.
    """
    # missing initial transition are handled separately so they're excluded
    without = find_missing_initial_transitions(flat_state_list, trans_dict)
    composites = [st for st in flat_state_list
                  if st.kind == 'composite' and st not in without]

    def report(state):
        init_tran = trans_dict[state.sig][e.Initial]
        msg = None

        get_state = lambda sig: l.get_state_by_sig(sig, flat_state_list)
        is_child = lambda sig: state in l.get_path_from_root(get_state(sig))

        if isinstance(init_tran, e._Local):
            msg = ('initial transition cannot be declared using '
                   'LocalTransition, use Choice or regular Transition')
        elif isinstance(init_tran, e._Internal):
            msg = ('initial transition cannot be declared using '
                   'InternalTransition, use Choice or regular Transition')
        elif isinstance(init_tran, e._Choice):
            if init_tran.default is None:
                msg = ('must declare default target when using '
                       'Choice as initial transition')
            elif get_state(init_tran.default) is None:
                msg = 'default points to nonexistent state'
            elif not is_child(init_tran.default):
                msg = 'default target must be a child state'
            elif any(get_state(s) is None for s in init_tran.switch.values()):
                msg = 'switch dict references nonexistent state'
            elif not all(is_child(sig) for sig in init_tran.switch.values()):
                msg = 'switch dict values must be names of child states'
        # at this point we know it is instance of regular Transition
        elif init_tran.target == st.sig:
            msg = 'initial transition cannot be a loop'
        elif get_state(init_tran.target) is None:
            msg = 'transition target points to nonexistent state'
        elif not is_child(init_tran.target):
            msg = 'target state must be a child state'
        elif init_tran.guard is not e.always_true:
            msg = 'initial transition cannot have a guard'
        return (state, msg) if msg else None

    return [report(st) for st in composites if report(st) is not None]


def find_invalid_local_transitions(flat_state_list, trans_dict):
    """
        Returns list of 3-tuples (state_sig, event, transition).
        To be valid, local transition must be must be from superstate to
        substate or vice versa (source and target must be in parent-child
        relationship), and cannot be a self-loop.
    """
    bad_sources = find_nonexistent_transition_sources(flat_state_list,
                                                      trans_dict)
    bad_targets = find_nonexistent_transition_targets(flat_state_list,
                                                      trans_dict)
    bad_state_sigs = bad_sources + bad_targets

    get_by_sig = lambda sig: l.get_state_by_sig(sig, flat_state_list)
    common_parent = lambda sig_a, sig_b: l.get_common_parent(
        get_by_sig(sig_a), get_by_sig(sig_b)).sig

    return [(st_sig, evt.__name__, tran.target)
            for st_sig, outgoing in trans_dict.items()
            for evt, tran in outgoing.items()
            if st_sig not in bad_state_sigs and
            isinstance(tran, e._Local) and (
            st_sig == tran.target or  # loop
            common_parent(st_sig, tran.target) not in [st_sig, tran.target])]


def find_invalid_choice_transitions(flat_state_list, trans_dict):
    """ Returns list of tuples (state_sig, event_name) for each malformed
        Choice transition found.

        Choice transition is invalid if default is not a valid state name, or
        if switch dict is unspecified, empty or contains value which is not a
        valid state name.
    """
    state_sigs = [st.sig for st in flat_state_list]
    choice_trans = [(tran, src_sig, evt.__name__)
                    for src_sig, dct in trans_dict.items()
                    for evt, tran in dct.items()
                    if isinstance(tran, e._Choice)]

    targets_ok = lambda tr: all(sg in state_sigs for sg in tr.switch.values())
    default_ok = lambda tr: tr.default is None or tr.default in state_sigs

    return [(src_sig, evtname) for tran, src_sig, evtname in choice_trans
            if not tran.switch  # tran switch dict empty or unspecified
            or not targets_ok(tran)  # switch dict contains invalid target
            or not default_ok(tran)]  # default target points to invalid state


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
        for parent in l.get_path_from_root(state):
            visit(parent, visited)
        # visit transition targets going out of current state
        for tran in trans_dict.get(state.sig, {}).values():
            target_state = l.get_state_by_sig(tran.target, flat_state_list)
            if target_state is not None:  # nonexistent state in trans_dict
                visit(target_state, visited)  # will be checked by another func
        return visited

    reachable = visit(top_state)
    return [st for st in flat_state_list if st not in reachable]
