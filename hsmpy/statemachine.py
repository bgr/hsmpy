import logging
from collections import namedtuple
from eventbus import Event
from copy import copy
from itertools import izip_longest
import re


_log = logging.getLogger(__name__)


# used for parsing State name into signature tuple
re_name_and_index = re.compile("""
        \s*                   # optional whitespace before state name
        ([^\.\[\]]+)          # capture state name, can't contain: .[]
        \s*                   # optional whitespace between name and bracket
        \[\s*  (\d+)  \s*\]   # index number inside square brackets
        \s*                   # optional whitespace after closed brackets
        $                     # and nothing else
                        """, re.VERBOSE)
re_last_name = re.compile("""
        \s*                   # optional whitespace before state name
        ([^\.\[\]]+)          # capture state name, can't contain: .[]
        \s*                   # optional whitespace at the end
        $                     # and nothing else
                        """, re.VERBOSE)


class State(object):
    def __init__(self, states=None, on_enter=None, on_exit=None):
        """
            Constructor

            Parameters
            ----------
            states : dict or list (optional, empty dict by default)
                states can be a:
                    * dict, which makes this state a composite state that
                      has nested children substates
                    * list of (states_dict, transition_map) tuples, which
                      makes this state a container for sub-machines defined by
                      those tuples
            on_enter : function
                function to be called when state is entered, after state's
                *enter* method
            on_exit : function
                function to be called when state is exited, before state's
                *exit* method
        """
        self.states = {} if states is None else states
        self.parent = None
        self.sig = ('unnamed',)
        self.kind = 'unknown'
        self.on_enter = on_enter or do_nothing
        self.on_exit = on_exit or do_nothing

    def _enter(self, evt, hsm):
        """Used internally by HSM"""
        self.enter(evt, hsm)
        self.on_enter(evt, hsm)

    def _exit(self, evt, hsm):
        """Used internally by HSM"""
        self.on_exit(evt, hsm)
        self.exit(evt, hsm)

    def enter(self, evt, hsm):  # override
        """
            Called when entering this state, triggered by some transition.

            Override this function to implement actions that should be
            performed when entering the state.

            In addition to those actions, if *enter* argument was passed to
            constructor, that function will be invoked **after** this one.

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
        """
            Called when exiting this state, triggered by some transition.

            Override this function to implement actions that should be
            performed when exiting the state.

            In addition to those actions, if *exit* argument was passed to
            constructor, that function will be invoked **before** this one.

            Parameters
            ----------
            evt : Event
                event instance that triggered the transition
            hsm : HSM
                instance of HSM that this state is part of, useful for
                accessing data shared between all states
        """
        pass

    @staticmethod
    def sig_to_name(tup):
        def grouper(iterable, n, fillvalue=None):
            "Collect data into fixed-length chunks or blocks"
            # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
            args = [iter(iterable)] * n
            return izip_longest(fillvalue=fillvalue, *args)

        # last element of group will be None
        rename = lambda a, b: str(a) if b is None else '{0}[{1}]'.format(a, b)
        return '.'.join([rename(*t) for t in grouper(tup, 2)])

    @staticmethod
    def name_to_sig(name):
        # got to split manually, python regex doesn't support repeated captures
        segments = [n.strip() for n in name.split('.')]
        first_matches = [re_name_and_index.match(seg) for seg in segments[:-1]]
        last_match = re_last_name.match(segments[-1])
        if not all(first_matches + [last_match]):
            raise ValueError("Malformed state name '{0}'".format(name))
        first_elems = [(m.group(1).strip(), int(m.group(2).strip()))
                       for m in first_matches]
        sig = tuple(
            [el for tup in first_elems for el in tup]
            + [last_match.group().strip()])
        return sig

    @property
    def name(self):
        return State.sig_to_name(self.sig)

    @name.setter
    def name(self, val):
        self.sig = State.name_to_sig(val)

    def __repr__(self):
        return "{0} '{1}' ({2})".format(self.__class__.__name__,
                                        self.name, self.kind)

    def __iter__(self):
        return iter(self.states)

    @property
    def __attrs(self):
        # doesn't consider parent state, parents can be different!
        return (self.sig, self.on_enter, self.on_exit, self.kind)

    def __eq__(self, other):
        def check_states(a, b):
            if isinstance(a.states, list):  # already checked for same type
                key = lambda s: s.sig
                return sorted(a.states, key=key) == sorted(b.states, key=key)
            else:
                return a.states == b.states

        return (type(other) == type(self)
                and self.__attrs == other.__attrs
                and type(self.states) == type(other.states)
                and len(self.states) == len(other.states)
                and check_states(self, other))


class Initial(Event):
    """Used for defining initial transitions of composite states."""
    pass


# transitions

do_nothing = lambda evt, hsm: None  # action does nothing by default
always_true = lambda evt, hsm: True  # make guard always pass by default


def _make_tran(Which, target, action=None, guard=None):
    return Which(target, action or do_nothing, guard or always_true)


_Transition = namedtuple('Transition', 'target, action, guard')
_Local = namedtuple('LocalTransition', 'target, action, guard')
_Internal = namedtuple('InternalTransition', 'target, action, guard')


def Transition(target, action=None, guard=None):
    """
        Regular transition. Also used for initial transitions.

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
    return _make_tran(_Transition, target, action, guard)


