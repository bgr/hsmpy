"""Functions that parse, transform and query the HSM structure"""

import logging
_log = logging.getLogger(__name__)

from copy import copy
import elements as e



def perform_transition(state_set, event, trans_map, flat_states, hsm):
    """ Main function that performs transition from given *state_set* on given
        *event* instance. Returns set of new states HSM is in.
    """

    if isinstance(event, e.Initial):
        raise TypeError("You shouldn't ever dispatch Initial event")

    # build tree of active states from current state set,
    # propagate event through tree and get responses
    # and get exit and entry sequence for each response
    tree_root = tree_from_state_set(state_set)
    responses = get_responses(tree_root, event, trans_map, hsm)

    sequences = [perform_response(resp, event, trans_map, flat_states, hsm)
                 for resp in responses]

    # extract and merge together exit/entry actions from sequences
    exits = [st for seq in sequences for st in seq[0]]
    entries = [st for seq in sequences for st in seq[1]]


    # remove exited states from current state set, and add entered states
    new_state_set = (state_set - set(exits)) | set(entries)
    # optimization, knowing only leaf states is sufficient
    #new_state_set = set(filter(lambda s: s.kind == 'leaf', new_state_set))

    return new_state_set



def join_paths(paths):
    """ Joins paths with common subpaths from root to some node into single
        path (up to the deepest common node, from which path will branch into
        the tree). In order to join all paths into one tree, each path
        in *paths* must have same root, otherwise multiple trees will be
        returned.
    """
    nodes = {}
    # put all subpaths with common root state under same dict key
    for path in paths:
        if not path:
            continue
        state = path[0]
        if nodes.get(state) is None:
            nodes[state] = []
        tail = path[1:]
        if tail:
            nodes[state] += [tail]
    # turn each dict key-value pair into (common_state, subbranches) tuple
    return sorted([(el, join_paths(subs)) for el, subs in nodes.items()])


def tree_from_state_set(state_set):
    """ Reconstructs the tree out of states in *state_set* by joining paths
        from each state to the root.
    """
    return join_paths([get_path_from_root(st) for st in state_set])


def get_responses(tree_roots, event, trans_map, hsm):
    """ Returns list of tuples (responding_node, transition).
        *responding_node* is a tuple (state, subnodes).
    """
    resps = []
    # go all the way to the leaf states to find deepest states that respond
    for node_tuple in tree_roots:
        state, subtrees = node_tuple
        sub_resps = get_responses(subtrees, event, trans_map, hsm)
        # see if at least one subbranch responded
        if sub_resps:
            resps += sub_resps
            continue
        # maybe this state can respond since its substates didn't
        tran = trans_map.get(state.sig, {}).get(event.__class__)
        if tran and tran.guard(event, hsm):
            target = tran.get_target(event, hsm)
            if target or isinstance(tran, e.InternalTransition):
                resps += [ (node_tuple, tran) ]
    return resps


def postorder(nodes):
    """ Returns flattened states of the tree gathered by post-order traversal
        of each node in *nodes*, where node is tuples (state, subnodes).
    """
    return [st for root, subnodes in nodes
            for st in postorder(subnodes) + [root]]


def perform_response(response, event, trans_map, flat_states, hsm):
    """Returns tuple (exited_states_list, entered_states_list)."""
    (responding_state, subtree), transition = response

    if isinstance(transition, e.InternalTransition):
        # don't have to check transition's guard since it's already passed
        transition(event, hsm)
        return ([], [])  # no exits, no entries

    target_sig = transition.get_target(event, hsm)
    assert target_sig is not None, "must have target since it responded"

    target_state = get_state_by_sig(target_sig, flat_states)

    # first we should exit states from current leaf state to responding state
    exit_states = postorder(subtree)

    # then follow transition - perform exits from responding state to common
    # parent and then enter states from common parent until target state
    exits_till_parent, parent, entries_till_target = get_path(responding_state,
                                                              target_state)
    exit_states += exits_till_parent
    enter_states = entries_till_target

    is_external = not isinstance(transition, e.LocalTransition)
    # should exit and re-enter parent state if transition type is external and
    # one of the states is parent of another
    if is_external and parent in [responding_state, target_state]:
        exit_states.append(parent)
        enter_states.insert(0, parent)

    # perform state and transition actions

    for st in exit_states:
        st._do_exit(hsm)

    transition(event, hsm)

    for st in enter_states:
        st._do_enter(hsm)

    enter_states += enter(target_state, trans_map, flat_states, hsm,
                          skip_root_entry_action=True)

    return (exit_states, enter_states)


