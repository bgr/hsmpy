import logging

_log = logging.getLogger(__name__)


class Event(object):
    def __init__(self, data=None):
        self.data = data


class EventBus(object):
    def __init__(self):
        self.listeners = {}
        self.queue = []
        self.dispatch_in_progress = False

    def register(self, event_type, callback):
        if not issubclass(event_type, Event):
            raise TypeError("Must be a subclass of Event")

        if event_type not in self.listeners:
            self.listeners[event_type] = set()
        self.listeners[event_type].add(callback)
        _log.debug("Registering for {0}".format(event_type.__name__))
        _log.debug(self._get_stats())


    def unregister(self, event_type, callback):
        if event_type not in self.listeners:
            raise LookupError("Noone listens to '{0}'".format(event_type))

        group = self.listeners[event_type]

        if callback not in group:
            raise LookupError("Listener '{0}' wasn't registered "
                              "for '{1}'".format(callback, event_type))

        group.remove(callback)

        if len(group) == 0:
            del self.listeners[event_type]
        _log.debug("Un-registering for {0}".format(event_type.__name__))
        _log.debug(self._get_stats())

    def dispatch(self, event):
        if not isinstance(event, Event):
            raise TypeError("Must subclass Event")

        # TODO: check for infinite dispatch loops

        # add event to queue
        self.queue += [event]

        # if dispatch is currently in progress just leave event on queue
        # it will be served by currently running method
        if self.dispatch_in_progress:
            _log.debug("Event {0} added to queue (dispatch already in "
                       "progress, exiting)".format(event.__class__.__name__))
            return

        _log.debug("Event {0} added to queue, starting "
                   "dispatch".format(event.__class__.__name__))

        # lock to prevent other calls
        self.dispatch_in_progress = True

        while self.queue:
            event = self.queue.pop(0)
            # gather all callbacks registered for event
            callbacks = [cb for cb in self.listeners.get(event.__class__, [])]
            _log.debug("Invoking {0} callbacks for {1}".format(
                len(callbacks), event.__class__.__name__))
            # perform gathered calls
            [cb(event) for cb in callbacks]

        # unlock
        self.dispatch_in_progress = False
        _log.debug("Dispatch done".format(event.__class__.__name__))

    def _get_stats(self):
        groups = [(evt.__name__, len(grp))
                  for evt, grp in self.listeners.items()]
        total = sum(l for _, l in groups)
        return "Groups: {n_groups}, total callbacks: {total} - {items}".format(
            n_groups=len(groups), total=total, items=', '.join(
                ['{0}: {1}'.format(evt, l) for evt, l in groups]))
