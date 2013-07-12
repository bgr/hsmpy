import logging
from eventbus import Event

_log = logging.getLogger(__name__)


class Initial(Event):
    """Used to mark initial transitions of CompositeStates"""
    pass


class Transition(object):
    def __init__(self, target, action=None, guard=None):
        """
            Constructor

            Parameters
            ----------
            target : str
                name of the target state (in case of InternalTransition target
                is fixed to None)
            action : function/callable (optional)
                function to call when performing the transition, it must take
                two parameters: event instance and reference to HSM instance
            guard : function/callable (optional)
                function that evaluates to True/False, deciding whether to take
                this transiton or leave it to some other; must take two
                parameters: event instance and reference to HSM instance
        """
        if action is None:
            action = lambda evt, hsm: None  # action does nothing by default
        if guard is None:
            guard = lambda evt, hsm: True  # make guard always pass by default
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

    def __init__(self, name='unnamed_simple_state'):
        """
            Constructor
        """
        self.name = name
        self.states = {}  # for cleaner code, only CompositeState has substates
        self._hsm = None  # maybe not needed
        self._parent = None

    def enter(self, evt, hsm):  # override
        """
            Called when entering this state, triggered by some transition.

            Parameters
            ----------
            evt : Event
                event instance that triggered the transition
            hsm : HSM
                instance of HSM that this state is part of, useful for
                accessing data shared between all states
        """
        pass

    def exit(self, evt, hsm):  # override
        """Called when exiting this state (see 'enter')"""
        pass

    def __repr__(self):
        return "{0} '{1}'".format(self.__class__.__name__, self.name)

    def __getitem__(self, key):
        return self.states[key]


class CompositeState(State):
    def __init__(self, states, name='unnamed_composite_state'):
        """
            Constructor

            Parameters
            ----------
            states : dict
                mapping of state names to state instances, defining immediate
                children of this state
        """
        super(CompositeState, self).__init__(name)
        self.states = states


class Action(object):
    def __init__(self, name, function):
        """
            Constructor

            Action's purpose is to adapt different functions into common
            interface required when executing transitions.
            Action is a callable that take two parameters: event instance and
            HSM instance which are relayed to wrapped function.
            Actions are used (instantiated and called) internally and are not
            relevant for end users.

            Parameters
            ----------
            name : str
                descriptive name of action, useful for tests and debugging
            function : function/callable
                function to wrap, it must take two parameters: event instance
                and HSM instance
        """
        self.name = name
        self.function = function

    def __call__(self, event, hsm):
        """Invokes the wrapped function"""
        return self.function(event, hsm)

    def __repr__(self):
        return self.name


