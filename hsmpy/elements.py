import logging
from eventbus import Event
from itertools import izip_longest
import re
from logic import parse, get_events, perform_transition, enter
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
                function taking one argument - HSM instance, that will be
                called when state is entered, after state's *enter* method
            on_exit : function
                function taking one argument - HSM instance, that will be
                called when state is exited, before state's *exit* method
        """
        self.states = {} if states is None else states
        self.parent = None
        self.sig = ('unnamed',)
        self.kind = 'unknown'
        self.on_enter = on_enter or do_nothing
        self.on_exit = on_exit or do_nothing

    def _do_enter(self, hsm):
        """Used internally by HSM"""
        self.enter(hsm)
        self.on_enter(hsm)

    def _do_exit(self, hsm):
        """Used internally by HSM"""
        self.on_exit(hsm)
        self.exit(hsm)

    def enter(self, hsm):  # for overriding by user
        """
            Called when entering this state, triggered by some transition.

            Override this function to implement actions that should be
            performed when entering the state.

            In addition to those actions, if *enter* argument was passed to
            constructor, that function will be invoked **after** this one.

            Parameters
            ----------
            hsm : HSM
                instance of HSM that this state is part of, useful for
                accessing data shared between all states
        """
        pass

    def exit(self, hsm):  # for overriding by user
        """
            Called when exiting this state, triggered by some transition.

            Override this function to implement actions that should be
            performed when exiting the state.

            In addition to those actions, if *exit* argument was passed to
            constructor, that function will be invoked **before** this one.

            Parameters
            ----------
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

do_nothing = lambda *_, **__: None  # action does nothing by default
always_true = lambda *_, **__: True  # make guard always pass by default
default_key = lambda evt, _: evt.data

class _GenericTransition(object):
    __slots__ = ['switch', 'default_key', 'key', 'action', 'guard', 'source']

    def __init__(self, switch_dict, default_target,
                 key_func=None, action_func=None, guard_func=None):
        if not isinstance(switch_dict, dict):
            raise TypeError("switch must be a dict")
        self.switch = switch_dict.copy()
        self.default = default_target
        self.key = key_func or default_key
        self.action = action_func or do_nothing
        self.guard = guard_func or always_true
        self.source = None  # will be set by reformat function

    def get_target(self, evt, hsm):
        k = self.key(evt, hsm)
        return self.switch.get(k) or self.default

    def __call__(self, evt, hsm):
        return self.action(evt, hsm)

    def __repr__(self):
        return '{0}(switch={1}, source={2})'.format(self.__class__.__name__,
                                                    self.switch, self.source)

    @property
    def __attrs(self):
        # doesn't consider source
        return (self.switch, self.default, self.key, self.action, self.guard)

    def __eq__(self, other):
        return type(other) == type(self) and self.__attrs == other.__attrs



class ChoiceTransition(_GenericTransition):
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
            function that takes two parameters - event and HSM instance, and
            returns values that match *switch* dict's keys.
            if unspecified, event_instance.data will be used as key
        action : function/callable (optional)
            function to call when performing the transition, it must take
            two parameters: event instance and reference to HSM instance
        guard : function/callable (optional)
            function that takes two parameters - event and HSM instance, and
            evaluates to True/False, deciding whether to perform transition:
                * True - source state of this transition responds and
                  transition is performed,
                * False - HSM will check up the state tree if some parent state
                  to responds
            if omitted, a guard function that always returns True is used
            see Transition
    """

    def __init__(self, switch, default=None, key=None, action=None):
        super(ChoiceTransition, self).__init__(switch, default, key, action)
        if not switch:
            raise ValueError("switch dict cannot be empty")


class _SingleTargetTransition(_GenericTransition):
    def __init__(self, target, action=None, guard=None):
        switch = { 0: target }
        super(_SingleTargetTransition, self).__init__(switch, None, None,
                                                      action, guard)

    def get_target(self, *_, **__):
        return self.switch.get(0)

    @property
    def target(self):
        return self.get_target()

    def __repr__(self):
        return '{0}(target={1}, source={2})'.format(self.__class__.__name__,
                                                    self.target, self.source)


class Transition(_SingleTargetTransition):
    """
        Regular (external) transition. Also used for initial transitions.

        Parameters
        ----------
        target : str
            name of the target state (in case of InternalTransition target
            is fixed to None)
        action : function/callable (optional)
            function to call when performing the transition, it must take
            two parameters: event instance and reference to HSM instance
        guard : function/callable (optional)
            function that takes two parameters - event and HSM instance, and
            evaluates to True/False, deciding whether to perform transition:
                * True - source state of this transition responds and
                  transition is performed,
                * False - HSM will check up the state tree if some parent state
                  to responds
            if omitted, a guard function that always returns True is used
    """
    pass


class LocalTransition(_SingleTargetTransition):
    """
        Local transition.

        Valid only from parent state to child state or vice versa. Doesn't
        cause exiting from parent state.
    """
    pass


class InternalTransition(_GenericTransition):
    """
        Internal transition.

        Doesn't have a target state. Doesn't cause change of states.
    """

    def __init__(self, action, guard=None):
        super(InternalTransition, self).__init__({}, None, None, action, guard)

    def get_target(self, *_, **__):
        return None




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
            entered = enter(self.root, self.trans, self.flattened, self)
            self.current_state_set = set(entered)
            _log.debug("HSM is now in states: " +
                       ', '.join(st.name for st in entered))

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


    def _handle_event(self, event):
        """
            Triggers transition (and associated actions) for event, or ignores
            it if none of the states in HSM's current state set is interested
            in that event (or guards don't pass).
        """
        _log.debug("Performing transition for "
                   "event {0}".format(event.__class__.__name__))

        new_state_set = perform_transition(
            self.current_state_set, event, self.trans, self.flattened, self)

        assert new_state_set, "New state set cannot possibly be empty"
        self.current_state_set = new_state_set

        _log.debug("HSM is now in states: " +
                   ', '.join(st.name for st in self.current_state_set))


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
        chk("Invalid initial transitions", inv_init)

        inv_local = find_invalid_local_transitions(flat, trans)
        chk("Invalid local transitions (must be parent-child relationship, "
            "must not be loop or initial transition)", inv_local)

        inv_choice = find_invalid_choice_transitions(flat, trans)
        chk("Invalid choice transitions", inv_choice)
