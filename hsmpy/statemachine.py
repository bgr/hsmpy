import logging

_log = logging.getLogger(__name__)


class Transition(object):
    def __init__(self, target, action=None, guard=None):
        if action is None:
            action = lambda hsm: None  # action does nothing by default
        if guard is None:
            guard = lambda hsm: True  # make guard always pass by default
        self.target = target
        self.action = action
        self.guard = guard

    def __repr__(self):
        return "{0} to '{1}'".format(self.__class__.__name__, self.target)


class LocalTransition(Transition):
    pass


class InternalTransition(Transition):
    def __init__(self, action=None, guard=None):
        super(InternalTransition, self).__init__(None, action, guard)

# TODO: maybe reintroduce LoopTransition


class State(object):
    interests = {}  # override

    def __init__(self, name='unnamed_state'):
        self.name = name
        self.states = {}  # for cleaner code, only CompositeState has substates
        self._hsm = None  # maybe not needed
        self._parent = None

    def enter(self, hsm):  # override
        pass

    def exit(self, hsm):  # override
        pass

    def __repr__(self):
        return "{0} '{1}'".format(self.__class__.__name__, self.name)

    def __getitem__(self, key):
        return self.states[key]


class CompositeState(State):
    def __init__(self, states, name='unnamed_state'):
        super(CompositeState, self).__init__(name)
        self.states = states


class Action(object):
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __call__(self, hsm):
        return self.function(hsm)

    def __repr__(self):
        return self.name


class HSM(object):
    def __init__(self, states, transitions):
        # states tree must have single state as root
        self.states = states
        self.trans = transitions
        self.data = object()
        self._log = []
        self._running = False

        self.flattened = self._traverse_and_wire_up(self.states)
        # TODO: _validate

    def _traverse_and_wire_up(self, states_dict, parent_state=None):
        traversed = []  # will contain flattened subtree of state instances
        # traverse state tree
        for key_name, state in states_dict.items():
            state._parent = parent_state  # make state know its parent state
            state.name = key_name  # make state know its name
            state._hsm = self      # make state know about its HSM
            traversed += [state]   # add state to traversed list
            traversed += self._traverse_and_wire_up(state.states, state)
        return traversed

    def start(self):
        assert not self._running
        if not self._attempt_transition('start'):
            raise RuntimeError("State machine couldn't start, "
                               "this shouldn't ever happen")
        self._running = True

    def validate(self):
        # TODO
        if not len(self.flattened) == 1:
            raise ValueError("Given state structure should have "
                             "exactly one top state")

        duplicate_names = _find_duplicate_names(self.flattened)
        if duplicate_names:
            raise ValueError("Found duplicate state "
                             "names: {0}".format(duplicate_names))

        duplicate_instances = _find_duplicates(self.flattened)
        if duplicate_instances:
            raise ValueError("Found duplicate state "
                             "instances: {0}".format(duplicate_instances))

        unreachable = _find_unreachable_states()
        if unreachable:
            raise ValueError("Found unreachable "
                             "states: {0}".format(', '.join(unreachable)))

        #if not state.states or len(state.states) == 0:
            #raise ValueError("Composite state must have substates")
        # TODO: add rest of the validation checks, move to HSM maybe



# helper functions:

def _get_children(parent_state):
    direct_children = parent_state.states.values()
    return direct_children + [ch for dir_ch in direct_children
                              for ch in _get_children(dir_ch)]


def _get_state_by_name(state_name, flat_state_list):
    found = [st for st in flat_state_list if st.name == state_name]
    if len(found) == 0:
        return None
        #raise LookupError("State with name '{0}' "
                          #"not found".format(state_name))
    if len(found) > 1:
        raise LookupError("Multiple states with name '{0}' "
                          "found".format(state_name))
    return found[0]


def _get_incoming_transitions(target_state_name, trans_dict,
                              include_loops=False):
    found = []
    for source_state_name, outgoing_trans in trans_dict.items():
        for event, tran in outgoing_trans.items():
            is_loop = (target_state_name == source_state_name)
            if (tran.target == target_state_name
                    and (include_loops or not is_loop)):
                    # this ^ will be false only when it's a loop
                    # and include_loops is False
                found += [(source_state_name, event, tran)]
    return found


def _get_path_from_root(to_state):
    if to_state._parent is None:
        return [to_state]
    return _get_path_from_root(to_state._parent) + [to_state]