class HSM(object):
    def __init__(self, states_map, transitions_map):
        """
            Constructor

            Note: Immediately upon calling it will traverse all states in
            states_map and assign *name*, *_parent* and *_hsm* properties to
            each state, thus modifying the states_map, which makes this
            constructor a bit destructive.

            Parameters
            ----------
            states_map : dict
                dictionary that describes state hierarchy, it should have
                exactly one top-level item (instance of CompositeState that
                acts as the container for all other nested states within it)
            transitions_map : dict
                dictionary that maps states described in states_map to their
                corresponding event-transition map
        """
        # states tree must have single state as root
        self.states = states_map
        self.trans = transitions_map
        # empty object which can be used as a shared data between all states
        self.data = type('HSM_data', (object,), {})()
        self._log = []
        self._running = False
        self.flattened = self._traverse_and_wire_up(self.states)

    def _traverse_and_wire_up(self, states_dict, parent_state=None):
        """
            Recursively traverses the tree described by states_dict and updates
            states' *name*, *_parent* and *_hsm* properties.
            Returns flattened list of all state **instances**.
        """
        traversed = []  # will contain flattened subtree of state instances
        # traverse state tree
        for key_name, state in states_dict.items():
            state._parent = parent_state  # make state know its parent state
            state.name = key_name  # make state know its name
            state._hsm = self      # make state know about its HSM
            traversed += [state]   # add state to traversed list
            traversed += self._traverse_and_wire_up(state.states, state)
        return traversed

    def start(self, eventbus):
        """
            Checks the machine for valid structure and, if everything is
            correct, starts it (starts responding to events), otherwise raises
            exception.

            Parameters
            ----------
            eventbus : EventBus
                event bus on which to attach event listeners; it must support
                event queuing in order for HSM to function correctly

            Raises
            ------
            RuntimeError : when called again after it's already started
            ValueError : when states_map or transitions_map are not valid
        """
        if self._running:
            raise RuntimeError("Machine is already running")

        self._validate()

        self.eb = eventbus

        self.event_set = _get_events(self.flattened, self.trans)
        [self.eb.register(evt, self._handle_event) for evt in self.event_set]

        self._running = True

        self._current_state = self.states.values()[0]  # set root as current

        # kick-start the machine
        # it has to be done by dispatching unique event (to make sure this
        # method is the only one who can dispatch it), in order to properly
        # queue up any calls to _handle_event that might happen during the
        # initial _handle_event call initiated by calling kick_start

        class KickStart(Event):
            pass

        def kick_start(evt=None):
            self._handle_event(Initial())

        self.eb.register(KickStart, kick_start)
        self.eb.dispatch(KickStart())
        self.eb.unregister(KickStart, kick_start)

    def stop(self):
        """
            Stops responding to events (unregisters the HSM from the eventbus).
            It doesn't exit any states, just stops responding - you should take
            care of stopping logic using states and events before calling
            'stop'. It is assumed that you don't want to use the instance
            anymore after calling 'stop', so machine behaviour after stopping
            and calling 'start' again was not tested.
        """
        if not self._running:
            return
        [self.eb.unregister(evt, self._handle_event) for evt in self.event_set]
        self._running = False

    def _handle_event(self, event_instance):
        """
            Triggers transition (and associated actions) for event, or ignores
            it if none of the states in HSM's current state set is interested
            in that event (or guards don't pass).
        """
        print 'handle event', event_instance
        exits, entries, new_state = _get_transition_sequence(
            self._current_state, event_instance,
            self.flattened, self.trans, self)

        if new_state:  # might be None if no state responds to event
            [action(event_instance, self) for action in exits + entries]
            self._current_state = new_state

    def _validate(self):
        """
            Runs a series of checks on the given state machine layout described
            by given states_map and transitions_map. It checks that:

                * states_map must have single top (container) state
                * there are no unreachable states
                * states_map doesn't contain multiple occurrences of same state
                  object instance
                * states_map doesn't contain occurrences of states with same
                  name
                * transitions_map doesn't have keys or transitions that point
                  to nonexistent states
                * there are no CompositeStates with missing or invalid initial
                  transitions
                * no invalid local transitions

            Raises
            ------
            ValueError : if any of the checks fails, with failure cause
                described in error message
        """
        def rs(msg):
            raise ValueError(msg)

        def chk(msg, ls):
            if ls:
                items = ["  {0}: {1}".format(n + 1, str(el))
                         for n, el in enumerate(ls)]
                rs(msg + '\n' + '\n'.join(items))

        flat = self.flattened
        states = self.states
        trans = self.trans

        if not len(states) == 1:
            rs("State tree should have exactly one top (root) state")

        unreachable = _find_unreachable_states(states.values()[0], flat, trans)
        chk("Unreachable states", unreachable)

        duplicate_names = _find_duplicate_names(flat)
        chk("Duplicate state names", duplicate_names)

        duplicate_instances = _find_duplicates(flat)
        chk("Duplicate state instances", duplicate_instances)

        nonx_sources = _find_nonexistent_transition_sources(flat, trans)
        chk("Keys in trans_map pointing to nonexistent states", nonx_sources)

        nonx_targets = _find_nonexistent_transition_targets(flat, trans)
        chk("Transition targets pointing to nonexistent states", nonx_targets)

        miss = _find_missing_initial_transitions(flat, trans)
        chk("CompositeStates with missing initial transitions", miss)

        inv_init = _find_invalid_initial_transitions(flat, trans)
        chk("Invalid initial transitions (must not be loop, "
            "local or point outside of the state)", inv_init)

        inv_local = _find_invalid_local_transitions(flat, trans)
        chk("Invalid local transitions (must be parent-child relationship, "
            "must not be loop or initial transition)", inv_local)


