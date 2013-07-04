import pytest
from hsmpy.eventbus import EventBus


class Dummy(object):
    def __init__(self):
        self.x = 1

    def increment(self, *_):
        self.x += 1


class Test_single_listener(object):

    def setup_class(self):
        self.eb = EventBus()
        self.obj = Dummy()

    def test_can_register(self):
        self.eb.register('hey', self.obj.increment)
        assert self.obj.x == 1  # unchanged

    def test_can_fire(self):
        self.eb.dispatch('hey')
        assert self.obj.x == 2
        self.eb.dispatch('hey')
        assert self.obj.x == 3

    def test_can_unregister(self):
        self.eb.unregister('hey', self.obj.increment)
        self.eb.dispatch('hey')
        assert self.obj.x == 3  # unchanged


class Test_multiple_listeners(object):

    def setup_class(self):
        self.eb = EventBus()
        self.deaf = Dummy()
        self.hey = Dummy()
        self.you = Dummy()
        self.eb.register('hey', self.hey.increment)
        self.eb.register('you', self.you.increment)
        assert self.deaf.x == 1
        assert self.hey.x == 1
        assert self.you.x == 1

    def test_firing_impacts_only_interested_listener(self):
        self.eb.dispatch('hey')
        assert self.deaf.x == 1  # unchanged
        assert self.hey.x == 2
        assert self.you.x == 1  # unchanged
        self.eb.dispatch('hey')
        assert self.deaf.x == 1  # unchanged
        assert self.hey.x == 3
        assert self.you.x == 1  # unchanged
        self.eb.dispatch('you')
        assert self.deaf.x == 1  # unchanged
        assert self.hey.x == 3
        assert self.you.x == 2  # unchanged

    def test_others_work_after_one_is_unregistered(self):
        self.eb.unregister('hey', self.hey.increment)
        self.eb.dispatch('hey')
        assert self.deaf.x == 1  # unchanged
        assert self.hey.x == 3  # unchanged
        assert self.you.x == 2  # unchanged
        self.eb.dispatch('you')
        assert self.deaf.x == 1  # unchanged
        assert self.hey.x == 3  # unchanged
        assert self.you.x == 3  # unchanged

    def test_can_unregister_last_listener(self):
        self.eb.unregister('you', self.you.increment)
        self.eb.dispatch('hey')
        self.eb.dispatch('you')
        assert self.deaf.x == 1  # unchanged
        assert self.hey.x == 3  # unchanged
        assert self.you.x == 3  # unchanged


class Test_raising_errors(object):

    def setup_class(self):
        self.eb = EventBus()
        self.deaf = Dummy()
        self.hey = Dummy()
        self.you = Dummy()

    def test_raise_when_trying_to_unregister_before_registering(self):
        with pytest.raises(LookupError):
            self.eb.unregister('hey', self.hey.increment)

    def test_raise_when_unregistering_wrong_listener(self):
        self.eb.register('hey', self.hey.increment)
        with pytest.raises(LookupError):
            self.eb.unregister('hey', self.you.increment)

    def test_raise_when_unregistering_from_wrong_event_type(self):
        with pytest.raises(LookupError):
            self.eb.unregister('you', self.hey.increment)

    def test_raise_when_already_unregistered(self):
        self.eb.unregister('hey', self.hey.increment)
        with pytest.raises(LookupError):
            self.eb.unregister('hey', self.hey.increment)
