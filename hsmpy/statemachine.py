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


class LoopTransition(Transition):
    def __init__(self, action=None, guard=None):
        super(self).__init__(None, action, guard)


class State(object):
    interests = {}  # override

    def enter(self):  # override
        pass

    def exit(self):  # override
        pass


class CompositeState(State):
    def __init__(self, states):
        self.states = states

# after bundling states and transitions by calling HSM.bundle(),
# states will get additional properties: _hsm, name


class NullState(State):
    # every FSM will be in this state before calling fsm.start()
    pass


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
