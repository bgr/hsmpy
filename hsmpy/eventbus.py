class Event(object):
    def __init__(self, data):
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

        if not self.dispatch_in_progress:
            # set lock for upcoming calls to 'dispatch' method
            self.dispatch_in_progress = True

            # gather all callbacks registered for initial event
            callbacks = [cb for cb in self.listeners.get(event.__class__, [])]

            while True:  # more events might get queued up while dispatching
                [cb(event) for cb in callbacks]  # perform gathered calls
                if not self.queue:  # check if new events have been queued up
                    break
                # events were queued, gather new callbacks for queued events
                callbacks = [cb for evt in self.queue
                             for cb in self.listeners.get(evt.__class__, [])]
                self.queue = []

            # unlock
            self.dispatch_in_progress = False

        else:  # dispatching currently in progress, add event to queue
            self.queue += [event]
