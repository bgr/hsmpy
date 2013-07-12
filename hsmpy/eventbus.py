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

    def dispatch(self, event):
        if not isinstance(event, Event):
            raise TypeError("Must subclass Event")

        # TODO: check for infinite dispatch loops

        # add event to queue
        self.queue += [event]

        # if dispatch is currently in progress just leave event on queue
        # it will be served by currently running method
        if self.dispatch_in_progress:
            return

        # lock to prevent other calls
        self.dispatch_in_progress = True

        while self.queue:
            event = self.queue.pop()
            # gather all callbacks registered for event
            callbacks = [cb for cb in self.listeners.get(event.__class__, [])]
            # perform gathered calls
            [cb(event) for cb in callbacks]

        # unlock
        self.dispatch_in_progress = False