def LocalTransition(target, action=None, guard=None):
    """
        Local transition.

        Valid only from parent state to child state or vice versa. Doesn't
        cause exiting from parent state.
    """
    return _make_tran(_Local, target, action, guard)


def InternalTransition(action=None, guard=None):
    """
        Internal transition.

        Doesn't have a target state. Doesn't cause change of states.
    """
    return _make_tran(_Internal, None, action, guard)


class Action(namedtuple('Action', 'name, function')):
    """
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
    def __call__(self, event, hsm):
        """Invokes the wrapped function"""
        return self.function(event, hsm)

    def __repr__(self):
        return self.name


class HSM(object):
    def __init__(self, states_map, transitions_map, skip_validation=False):
        """
            Constructor

            Parameters
            ----------
            states_map : dict
                dictionary that describes state hierarchy, it should have
                exactly one top-level item (state that acts as the container
                for all other nested states within it)
            transitions_map : dict
                dictionary that maps states described in states_map to their
                corresponding event-transition map
        """
        top, flattened, trans = _parse(states_map, transitions_map)
        self.flattened = flattened
        self.root = top
        self.trans = trans
        if not skip_validation:
            self._validate(states_map, self.trans, self.flattened)
        # empty object which can be used as a shared data between all states
        self.data = type('HSM_data', (object,), {})()
        self._running = False


    def start(self, eventbus):
        """
            Starts the machine (starts responding to events).

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

        self.eb = eventbus

        self.event_set = _get_events(self.flattened, self.trans)
        [self.eb.register(evt, self._handle_event) for evt in self.event_set]

        self._running = True

        self.current_state_set = set([self.root])

        # kick-start the machine
        # it has to be done by dispatching unique event (to make sure this
        # method is the only one who can dispatch it), in order to properly
        # queue up any calls to _handle_event that might happen during the
        # initial _handle_event call initiated by calling kick_start

        class KickStart(Event):
            pass

        def kick_start(evt=None):
            _log.debug("Starting HSM, entering '{0}' state".format(self.root))
            self.root._enter(None, self)  # enter top state
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
        _log.debug('HSM stopped')

    def _handle_event(self, event_instance):
        """
            Triggers transition (and associated actions) for event, or ignores
            it if none of the states in HSM's current state set is interested
            in that event (or guards don't pass).
        """
        exits, entries, new_states = _get_merged_sequences(
            self.current_state_set, event_instance, self.flattened, self.trans,
            self)

        if not exits and not entries and not new_states:
            _log.debug("No response for to event '{0}'".format(event_instance))
            return

        _log.debug("HSM responding to event '{0}'".format(event_instance))
        actions = exits + entries
        _log.debug("Performing actions: {0}".format(', '.join(
            ["'{0}'".format(action.name) for action in actions]
        )))
        [action(event_instance, self) for action in actions]

        assert new_states, "new state set cannot possibly be empty"

        self.current_state_set = set(new_states)
        _log.debug("HSM is now in '{0}'".format(self.current_state_set))

    def _validate(self, original_states, trans, flat):
        """
            Runs a series of checks on the given state machine layout described
            by given states_map and transitions_map. It checks that:

                * states_map must have single top (container) state
                * there are no unreachable states
                * states_map doesn't contain occurrences of states with same
                  name
                * transitions_map doesn't have keys or transitions that point
                  to nonexistent states
                * there are no composite states with missing or invalid initial
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

        if not len(original_states) == 1:
            rs("State tree should have exactly one top (root) state")

        unreachable = _find_unreachable_states(self.root, flat, trans)
        chk("Unreachable states", unreachable)

        duplicate_sigs = _find_duplicate_sigs(flat)
        chk("Duplicate state signatures", duplicate_sigs)

        nonx_sources = _find_nonexistent_transition_sources(flat, trans)
        chk("Keys in trans_map pointing to nonexistent states", nonx_sources)

        nonx_targets = _find_nonexistent_transition_targets(flat, trans)
        chk("Transition targets pointing to nonexistent states", nonx_targets)

        miss = _find_missing_initial_transitions(flat, trans)
        chk("Composite states with missing initial transitions", miss)

        inv_init = _find_invalid_initial_transitions(flat, trans)
        chk("Invalid initial transitions (must not be loop, "
            "local or point outside of the state)", inv_init)

        inv_local = _find_invalid_local_transitions(flat, trans)
        chk("Invalid local transitions (must be parent-child relationship, "
            "must not be loop or initial transition)", inv_local)


# helper functions:


def _get_state_by_sig(state_sig, flat_state_list):
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


def _get_incoming_transitions(target_state_sig, trans_dict,
                              include_loops=False):
    """
        Returns list of incoming transitions to given state.

        Return value is list of 3-tuples, where each tuple is
        (source_state_name, triggering_event, transition).
    """
    found = []
    for source_state_sig, outgoing_trans in trans_dict.items():
        for event, tran in outgoing_trans.items():
            is_loop = (target_state_sig == source_state_sig)
            if (tran.target == target_state_sig
                    and (include_loops or not is_loop)):
                    # this ^ will be false only when it's a loop
                    # and include_loops is False
                found += [(source_state_sig, event, tran)]
    return found


def _get_path_from_root(to_state):
    """
        Returns list of state **instances** that represent the path
        from root (inclusive) to given state.
    """
    if to_state.parent is None:
        return [to_state]
    return _get_path_from_root(to_state.parent) + [to_state]


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


def _get_state_response(source_state, event_instance, trans_dict, hsm):
    """
        Returns state that responds to given event when machine is in
        *source_state*, and transition to follow.

        Return value is tuple (responding_state_instance, transition).
    """
    tran = trans_dict.get(source_state.sig, {}).get(event_instance.__class__)
    # transition exists and its guard passes
    if tran is not None and tran.guard(event_instance, hsm):
        return (source_state, tran)
    # try looking up the hierarchy
    if source_state.parent is not None:
        return _get_state_response(source_state.parent, event_instance,
                                   trans_dict, hsm)
    return (None, None)


def _get_responses(state_set, event, trans_dict, hsm):
    """
        Returns list of (source_state, responding_state, transition) tuples
        describing all states that respond to given *event* instance when
        machine is in the set of states specified by *state_set*, and
        transitions to follow.

        When machine is in one state and *event* happens, it might not
        be that state which responds to the event, but some parent state.

        Return value is set of tuples (responding_state, transition).
    """
    resps = [( (st,) + _get_state_response(st, event, trans_dict, hsm) )
             for st in state_set]
    filtered = [r for r in resps if r[1] is not None]
    return filtered or [([], [], [])]



def _get_state_sequences(src_state, event, flat_states, trans_dict, hsm):
    # TODO: docstring
    resp_state, tran = _get_state_response(src_state, event, trans_dict, hsm)

    action_name = lambda st, descr: '{0}-{1}'.format(st.name, descr)
    evt_name = event.__class__.__name__

    # nothing happens if no state responds to event
    if resp_state is None:
        return [ ([], [], []) ]

    # wrap transition into Action
    tran_action = Action(action_name(resp_state, evt_name), tran.action)

    # in case of internal transition just perform the transition action
    # do not add any exit actions, and don't change the state (resulting state
    # is the source state)
    if isinstance(tran, _Internal):
        return [ ([], [tran_action], [src_state]) ]

    exits = []
    entries = []

    target_state = _get_state_by_sig(tran.target, flat_states)

    # states to exit in order to get to responding state
    exits_till_resp, _, _ = _get_path(src_state, resp_state)
    # more to exit from responding state and then to enter to get to target
    exits_from_resp, parent, entries = _get_path(resp_state, target_state)
    exits += exits_till_resp + exits_from_resp

    # also add exit and reentry actions for responding state if transition
    # is a LOOP transition or EXTERNAL transition (external transition goes
    # from parent to child or child to parent just like LOCAL transition
    # but it also exits and reenters the parent state
    is_external_tran = (parent in [resp_state, target_state]
                        and not isinstance(tran, _Local)
                        and not isinstance(event, Initial))
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
    # original transition action must come before any entry action
    entry_acts = [tran_action] + entry_acts

    # if transition ends at leaf state we're done, and it's the resulting state
    if target_state.kind == 'leaf':
        return [ (exit_acts, entry_acts, [target_state]) ]
    # if target state is composite, add exits and entries we got so far to
    # result tuple list, keeping resulting state empty (cannot end at composite
    # state), and follow the 'initial' transition recursively into the target
    # state, retrieving more tuples (composite state might even contain an
    # orthogonal state)
    elif target_state.kind == 'composite':
        tuples = [ (exit_acts, entry_acts, []) ]
        tuples += _get_state_sequences(target_state, Initial(), flat_states,
                                       trans_dict, hsm)
        return tuples
    # if transition ends at orthogonal state, add exits and entries we got so
    # far to result tuple list
    # to resulting tuple BUT with resulting state empty, and then add more
    # tuples recursively for every submachine by following initial transition
    # of each submachine
    elif target_state.kind == 'orthogonal':
        tuples = [ (exit_acts, entry_acts, []) ]
        tuples += _get_transition_sequences(target_state.states, Initial(),
                                            flat_states, trans_dict, hsm)
        return tuples
    assert False, "should never get here"


def _get_transition_sequences(state_set, event, flat_states, trans_dict, hsm):
    """
        Returns transition action sequence.

        Returned value is list of 3-tuples:
        (exit_actions_list, entry_actions_list, resulting_state), whose first
        two elements are lists containing ordered instances of Actions to be
        executed to perform the transition from given *source_state* to the
        returned *resulting_state* which is the state machine will be in after
        parforming the transition. If no state responds to given
        *event* instance, lists will be empty and value of *resulting_state*
        will be None. If state responds via internal transition
        *exit_actions_list* will be empty, *entry_actions_list* will contain
        single transition action and *resulting_state* will be None since no
        change of state is required.
    """
    seqs = [seq for st in state_set for seq in
            _get_state_sequences(st, event, flat_states, trans_dict, hsm)]
    return seqs


def _get_merged_sequences(state_set, event, flat_states, trans_dict, hsm):
    seqs = _get_transition_sequences(
        state_set, event, flat_states, trans_dict, hsm)

    extract = lambda i: _remove_duplicates([el for s in seqs for el in s[i]])
    exits = extract(0)
    entries = extract(1)
    resulting_states = extract(2)

    if entries and not resulting_states:
        assert False, "must have resulting states when entries exist"

    return (exits, entries, resulting_states)



def _get_events(flat_state_list, trans_dict):
    """
        Returns set of all event types that machine is
        interested in listening to.
    """
    def get_subclasses(cls):
        """Returns all subclasses of class (not only direct ones)"""
        ls = cls.__subclasses__()
        return ls + [subsub for sub in ls for subsub in get_subclasses(sub)]

    events = [evt for outgoing in trans_dict.values()
              for evt in outgoing.keys() if evt != Initial]
    events += [sub for evt in events for sub in get_subclasses(evt)]
    return set(events)


def _add_prefix(name, prefix):
    """Adds prefix to name"""
    prefix = prefix or ()
    if isinstance(name, str):
        return prefix + (name,)
    elif isinstance(name, tuple):
        return prefix + name
    raise ValueError("Invalid state name '{0}'".format(name))


def _rename_transitions(trans_dict, prefix):
    """Renames source state sigs and outgoing transition targets"""
    def rename_tran_target(tran):
        """Returns new transition with prefix prepended to target state sig"""
        if tran.target is None:
            return tran
        new_name = _add_prefix(tran.target, prefix)
        return tran._make((new_name, tran.action, tran.guard))

    def rename_event_trans_map(trans_map):
        """Renames transition targets in evt -> tran sub-dictionary"""
        return dict([(evt, rename_tran_target(tran))
                     for evt, tran in trans_map.items()])

    return dict([(_add_prefix(src_sig, prefix), rename_event_trans_map(outg))
                 for src_sig, outg in trans_dict.items()])


def _reformat(states_dict, trans_dict, prefix=None):
    """
        Renames states and transition targets.
        Extracts trans dicts from tuples that define orthogonal submachines
        and appends them all to one main trans_dict.
    """
    def fix(state_sig, val, parent_state=None):
        """Recursively rename and convert to state instance if needed"""
        if isinstance(val, State):
            # already defined as state
            # copy it, set name and parent, fix children states recursively
            new_state = copy(val)
            children = val.states
        else:
            new_state = State()
            children = val

        new_state.sig = _add_prefix(state_sig, prefix)
        new_state.parent = parent_state

        if not children:  # empty list or dict
            new_state.kind = 'leaf'
            subs, trans = ([], {})
        elif isinstance(children, list):
            new_state.kind = 'orthogonal'
            ch_prefix = lambda i: _add_prefix(state_sig, prefix) + (i,)
            # get renamed states and renamed trans for every submachine
            subs, trans = zip(*[_reformat(sdict, tdict, ch_prefix(i))
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
            subs, trans = _reformat(children, {}, prefix)
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
    fixed_trans.update(_rename_transitions(trans_dict, prefix))
    return (fixed_states, fixed_trans)


def _parse(states_dict, trans_dict):
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
    renamed_states, renamed_trans = _reformat(states_dict, trans_dict)
    top_state = renamed_states[0]
    flattened = _flatten(renamed_states)
    return (top_state, flattened, renamed_trans)


def _flatten(container):
    if isinstance(container, list):
        return [sub for cont_elem in container for sub in _flatten(cont_elem)]
    if isinstance(container, State):
        return [container] + _flatten(container.states)
    return [container]  # any other object


def _remove_duplicates(ls):
    seen = set()
    add_to_seen = lambda elem: not seen.add(elem)  # always returns True
    return [elem for elem in ls if elem not in seen and add_to_seen(elem)]


# validation methods:

def _find_duplicates(ls):
    """Returns list of elements that occur more than once in the given list."""
    import collections
    return [el for el, n in collections.Counter(ls).items() if n > 1]


def _find_duplicate_sigs(flat_state_list):
    """
        Returns list of state **sigs** that occur more than once in the given
        flattened state list.
    """
    return _find_duplicates([st.sig for st in flat_state_list])


def _find_nonexistent_transition_sources(flat_state_list, trans_dict):
    """
        Returns list of keys (state **instances**) found in transition map that
        don't have corresponding state in the states map.
    """
    state_names = [st.sig for st in flat_state_list]
    return [name for name in trans_dict.keys() if name not in state_names]


def _find_nonexistent_transition_targets(flat_state_list, trans_dict):
    """
        Returns list of transition targets (state **names**) found in
        transition map that don't have corresponding state in the states map.
    """
    state_names = [st.sig for st in flat_state_list]
    return [tran.target
            for dct in trans_dict.values()  # transitions dict for state
            for tran in dct.values()  # transition in state's transitions dict
            if (not isinstance(tran, _Internal)  # don't have targets
                and tran.target not in state_names)]  # no corresponding state


def _find_missing_initial_transitions(flat_state_list, trans_dict):
    """
        Returns list of composite state **instances** that don't have initial
        transition defined in transitions map.
    """
    composites = [st for st in flat_state_list
                  if st.kind == 'composite']
    return [st for st in composites
            if (trans_dict.get(st.sig) is None or
                trans_dict.get(st.sig).get(Initial) is None)]


def _find_invalid_initial_transitions(flat_state_list, trans_dict):
    """
        Returns list of composite state **instances** that have invalid initial
        transition defined.

        Initial transition is invalid if it's a self-loop, is defined as
        LocalTransition, has a target which is not a child of the state.
    """
    # TODO: OR have guards (implemented but untested)
    without = _find_missing_initial_transitions(flat_state_list, trans_dict)
    composites = [st for st in flat_state_list
                  if st.kind == 'composite' and st not in without]

    is_local = lambda tran: isinstance(tran, _Local)
    init_tran_of = lambda state: trans_dict[state.sig][Initial]
    init_tran_target_of = lambda state: _get_state_by_sig(
        init_tran_of(state).target, flat_state_list)

    return [st for st in composites if is_local(init_tran_of(st))
            or init_tran_of(st).target == st.sig
            or st not in _get_path_from_root(init_tran_target_of(st))
            or init_tran_of(st).guard(None, None) is not True]


def _find_invalid_local_transitions(flat_state_list, trans_dict):
    """
        Returns list invalid local transitions.

        List elements are 3-tuples (state_sig, event, transition).
        To be valid, local transition must be must be from superstate to
        substate or vice versa (source and target must be in parent-child
        relationship), and cannot be a self-loop.
    """
    bad_sources = _find_nonexistent_transition_sources(flat_state_list,
                                                       trans_dict)
    bad_targets = _find_nonexistent_transition_targets(flat_state_list,
                                                       trans_dict)
    bad_state_sigs = bad_sources + bad_targets

    get_by_sig = lambda sig: _get_state_by_sig(sig, flat_state_list)
    common_parent = lambda sig_a, sig_b: _get_common_parent(
        get_by_sig(sig_a), get_by_sig(sig_b)).sig

    return [(st_sig, evt.__name__, tran.target)
            for st_sig, outgoing in trans_dict.items()
            for evt, tran in outgoing.items()
            if st_sig not in bad_state_sigs and
            isinstance(tran, _Local) and (
            st_sig == tran.target or  # loop
            common_parent(st_sig, tran.target) not in [st_sig, tran.target])]


def _find_unreachable_states(top_state, flat_state_list, trans_dict):
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
        for parent in _get_path_from_root(state):
            visit(parent, visited)
        # visit transition targets going out of current state
        for tran in trans_dict.get(state.sig, {}).values():
            target_state = _get_state_by_sig(tran.target, flat_state_list)
            if target_state is not None:  # nonexistent state in trans_dict
                visit(target_state, visited)  # will be checked by another func
        return visited

    reachable = visit(top_state)
    return [st for st in flat_state_list if st not in reachable]