def _get_path(from_state, to_state):
    # returns (states_to_exit, common_parent, states_to_enter) tuple
    from_path = _get_path_from_root(from_state)
    to_path = _get_path_from_root(to_state)
    common_path = [a for a, b in zip(from_path, to_path) if a == b]
    common_parent = common_path[-1]
    exits = list(reversed([st for st in from_path if st not in common_path]))
    entries = [st for st in to_path if st not in common_path]
    return (exits, common_parent, entries)


def _get_common_parent(state_A, state_B):
    return _get_path(state_A, state_B)[1]


def _get_response(source_state, for_event, trans_dict, hsm):
    # returns (responding_state, transition) tuple
    tran = trans_dict.get(source_state.name, {}).get(for_event)
    if tran is None:  # maybe it has internal transition defined
        tran = source_state.interests.get(for_event)
    if tran is not None:
        if tran.guard(hsm):  # only match if transition guard passes
            return (source_state, tran)
    if source_state._parent is not None:  # look up the hierarchy
        return _get_response(source_state._parent, for_event, trans_dict, hsm)
    return (None, None)


def _get_transition_sequence(source_state, for_event,
                             flat_state_list, trans_dict, hsm):
    # returns (exit_action_list, entry_action_list) tuple
    # where entry_action_list contains states and transitions

    # state that responds to event might not be the source_state
    resp_state, transition = _get_response(source_state, for_event,
                                           trans_dict, hsm)
    if resp_state is None:
        return ([], [])  # nothing to exit or enter

    target_state = _get_state_by_name(transition.target, flat_state_list)

    action_name = lambda st, descr: '{0}-{1}'.format(st.name, descr)

    exits_till_responding, _, _ = _get_path(source_state, resp_state)
    exits_from_responding, _, entries = _get_path(resp_state, target_state)

    exits = exits_till_responding + exits_from_responding

    # in case of loops add exit and reentry actions for responding state
    if resp_state is target_state:
        exits = exits + [resp_state]
        entries = [resp_state] + entries

    # wrap in Action objects
    exits = [Action(action_name(st, 'exit'), st.exit) for st in exits]
    entries = [Action(action_name(st, 'entry'), st.enter) for st in entries]

    evt_name = 'init' if for_event == 'initial' else for_event.__name__
    tran_action = Action(action_name(resp_state, evt_name), transition.action)

    # original transition action must come before any entry action
    entries = [tran_action] + entries

    # if target state is composite, follow its 'initial' transition
    # recursively and append more entry actions to entries list
    if isinstance(target_state, CompositeState):
        _, more = _get_transition_sequence(target_state, 'initial',
                                           flat_state_list, trans_dict, hsm)
        entries += more  # cannot have exits if machine is valid

    return (exits, entries)



# validation methods:

def _find_duplicates(ls):
    import collections
    return [el for el, n in collections.Counter(ls).items() if n > 1]


def _find_duplicate_names(ls):
    return _find_duplicates([st.name for st in ls])


def _find_nonexistent_transition_sources(flat_state_list, trans_dict):
    state_names = [st.name for st in flat_state_list]
    return [name for name in trans_dict.keys() if name not in state_names]


def _find_nonexistent_transition_targets(flat_state_list, trans_dict):
    state_names = [st.name for st in flat_state_list]
    return [tran.target
            for dct in trans_dict.values()  # transitions dict for state
            for tran in dct.values()  # transition in state's transitions dict
            if tran.target not in state_names]


def _find_missing_initial_transitions(flat_state_list, trans_dict):
    composites = [st for st in flat_state_list
                  if isinstance(st, CompositeState)]
    return [st for st in composites
            if (trans_dict.get(st.name) is None or
                trans_dict.get(st.name).get('initial') is None)]


def _find_invalid_initial_transitions(flat_state_list, trans_dict):
    # composite states with initial transitions that are defined as local
    # OR have target which is not a child of that state
    # TODO: OR have guards
    without = _find_missing_initial_transitions(flat_state_list, trans_dict)
    composites = [st for st in flat_state_list
                  if isinstance(st, CompositeState) and st not in without]

    is_local = lambda tran: isinstance(tran, LocalTransition)
    get_init_tran = lambda state: trans_dict[state.name]['initial']

    return [st for st in composites
            if is_local(get_init_tran(st)) or
            _get_state_by_name(get_init_tran(st).target, flat_state_list)
            not in _get_children(st)]


