import pytest
from hsmpy.eventbus import EventBus, Event


class Dummy(object):
    def __init__(self):
        self.x = 1

    def increment(self, evt):
        self.x += evt.data

class PingEvent(Event): pass
class AnotherEvent(Event): pass


class Test_single_listener:

    def setup_class(self):
        self.eb = EventBus()
        self.obj = Dummy()

    def test_can_register(self):
        self.eb.register(PingEvent, self.obj.increment)
        assert self.obj.x == 1  # unchanged

    def test_can_fire(self):
        self.eb.dispatch(PingEvent(1))
        assert self.obj.x == 2
        self.eb.dispatch(AnotherEvent(1))
        assert self.obj.x == 2  # unchanged
        self.eb.dispatch(PingEvent(4))
        assert self.obj.x == 6

    def test_can_unregister(self):
        self.eb.unregister(PingEvent, self.obj.increment)
        self.eb.dispatch(PingEvent(2))
        assert self.obj.x == 6  # unchanged


class Test_multiple_listeners:

    def setup_class(self):
        self.eb = EventBus()
        self.deaf = Dummy()
        self.hey = Dummy()
        self.you = Dummy()
        self.eb.register(PingEvent, self.hey.increment)
        self.eb.register(AnotherEvent, self.you.increment)
        assert self.deaf.x == 1
        assert self.hey.x == 1
        assert self.you.x == 1

    def test_firing_impacts_only_interested_listener(self):
        self.eb.dispatch(PingEvent(1))
        assert self.deaf.x == 1
        assert self.hey.x == 2  # changed
        assert self.you.x == 1
        self.eb.dispatch(PingEvent(1))
        assert self.deaf.x == 1
        assert self.hey.x == 3  # changed
        assert self.you.x == 1
        self.eb.dispatch(AnotherEvent(1))
        assert self.deaf.x == 1
        assert self.hey.x == 3
        assert self.you.x == 2  # changed

    def test_others_work_after_one_is_unregistered(self):
        self.eb.unregister(PingEvent, self.hey.increment)
        self.eb.dispatch(PingEvent(2))
        # all unchanged
        assert self.deaf.x == 1
        assert self.hey.x == 3
        assert self.you.x == 2
        self.eb.dispatch(AnotherEvent(2))
        assert self.deaf.x == 1
        assert self.hey.x == 3
        assert self.you.x == 4  # changed

    def test_can_unregister_last_listener(self):
        self.eb.unregister(AnotherEvent, self.you.increment)
        self.eb.dispatch(PingEvent(3))
        self.eb.dispatch(AnotherEvent(3))
        # all unchanged
        assert self.deaf.x == 1
        assert self.hey.x == 3
        assert self.you.x == 4


class Test_raising_errors:

    def setup_class(self):
        self.eb = EventBus()
        self.deaf = Dummy()
        self.hey = Dummy()
        self.you = Dummy()

    def test_raise_when_event_is_of_wrong_type(self):
        with pytest.raises(TypeError):
            self.eb.register(EventBus, self.hey.increment)

    def test_raise_when_trying_to_unregister_before_registering(self):
        with pytest.raises(LookupError):
            self.eb.unregister(PingEvent, self.hey.increment)

    def test_raise_when_unregistering_wrong_listener(self):
        self.eb.register(PingEvent, self.hey.increment)
        with pytest.raises(LookupError):
            self.eb.unregister(PingEvent, self.you.increment)

    def test_raise_when_unregistering_from_wrong_event_type(self):
        with pytest.raises(LookupError):
            self.eb.unregister(AnotherEvent, self.hey.increment)

    def test_raise_when_already_unregistered(self):
        self.eb.unregister(PingEvent, self.hey.increment)
        with pytest.raises(LookupError):
            self.eb.unregister(PingEvent, self.hey.increment)


class Test_event_queuing:
    def setup_class(self):
        self.eb = EventBus()

        self.x = 1
        self.first_visited = 'not yet'
        self.second_visited = 'not yet'

        def first(evt):
            assert isinstance(evt, PingEvent)
            assert self.x == 1  # unchanged, sanity check
            self.x += 1
            another = AnotherEvent()
            self.eb.dispatch(another)
            assert self.eb.queue == [another]  # event is in queue
            assert self.x == 2  # assert that 'second' hasn't been called yet
            assert self.second_visited == 'not yet'
            self.first_visited = 'yes'
            # 'second' should be invoked only after this function returns

        def second(evt):
            assert isinstance(evt, AnotherEvent)  # right event is passed in
            assert self.x == 2
            assert self.first_visited == 'yes'
            assert self.second_visited == 'not yet'
            assert self.eb.queue == []
            self.second_visited = 'yes'
            self.x += 1

        self.eb.register(PingEvent, first)
        self.eb.register(AnotherEvent, second)

    def test_dispatch(self):
        self.eb.dispatch(PingEvent())
        assert self.x == 3
        assert self.first_visited == 'yes'
        assert self.second_visited == 'yes'



class Test_callback_order:
    def test_order_after_dispatc(self):
        # after event is dispatched, log_after must be equal to log_before,
        # otherwise queuing is not correct
        self.log_before = []
        self.log_after = []
        self.eb = EventBus()

        class E1(Event): pass
        class E2(Event): pass
        class E3(Event): pass
        class E4(Event): pass
        class E5(Event): pass
        class E6(Event): pass

        def cb1(evt):
            self.log_before += [1]
            self.eb.dispatch(E2())
            self.eb.dispatch(E3())
            self.log_after += [1]

        def cb2(evt):
            self.log_before += [2]
            self.eb.dispatch(E4())
            self.eb.dispatch(E5())
            self.eb.dispatch(E6())
            self.log_after += [2]

        def cb3(evt):
            self.log_before += [3]
            self.log_after += [3]

        def cb4(evt):
            self.log_before += [4]
            self.log_after += [4]

        def cb5(evt):
            self.log_before += [5]
            self.log_after += [5]

        def cb6(evt):
            self.log_before += [6]
            self.log_after += [6]

        self.eb.register(E1, cb1)
        self.eb.register(E2, cb2)
        self.eb.register(E3, cb3)
        self.eb.register(E4, cb4)
        self.eb.register(E5, cb5)
        self.eb.register(E6, cb6)

        assert self.log_before == []
        assert self.log_after == []
        self.eb.dispatch(E1())
        assert self.log_before == [1, 2, 3, 4, 5, 6]
        assert self.log_after == [1, 2, 3, 4, 5, 6]
