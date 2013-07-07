import logging

_log = logging.getLogger(__name__)


class Transition(object):
    def __init__(self, target, action=None, guard=None):
        if action is None:
            action = lambda: None
        if guard is None:
            guard = lambda: True
        self.target = target
        self.action = action
        self.guard = guard


class LocalTransition(Transition):
    pass


#class LoopTransition(Transition):
    #def __init__(self, action=None, guard=None):
        #super(self).__init__(None, action, guard)


class State(object):
    interests = {}  # override

    def enter(self):  # override
        pass

    def exit(self):  # override
        pass


class CompositeState(State):
    def __init__(self, states):
        self.states = states

# after bundling states and transitions by calling HSM(states, transitions)
# states will get additional properties: _hsm, name


def _traverse_and_wire_up(hsm, states_dict, parent_state=None):
    traversed = []  # will contain state instances

    # traverse state tree
    for key_name, state in states_dict.items():
        state._parent = parent_state  # used internally for traversing
        state.name = key_name  # give name to state
        state._hsm = hsm       # make state know about its HSM
        traversed += [state]   # add to traversed list
        if isinstance(state, CompositeState):
            if not state.states or len(state.states) == 0:
                raise ValueError("Composite state must have substates")
                # TODO: maybe extract this, make traversal side-effect free
            traversed += _traverse_and_wire_up(state.states, state)

    return traversed


def _find_incoming_trans(target_state_name, trans_dict, include_loops=False):
    found = []
    for source_state_name, outgoing_trans in trans_dict.values():
        for event, tran in outgoing_trans.items():
            is_loop = (target_state_name == source_state_name)
            if (tran.target == target_state_name
                    and (include_loops or not is_loop)):
                    # this ^ will be false only when it's a loop
                    # and include_loops is False
                found += [(event, tran)]
    return found


def _path_from_root(to_state):
    if to_state._parent is None:
        return [to_state]
    return _path_from_root(to_state._parent) + [to_state]


def _common_parent(state_A, state_B):
    path_A = _path_from_root(state_A)
    path_B = _path_from_root(state_B)
    common_path = [a for a, b in zip(path_A, path_B) if a == b]
    return common_path[-1]


def _find_duplicates(ls):
    import collections
    return [el for el, n in collections.Counter(ls).items() if n > 1]


def _find_transitions_with_nonexistent_targets(state_list, trans_dict):
    # TODO
    pass


def _find_invalid_local_transitions(state_list, trans_dict):
    # TODO
    # local transitions must be from superstate to substate or vice versa
    # they cause either exits (from substate to superstate),
    # or entries (from superstate to substate), not both
    # if isinstance(tran, LocalTransition) and
    #         _common_parent(source, target) not in [source, target]:
    pass


def _validate(state_list):
    if not len(state_list) == 1:
        raise ValueError("Given state structure should have "
                         "exactly one top state")

    duplicate_names = _find_duplicates(state_list)
    if duplicate_names:
        raise ValueError("Found duplicate state "
                         "names: {0}".format(duplicate_names))

    duplicate_instances = _find_duplicates([st.name for st in state_list])
    if duplicate_instances:
        raise ValueError("Found duplicate state "
                         "instances: {0}".format(duplicate_instances))

    unreachable = [st.name for st in state_list
                   if not _find_incoming_trans(st.name, include_loops=False)]
    if unreachable:
        raise ValueError("Found unreachable "
                         "states: {0}".format(', '.join(unreachable)))

    # TODO: _find_transitions_with_nonexistent_targets
    # TODO: _find_invalid_local_transitions
    # TODO: find loops and raise if loop is declared using local transition
    # TODO: make sure transitions for composite states have initial tran
    # TODO: make sure transitions for basic states don't have initial tran


class HSM(object):
    def __init__(self, states, transitions):
        # states tree must have single state as root
        self.states = states
        self.trans = transitions
        self.data = object()
        self._log = []
        self._running = False

        state_list = _traverse_and_wire_up(self, self.states)
        # TODO: _validate


    def start(self):
        assert not self._running
        if not self._attempt_transition('start'):
            raise RuntimeError("State machine couldn't start, "
                               "this shouldn't ever happen")
        self._running = True


# old deprecated code below

class StateMachine(object):
    def __init__(self, transition_map, initial_state, eventbus):
        assert initial_state in transition_map.keys()
        self._eb = eventbus
        self._running = False
        self._tmap = transition_map.copy()
        null_state = NullState()
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