# helper functions:

def _get_children(parent_state):
    """
        Returns the list of all children state **instances** in sub-tree of
        given parent state **instance**.
    """
    direct_children = parent_state.states.values()
    return direct_children + [ch for dir_ch in direct_children
                              for ch in _get_children(dir_ch)]


def _get_state_by_name(state_name, flat_state_list):
    """
        Looks up and returns the state **instance** for given state **name**.
    """
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
    """
        Returns list of incoming transitions to given state.

        Return value is list of 3-tuples, where each tuple is
        (source_state_name, triggering_event, transition).
    """
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
    """
        Returns list of state **instances** that represent the path
        from root (inclusive) to given state.
    """
    if to_state._parent is None:
        return [to_state]
    return _get_path_from_root(to_state._parent) + [to_state]


def _get_path(from_state, to_state):
    """
        Returns the path from given state **instance** to another.

        Return value is 3-tuple (list_of_state_instances_to_exit,
        common_parent, list_of_state_instances_to_enter).
    """
    from_path = _get_path_from_root(from_state)
    to_path = _get_path_from_root(to_state)
    common_path = [a for a, b in zip(from_path, to_path) if a == b]
    common_parent = common_path[-1]
    exits = list(reversed([st for st in from_path if st not in common_path]))
    entries = [st for st in to_path if st not in common_path]
    return (exits, common_parent, entries)


def _get_common_parent(state_A, state_B):
    """
        Returns the common parent state **instance** for given two state
        **instances**.

        If one state is parent of the other, it'll return that state.
    """
    return _get_path(state_A, state_B)[1]


def _get_response(source_state, event_instance, trans_dict, hsm):
    """
        Returns state that responds to given event, and transition to follow.

        When machine is in *source_state* and *event_instance* happens, it
        might not be the *source_state* that responds to that event, but some
        parent state (or state in another orthogonal region - not yet
        implemented).

        Return value is tuple (responding_state_instance, transition).
    """
    tran = trans_dict.get(source_state.name, {}).get(event_instance.__class__)
    if tran is None:  # maybe it has internal transition defined
        tran = source_state.interests.get(event_instance.__class__)
    # try again, and only match if transition guard passes
    if tran is not None and tran.guard(event_instance, hsm):
        return (source_state, tran)
    # try looking up the hierarchy
    if source_state._parent is not None:
        return _get_response(source_state._parent, event_instance,
                             trans_dict, hsm)
    return (None, None)


def _get_transition_sequence(source_state, event_instance,
                             flat_state_list, trans_dict, hsm):
    """
        Returns transition action sequence.

        Returned value is 3-tuple:
        (exit_actions_list, entry_actions_list, resulting_state), whose first
        two elements are lists containing ordered instances of Actions to be
        executed to perform the transition from given *source_state* to the
        returned *resulting_state* which is the state machine will be in after
        parforming the transition. If no state responds to given
        *event_instance*, lists will be empty and value of *resulting_state*
        will be None.
    """
    # state that responds to event might not be the source_state
    resp_state, transition = _get_response(source_state, event_instance,
                                           trans_dict, hsm)
    if resp_state is None:
        return ([], [], None)  # no state responds to event

    target_state = _get_state_by_name(transition.target, flat_state_list)

    action_name = lambda st, descr: '{0}-{1}'.format(st.name, descr)

    exits_till_resp, _, _ = _get_path(source_state, resp_state)
    exits_from_resp, parent, entries = _get_path(resp_state, target_state)

    exits = exits_till_resp + exits_from_resp

    # also add exit and reentry actions for responding state if transition
    # is a LOOP transition or EXTERNAL transition (external transition goes
    # from parent to child or child to parent just like LOCAL transition but
    # it also exits and reenters the parent state
    is_external_tran = (parent in [resp_state, target_state]
                        and not isinstance(transition, LocalTransition)
                        and not isinstance(event_instance, Initial))
    state_to_add = []

    if resp_state is target_state:
        state_to_add = [resp_state]
    elif is_external_tran:
        state_to_add = [parent]

    exits = exits + state_to_add
    entries = state_to_add + entries

    # wrap in Action objects
    exit_acts = [Action(action_name(st, 'exit'), st.exit) for st in exits]
    entry_acts = [Action(action_name(st, 'entry'), st.enter) for st in entries]


    resulting_state = target_state
    # if target state is composite, follow its 'initial' transition
    # recursively and append more entry actions to entries list
    # and also update resulting state - the final entered state
    if isinstance(target_state, CompositeState):
        # cannot have exits if machine is valid
        _, more_entry_acts, resulting_state = _get_transition_sequence(
            target_state, Initial(), flat_state_list, trans_dict, hsm)
        entry_acts += more_entry_acts

    # original transition action must come before any entry action
    evt_name = event_instance.__class__.__name__
    tran_action = Action(action_name(resp_state, evt_name), transition.action)
    entry_acts = [tran_action] + entry_acts

    return (exit_acts, entry_acts, resulting_state)