def enter(state, trans_map, flat_states, hsm, skip_root_entry_action=False):
    """ Enters the state and its substates, performing associated Initial
        transition actions along the way.
        Returns list of states entered along the way.
    """
    # TODO: make subclasses of State and have them implement this logic

    if not skip_root_entry_action:
        state._do_enter(hsm)

    event = e.Initial()

    if state.kind == 'leaf':
        return [state]
    if state.kind == 'composite':
        init_tran = trans_map[state.sig][e.Initial]
        target_sig = init_tran.get_target(event, hsm)
        target_state = get_state_by_sig(target_sig, flat_states)

        # gather more states to enter when following initial transition that
        # points to a nested state that is not immediate child. it's not done
        # recursively since it should ignore all nested initial transitions
        # until target. excluding last elem (target_state) since it'll be
        # added recursively
        _, _, to_enter = get_path(state, target_state)

        # perform transition action, initial transitions don't have guards so
        # it's safe to call it without checking guard condition
        init_tran(event, hsm)

        # perform entry actions for states until transition target state
        for st in to_enter[:-1]:
            st._do_enter(hsm)

        # enter transition target recursively, it might be composite/orthogonal
        more_entries = enter(target_state, trans_map, flat_states, hsm)
        return [state] + to_enter + more_entries
    if state.kind == 'orthogonal':
        init_tran(event, hsm)
        # enter each submachine
        return [state] + [st for substate in state.states for st in
                          enter(substate, trans_map, flat_states, hsm)]
    assert False, "this cannot happen"



def flatten(container):
    if isinstance(container, list):
        return [sub for cont_elem in container for sub in flatten(cont_elem)]
    if isinstance(container, e.State):
        return [container] + flatten(container.states)
    return [container]  # any other object


def with_rest(ls):
    """Generator - yields tuples (element, all_other_elements)"""
    for i, el in enumerate(ls):
        yield (el, ls[:i] + ls[i + 1:])


def duplicates(ls):
    """Returns list of elements that occur more than once in the given list."""
    import collections
    return [el for el, n in collections.Counter(ls).items() if n > 1]


def remove_duplicates(ls, key=lambda el: el):
    seen = set()
    add_to_seen = lambda elem: not seen.add(elem)  # always returns True
    return [elem for elem in ls
            if key(elem) not in seen and add_to_seen(key(elem))]


def get_state_by_sig(state_sig, flat_state_list):
    """
        Looks up and returns the state **instance** for given state **sig**.
    """
    found = [st for st in flat_state_list if st.sig == state_sig]
    if len(found) == 0:
        return None
        #raise LookupError("State with name '{0}' "
                          #"not found".format(state_sig))
    if len(found) > 1:
        raise LookupError("Multiple states with sig '{0}' "
                          "found".format(state_sig))
    return found[0]


def get_incoming_transitions(target_state_sig, trans_dict,
                             include_loops=False):
    """
        Returns list of incoming transitions to given state.

        Return value is list of 3-tuples, where each tuple is
        (source_state_name, triggering_event, transition).
    """
    found = []

    def targets_match(tran):
        return (tran.default == target_state_sig or
                any(v == target_state_sig for v in tran.switch.values()))

    for source_state_sig, outgoing_trans in trans_dict.items():
        for event, tran in outgoing_trans.items():
            is_loop = (target_state_sig == source_state_sig)
            if targets_match(tran) and (include_loops or not is_loop):
                # don't include if it's a loop and include_loops is False
                found += [(source_state_sig, event, tran)]
    return found


def get_path_from_root(to_state):
    """
        Returns list of state **instances** that represent the path
        from root (inclusive) to given state.
    """
    if to_state.parent is None:
        return [to_state]
    return get_path_from_root(to_state.parent) + [to_state]


def get_path(from_state, to_state):
    """
        Returns the path from given state **instance** to another.

        Return value is 3-tuple:
            (list_of_states_to_exit, common_parent, list_of_stats_to_enter).
    """
    from_path = get_path_from_root(from_state)
    to_path = get_path_from_root(to_state)
    common_path = [a for a, b in zip(from_path, to_path) if a == b]
    common_parent = common_path[-1]
    exits = list(reversed([st for st in from_path if st not in common_path]))
    entries = [st for st in to_path if st not in common_path]
    return (exits, common_parent, entries)


def get_common_parent(state_A, state_B):
    """
        Returns the common parent state **instance** for given two state
        **instances**.

        If one state is parent of the other, it'll return that state.
    """
    return get_path(state_A, state_B)[1]