def _find_invalid_local_transitions(flat_state_list, trans_dict):
    # local transitions must be from superstate to substate or
    # vice versa (source and target must be in parent-child relationship).
    # they cause either exits (from substate to superstate),
    # or entries (from superstate to substate), not both.
    # also local cannot be loops
    bad_sources = _find_nonexistent_transition_sources(flat_state_list,
                                                       trans_dict)
    bad_targets = _find_nonexistent_transition_targets(flat_state_list,
                                                       trans_dict)
    bad_state_names = bad_sources + bad_targets

    get_by_name = lambda name: _get_state_by_name(name, flat_state_list)
    common_parent = lambda name_a, name_b: _get_common_parent(
        get_by_name(name_a), get_by_name(name_b)).name

    return [(st_name, evt, tran) for st_name, outgoing in trans_dict.items()
            for evt, tran in outgoing.items()
            if st_name not in bad_state_names and
            isinstance(tran, LocalTransition) and (
            st_name == tran.target or  # loop
            common_parent(st_name, tran.target) not in [st_name, tran.target])]


def _find_unreachable_states(top_state, flat_state_list, trans_dict):
    # check if state can be reached by recursively following
    # all transitions going out from top state
    def visit(state, visited=set()):  # instantiating should be ok in this case
        if state in visited:
            return set()
        visited.add(state)
        # all state's parents are reachable
        # visit transition targets going out of every parent state
        for parent in _get_path_from_root(state):
            visited.update(visit(parent, visited))
        # visit transition targets going out of current state
        for tran in trans_dict.get(state.name, {}).values():
            target_state = _get_state_by_name(tran.target, flat_state_list)
            if target_state is not None:  # nonexistent state in trans_dict
                visited.update(visit(target_state, visited))
        return visited

    reachable = visit(top_state)
    return [st for st in flat_state_list if st not in reachable]



# old deprecated code below

class StateMachine(object):
    def __init__(self, transition_map, initial_state, eventbus):
        assert initial_state in transition_map.keys()
        self._eb = eventbus
        self._running = False
        self._tmap = transition_map.copy()
        null_state = None  # NullState()
        self._tmap.update({
            null_state: [ Transition('start', initial_state) ]
        })
        self._state = null_state
        self._register_listeners(self._state)

    def can_transition(self, event):
        return event in [tr.triggering_event for tr in self._tmap[self._state]]

    def _unregister_listeners(self, for_state):
        _log.debug("unregistering {0} currently registered transition "
                   "listeners".format(len(self._tmap[for_state])))
        # unregister currently registered transition listeners
        for tr in self._tmap[for_state]:
            _log.debug('    {0} - {1}'.format(tr.triggering_event, tr))
            self._eb.unregister(tr.triggering_event, self._attempt_transition)

        _log.debug("unregistering {0} events old state was "
                   "interested in ".format(len(for_state.interests)))
        # unregister the old state from the events it was interested in
        for evt, func in for_state.interests.items():
            _log.debug('    {0}'.format(evt))
            self._eb.unregister(evt, func)

    def _register_listeners(self, for_state):
        _log.debug("registering {0} new transition's "
                   "listeners".format(len(self._tmap[for_state])))
        # register new transitions
        for tr in self._tmap[for_state]:
            _log.debug('    {0}'.format(tr.triggering_event))
            self._eb.register(tr.triggering_event, self._attempt_transition)

        _log.debug("registering {0} events new state is "
                   "interested in ".format(len(for_state.interests)))
        # register all listeners that new state's is interested in
        for evt, func in for_state.interests.items():
            _log.debug('    {0}'.format(evt))
            self._eb.register(evt, func)

    def _attempt_transition(self, event, aux=None):
        assert event is not None

        found_trans = [tr for tr in self._tmap[self._state]
                       if tr.triggering_event == event]
        assert len(found_trans) == 1, "must have one transition per event"

        tran = found_trans[0]
        _log.debug("found transition for event '{0}': {1}".format(event, tran))

        if not tran.condition():
            _log.debug("transition cancelled due to unfulfilled condition")
            return False

        _log.debug("exiting current state '{0}'".format(self.current_state))
        self._state.exit()

        self._unregister_listeners(self._state)

        _log.debug("executing transition's on_transition()")
        # execute transition handler and set current state to new state
        tran.on_transition()
        self._state = tran.to_state

        self._register_listeners(self._state)

        _log.debug("entering new state '{0}'".format(self.current_state))
        self._state.enter()
        return True

    def start(self):
        assert not self._running
        if not self._attempt_transition('start'):
            raise RuntimeError("State machine couldn't start, "
                               "this shouldn't ever happen")
        self._running = True

    @property
    def current_state(self):
        return self._state.__class__.__name__
