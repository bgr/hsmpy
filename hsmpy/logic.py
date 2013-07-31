"""Functions that parse, transform and query the HSM structure"""

from copy import copy
import elements as e


exit_act = lambda st: e.Action('{0}-exit'.format(st.name), st._exit, st)
entry_act  = lambda st: e.Action('{0}-entry'.format(st.name), st._enter, st)
tran_act = lambda st, evt, tran: e.Action('{0}-{1}'.format(st.name,
                                          evt.__class__.__name__),
                                          tran.action, tran)


def get_merged_sequences(state_set, event, trans_map, flat_states, hsm):
    """ Main function that performs transition from given *state_set* on given
        *event* instance. Returns tuple
            (exit_actions_list, entry_actions_list, new_state_set)
    """
    # build tree of active states from current state set,
    # propagate event through tree and get responses
    # and get exit and entry sequence for each response
    tree = tree_from_state_set(state_set)
    resps = get_responses(tree, event, trans_map, hsm)
    seqs = [get_response_sequence(resp, event, trans_map, flat_states, hsm)
            for resp in resps]

    # extract and join exit and entry Actions from lists in sequence tuples
    exit_actions = [act for seq in seqs for act in seq[0]]
    entry_actions = [act for seq in seqs for act in seq[1]]

    # filter out Actions that wrap transitions and extract states from
    # remaining Actions
    exited = set(
        act.item for act in exit_actions if isinstance(act.item, e.State))
    entered = set(
        act.item for act in entry_actions if isinstance(act.item, e.State))

    # remove exited states from current state set, and add entered states
    new_state_set = (state_set - exited) | entered

    return (exit_actions, entry_actions, new_state_set)



def join_paths(paths):
    """ Joins multiple paths with common nodes into single path (up to the
        differing node). In order to join all paths into one tree, all *paths*
        should all have a common root state.
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
    if isinstance(event, e.Initial):
        raise TypeError("You shouldn't ever dispatch Initial event")

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
            resps += [ (node_tuple, tran) ]
            continue
    return resps


def postorder(nodes):
    """ Returns flattened states of the tree gathered by post-order traversal
        of each node in *nodes*, where node is tuples (state, subnodes).
    """
    return [st for root, subnodes in nodes
            for st in postorder(subnodes) + [root]]


def get_response_sequence(response, event, trans_map, flat_states, hsm):
    """Returns tuple (exit_actions, entry_actions)."""
    (resp_state, subtree), transition = response

    transition_action = tran_act(resp_state, event, transition)

    if isinstance(transition, e._Internal):  # internal transition
        return ([], [transition_action])  # no exits, no state entries

    if isinstance(transition, e._Choice):
        key = transition.key(event, hsm)
        target_name = transition.switch.get(key) or transition.default
        # choice condition can be unfulfilled in this implementation, that's
        # not really congruent with UML's statemachines but I don't see why it
        # should be a problem - regular transitions can have guards that
        # prevent transition which has same effect
        if target_name is None:
            return ([], [transition_action])
        target_state = get_state_by_sig(target_name)
    else:
        target_state = get_state_by_sig(transition.target, flat_states)

    # follow transition - perform exits from responding state to common parent
    # and then enter states from common parent towards transition target state
    exits_till_parent, parent, entries_till_target = get_path(resp_state,
                                                              target_state)
    states_to_exit = postorder(subtree) + exits_till_parent
    states_to_enter = entries_till_target

    is_not_local = not isinstance(transition, e._Local)

    if is_not_local and parent in [resp_state, target_state]:
        states_to_exit.append(parent)
        states_to_enter.insert(0, parent)

    exits = [exit_act(st) for st in states_to_exit]
    entries = ([transition_action]
               + [entry_act(st) for st in states_to_enter]
               + entry_sequence(target_state, trans_map, flat_states, hsm)[1:])

    return (exits, entries)


def entry_sequence(state, trans_map, flat_states, hsm):
    """Returns list of Actions to be performed when entering state."""
    if state.kind == 'leaf':
        return [entry_act(state)]
    if state.kind == 'composite':
        init_tran = trans_map[state.sig][e.Initial]
        if isinstance(init_tran, e._Choice):
            key = init_tran.key(e.Initial(), hsm)
            target_name = init_tran.switch.get(key) or init_tran.default
            assert target_name is not None
            target_state = get_state_by_sig(target_name, flat_states)
        else:
            target_state = get_state_by_sig(init_tran.target, flat_states)
        # states to enter when following initial transition that points to a
        # nested state that is not immediate child. it's not done recursively
        # since it should ignore all nested initial transitions until target.
        # excluding last elem (target_state) since it'll be added recursively
        _, _, to_enter = get_path(state, target_state)
        # transition might end at another composite/orthogonal, recursively
        # create the subbranch
        subtree_entries = entry_sequence(target_state, trans_map,
                                         flat_states, hsm)
        # wrap into actions and join
        return ([entry_act(state), tran_act(state, e.Initial(), init_tran)]
                + [entry_act(st) for st in to_enter[:-1]] + subtree_entries)
    if state.kind == 'orthogonal':
        # get action sequences for each submachine and flatten them in place
        sub_acts = [act
                    for st in state.states
                    for act in entry_sequence(st, trans_map, flat_states, hsm)]
        return [entry_act(state)] + sub_acts
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
        if isinstance(tran, e._Choice):
            return (tran.default == target_state_sig or
                    any(v == target_state_sig for v in tran.switch.values()))
        return tran.target == target_state_sig

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
    prefix = prefix or ()
    if isinstance(name, str):
        return prefix + (name,)
    elif isinstance(name, tuple):
        return prefix + name
    raise ValueError("Invalid state name '{0}'".format(name))


def rename_transitions(trans_dict, prefix):
    """Renames source state sigs and outgoing transition targets"""

    def rename_targets(tran):
        """Returns new transition with prefix prepended to target state sig"""
        if isinstance(tran, e._Choice):
            if tran.default is None:
                new_default = None
            else:
                new_default = add_prefix(tran.default, prefix)
            new_switch = dict((k, add_prefix(v, prefix))
                              for k, v in tran.switch.items())
            return tran._make((new_switch, new_default, tran.key, tran.action))
        if tran.target is None:  # internal has no target
            return tran
        new_name = add_prefix(tran.target, prefix)
        return tran._make((new_name, tran.action, tran.guard))

    def rename_trans_map(trans_map):
        """Renames transition targets in evt -> tran sub-dictionary"""
        return dict((evt, rename_targets(tr)) for evt, tr in trans_map.items())

    return dict((add_prefix(src_sig, prefix), rename_trans_map(outgoing_map))
                for src_sig, outgoing_map in trans_dict.items())


def reformat(states_dict, trans_dict, prefix=None):
    """
        Renames states and transition targets.
        Extracts trans dicts from tuples that define orthogonal submachines
        and appends them all to one main trans_dict.
    """
    def fix(state_sig, val, parent_state=None):
        """Recursively rename and convert to state instance if needed"""
        if isinstance(val, e.State):
            # already defined as state
            # copy it, set name and parent, fix children states recursively
            new_state = copy(val)
            children = val.states
        else:
            new_state = e.State()
            children = val

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

    fixed = [fix(sn, val) for sn, val in states_dict.items()]

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