def get_events(flat_state_list, trans_dict):
    """
        Returns set of all event types that machine is
        interested in listening to.
    """
    def get_subclasses(cls):
        """Returns all subclasses of class (not only direct ones)"""
        ls = cls.__subclasses__()
        return ls + [subsub for sub in ls for subsub in get_subclasses(sub)]

    events = [evt for outgoing in trans_dict.values()
              for evt in outgoing.keys() if evt != e.Initial]
    events += [sub for evt in events for sub in get_subclasses(evt)]
    return set(events)


def add_prefix(name, prefix):
    """Adds prefix to name"""
    if name is None:
        return None

    prefix = prefix or ()
    if isinstance(name, str):
        return prefix + (name,)
    elif isinstance(name, tuple):
        return prefix + name
    raise ValueError("Invalid state name '{0}'".format(name))


def rename_transitions(trans_dict, prefix):
    """Renames source state sigs and outgoing transition targets."""

    def rename_targets(tran):
        """Returns new transition with prefix prepended to target state sig"""
        tran2 = copy(tran)
        tran2.default = add_prefix(tran.default, prefix)
        tran2.switch = dict((key, add_prefix(target, prefix))
                            for key, target in tran.switch.items())
        return tran2

    def rename_trans(trans_map):
        """Renames target of every transition in trans_map sub-dictionary."""
        return dict((evt, rename_targets(tran))
                    for evt, tran in trans_map.items())

    renamed = dict((add_prefix(src_sig, prefix), rename_trans(outgoing_map))
                   for src_sig, outgoing_map in trans_dict.items())

    for src_sig, outgoing_map in renamed.items():
        for tran in outgoing_map.values():
            tran.source = src_sig

    return renamed


def reformat(states_dict, trans_dict, prefix=None):
    """
        Renames states and transition targets.
        Extracts trans dicts from tuples that define orthogonal submachines
        and appends them all to one main trans_dict.
    """
    def fix(state_sig, state_def, parent_state=None):
        """Recursively rename and convert to state instance if needed"""
        if isinstance(state_def, e.State):
            # already defined as state
            # copy it, set name and parent, fix children states recursively
            new_state = copy(state_def)
            children = state_def.states
        else:
            new_state = e.State()
            children = state_def

        new_state.sig = add_prefix(state_sig, prefix)
        new_state.parent = parent_state

        if not children:  # empty list or dict
            new_state.kind = 'leaf'
            subs, trans = ([], {})
        elif isinstance(children, list):
            new_state.kind = 'orthogonal'
            ch_prefix = lambda i: add_prefix(state_sig, prefix) + (i,)
            # get renamed states and renamed trans for every submachine
            subs, trans = zip(*[reformat(sdict, tdict, ch_prefix(i))
                                for i, (sdict, tdict) in enumerate(children)])
            # subs is tuple of lists with one element (top state of submachine
            # assumes that validation has passed), converto into list of
            # submachines
            subs = [s for ls in subs for s in ls]
            # merge all trans dicts into one dict
            trans = dict([kv for dct in trans for kv in dct.items()])
        elif isinstance(children, dict):
            new_state.kind = 'composite'
            # trans are the same, so {} for nested states
            subs, trans = reformat(children, {}, prefix)
            trans = dict(trans)
        else:
            raise ValueError("Invalid element")  # TODO: move to validation

        for sub in subs:
            sub.parent = new_state
        new_state.states = subs
        return (new_state, trans)

    fixed = [fix(st_sig, st_def) for st_sig, st_def in states_dict.items()]

    fixed_states = [st for st, _ in fixed]
    fixed_trans = dict([kv for _, dct in fixed for kv in dct.items()])
    fixed_trans.update(rename_transitions(trans_dict, prefix))
    return (fixed_states, fixed_trans)


def parse(states_dict, trans_dict):
    """
        Recursively traverses the state tree described by states_dict and
        performs the following transformations:
            * renames states (changes values of dict's keys)
            * renames transition targets
            * state instances are created from dict's values
                * if value is dict it is a state (with optional sub-states)
                * if value is list it is a state with orthogonal sub-machines
            * in case of orthogonal sub-machine state, whose elements are
              tuples (states, transitions), extracts transitions and appends
              them to main trans_dict

        Returns tuple (top_state, flattened_state_list, full_trans_dict).
    """
    renamed_states, renamed_trans = reformat(states_dict, trans_dict)
    top_state = renamed_states[0]
    flattened = flatten(renamed_states)
    return (top_state, flattened, renamed_trans)