def _get_events(flat_state_list, trans_dict):
    """
        Returns set of all event types that machine is
        interested in listening to.
    """
    trans = [evt for outgoing in trans_dict.values()
             for evt in outgoing.keys() if evt != Initial]
    internal = [evt for state in flat_state_list
                for evt in state.interests.keys()]
    return set(trans + internal)


# validation methods:

def _find_duplicates(ls):
    """Returns list of elements that occur more than once in the given list."""
    import collections
    return [el for el, n in collections.Counter(ls).items() if n > 1]


def _find_duplicate_names(flat_state_list):
    """
        Returns list of state **names** that occur more than once in the given
        flattened state list.
    """
    return _find_duplicates([st.name for st in flat_state_list])


def _find_nonexistent_transition_sources(flat_state_list, trans_dict):
    """
        Returns list of keys (state **instances**) found in transition map that
        don't have corresponding state in the states map.
    """
    state_names = [st.name for st in flat_state_list]
    return [name for name in trans_dict.keys() if name not in state_names]


def _find_nonexistent_transition_targets(flat_state_list, trans_dict):
    """
        Returns list of transition targets (state **names**) found in
        transition map that don't have corresponding state in the states map.
    """
    state_names = [st.name for st in flat_state_list]
    return [tran.target
            for dct in trans_dict.values()  # transitions dict for state
            for tran in dct.values()  # transition in state's transitions dict
            if tran.target not in state_names]


def _find_missing_initial_transitions(flat_state_list, trans_dict):
    """
        Returns list of CompositeState **instances** that don't have initial
        transition defined in transitions map.
    """
    composites = [st for st in flat_state_list
                  if isinstance(st, CompositeState)]
    return [st for st in composites
            if (trans_dict.get(st.name) is None or
                trans_dict.get(st.name).get(Initial) is None)]


def _find_invalid_initial_transitions(flat_state_list, trans_dict):
    """
        Returns list of CompositeState **instances** that have invalid initial
        transition defined.

        Initial transition is invalid if it's a self-loop, is defined as
        LocalTransition, has a target which is not a child of the state,
        or has a guard (not yet implemented).
    """
    # TODO: OR have guards
    without = _find_missing_initial_transitions(flat_state_list, trans_dict)
    composites = [st for st in flat_state_list
                  if isinstance(st, CompositeState) and st not in without]

    is_local = lambda tran: isinstance(tran, LocalTransition)
    get_init_tran = lambda state: trans_dict[state.name][Initial]

    return [st for st in composites
            if is_local(get_init_tran(st)) or
            _get_state_by_name(get_init_tran(st).target, flat_state_list)
            not in _get_children(st)]


def _find_invalid_local_transitions(flat_state_list, trans_dict):
    """
        Returns list invalid local transitions.

        List elements are 3-tuples (state_name, event, transition).
        To be valid, local transition must be must be from superstate to
        substate or vice versa (source and target must be in parent-child
        relationship), and cannot be a self-loop.
    """
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
    """
        Returns list of state **instances** that are unreachable.

        It checks if state can be reached by recursively following all
        transitions going out from top state. Any state that wasn't visited
        cannot be reached by any means.
    """
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
