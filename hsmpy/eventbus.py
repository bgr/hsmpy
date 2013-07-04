class EventBus(object):
    def __init__(self):
        self.listeners = {}

    def register(self, event_type, callback):
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

    def dispatch(self, event, aux=None):
        callbacks = [cb for cb in self.listeners.get(event, [])]
        [cb(event, aux) for cb in callbacks]
