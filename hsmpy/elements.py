import logging
from collections import namedtuple
from eventbus import Event
from itertools import izip_longest
import re
from logic import parse, get_events, get_merged_sequences, entry_sequence
from validation import (find_unreachable_states,
                        find_duplicate_sigs,
                        find_nonexistent_transition_sources,
                        find_nonexistent_transition_targets,
                        find_missing_initial_transitions,
                        find_invalid_initial_transitions,
                        find_invalid_local_transitions,
                        find_invalid_choice_transitions)


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
_Choice = namedtuple('ChoiceTransition', 'switch, default, key, action')


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


def ChoiceTransition(switch, default=None, key=None, action=None):
    """
        Choice transition.

        Allows choosing a target state based on the value returned by *key*
        function. Target state is chosen from *switch* dictionary which maps
        values returned by *key* function to strings representing target state
        names.

        Parameters
        ----------
        switch : dict
            mapping of values to state names
        default : str (optional)
            name of default target state to transition to if *switch* doesn't
            have a key returned by *key* function (and in that case if
            *default* is left unspecified no transition will be performed)
        key : function (optional)
            function that takes two parameters: event instance and HSM
            instance, and returns a value that matches *switch* dict keys.
            if unspecified, event_instance.data will be used as key
        action : func (optional)
            action to be performed when transition is performed
    """
    default_key = lambda evt, hsm: evt.data
    return _Choice(switch, default, key or default_key, action or do_nothing)


class Action(namedtuple('Action', 'name, function, item')):
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
        item : State or Transition
            original object whose function is wrapped
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
        top, flattened, trans = parse(states_map, transitions_map)
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

        self.event_set = get_events(self.flattened, self.trans)
        [self.eb.register(evt, self._handle_event) for evt in self.event_set]

        self._running = True

        self.current_state_set = set([self.root])

        # kick-start the machine
        # it has to be done by dispatching unique event (to make sure this
        # method is the only one who can dispatch it), in order to properly
        # queue up any calls to _handle_event that might happen during the
        # initial _perform_actions call initiated by calling kick_start

        class KickStart(Event):
            pass

        def kick_start(evt=None):
            _log.debug("Starting HSM, entering '{0}' state".format(self.root))
            actions = entry_sequence(self.root, self.trans, self.flattened)
            self._perform_actions(actions, Initial())
            self.current_state_set = set(act.item for act in actions
                                         if isinstance(act.item, State))

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

    def _perform_actions(self, actions, event):
            _log.debug("Performing actions for event {0}: {1}".format(
                event.__class__.__name__,
                ', '.join(["'{0}'".format(act.name) for act in actions])
            ))
            [act(event, self) for act in actions]

    def _handle_event(self, event):
        """
            Triggers transition (and associated actions) for event, or ignores
            it if none of the states in HSM's current state set is interested
            in that event (or guards don't pass).
        """
        exits, entries, new_state_set = get_merged_sequences(
            self.current_state_set, event, self.trans, self.flattened, self)

        assert new_state_set, "New state set cannot possibly be empty"

        actions = exits + entries
        self._perform_actions(actions, event)

        self.current_state_set = new_state_set
        _log.debug("HSM is now in states: {0}".format(
            ', '.join(st.name for st in self.current_state_set)))

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

        unreachable = find_unreachable_states(self.root, flat, trans)
        chk("Unreachable states", unreachable)

        duplicate_sigs = find_duplicate_sigs(flat)
        chk("Duplicate state signatures", duplicate_sigs)

        nonx_sources = find_nonexistent_transition_sources(flat, trans)
        chk("Keys in trans_map pointing to nonexistent states", nonx_sources)

        nonx_targets = find_nonexistent_transition_targets(flat, trans)
        chk("Transition targets pointing to nonexistent states", nonx_targets)

        miss = find_missing_initial_transitions(flat, trans)
        chk("Composite states with missing initial transitions", miss)

        inv_init = find_invalid_initial_transitions(flat, trans)
        chk("Invalid initial transitions (must not be loop, "
            "local or point outside of the state)", inv_init)

        inv_local = find_invalid_local_transitions(flat, trans)
        chk("Invalid local transitions (must be parent-child relationship, "
            "must not be loop or initial transition)", inv_local)

        inv_choice = find_invalid_choice_transitions(flat, trans)
        chk("Invalid choice transitions", inv_choice)
