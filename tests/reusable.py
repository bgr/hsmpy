import hsmpy
from hsmpy import Initial, Event


def get_state(kind, name, states):
    assert False, "make logging"
    st = hsmpy.State(states)
    st.name = name
    st.kind = kind
    return st

orthogonal = lambda name, states: get_state('orthogonal', name, states)
composite = lambda name, states: get_state('composite', name, states)
leaf = lambda name: get_state('leaf', name, [])


class MockHSM(object):
    def __init__(self):
        class Dump(object):
            pass
        self.data = Dump()


def log(hsm, log_entry):
    if not hasattr(hsm.data, '_log'):
        hsm.data._log = []
    hsm.data._log += [log_entry]


class LoggingState(hsmpy.State):
    """Utility state that logs entries and exits into hsm.data._log dict."""
    def __init__(self, states=None, on_enter=None, on_exit=None, log_id=None):
        super(LoggingState, self).__init__(states, on_enter, on_exit)
        self._log_id = log_id

    def enter(self, hsm):
        log(hsm, '{0}-entry'.format(self._log_id or self.name))

    def exit(self, hsm):
        log(hsm, '{0}-exit'.format(self._log_id or self.name))


class LoggingT(hsmpy.T):
    def __call__(self, evt, hsm):
        log(hsm, '{0}-{1}'.format(hsmpy.State.sig_to_name(self.source),
                                  evt.__class__.__name__,))
        super(LoggingT, self).__call__(evt, hsm)


class LoggingLocal(hsmpy.LocalTransition):
    def __call__(self, evt, hsm):
        log(hsm, '{0}-{1}'.format(hsmpy.State.sig_to_name(self.source),
                                  evt.__class__.__name__,))
        super(LoggingLocal, self).__call__(evt, hsm)


class LoggingInternal(hsmpy.InternalTransition):
    def __call__(self, evt, hsm):
        log(hsm, '{0}-{1}'.format(hsmpy.State.sig_to_name(self.source),
                                  evt.__class__.__name__,))
        super(LoggingInternal, self).__call__(evt, hsm)


class LoggingChoice(hsmpy.ChoiceTransition):
    def __call__(self, evt, hsm):
        log(hsm, '{0}-{1}'.format(hsmpy.State.sig_to_name(self.source),
                                  evt.__class__.__name__,))
        super(LoggingChoice, self).__call__(evt, hsm)


regular = [hsmpy.State, hsmpy.T, hsmpy.Local, hsmpy.Internal, hsmpy.Choice]
logging = [LoggingState, LoggingT, LoggingLocal, LoggingInternal,
           LoggingChoice]


# events
class A(Event): pass
class B(Event): pass
class C(Event): pass
class D(Event): pass
class E(Event): pass
class F(Event): pass
class G(Event): pass
class H(Event): pass
class I(Event): pass
class TERMINATE(Event): pass


def make_miro_machine(use_logging):
    """
        Returns (states, transitions) tuple describing the test machine layout
        as featured in Miro Samek's "A Crash Course in UML State Machines":
        http://classes.soe.ucsc.edu/cmpe013/Spring13/LectureNotes/A_Crash_Course_in_UML_State_Machines.pdf

        States in this machine don't have any entry/exit actions assigned,
        that functionality is tested separately.
    """
    # transition guards

    S, T, Local, Internal, Choice = logging if use_logging else regular

    def foo_is_False(evt, hsm):
        return hsm.data.foo is False

    def foo_is_True(evt, hsm):
        return hsm.data.foo is True

    # transition actions

    def set_foo_False(evt, hsm):
        hsm.data.foo = False

    def set_foo_True(evt, hsm):
        hsm.data.foo = True

    def do_nothing(evt, hsm):
        pass


    states = {
        'top': S({
            's': S({
                's1': S({
                    's11': S(),
                }),
                's2': S({
                    's21': S({
                        's211': S()
                    })
                })
            }),
            'final': S()
        })
    }

    transitions = {
        'top': {
            Initial: T('s2', action=set_foo_False),
        },
        's': {
            Initial: T('s11'),
            E: Local('s11'),
            TERMINATE: T('final'),
            I: Internal(guard=foo_is_True, action=set_foo_False),
        },
        's1': {
            Initial: T('s11'),
            A: T('s1'),  # loop into self
            B: Local('s11'),
            C: T('s2'),
            D: Local('s', guard=foo_is_False, action=set_foo_True),
            F: T('s211'),
            I: Internal(action=do_nothing),
        },
        's11': {
            D: Local('s1', guard=foo_is_True, action=set_foo_False),
            G: T('s211'),
            H: Local('s1'),
        },
        's2': {
            Initial: T('s211'),
            C: T('s1'),
            F: T('s11'),
            I: Internal(guard=foo_is_False, action=set_foo_True),
        },
        's21': {
            Initial: T('s211'),
            A: T('s21'),  # loop into self
            B: Local('s211'),
            G: T('s1'),
        },
        's211': {
            D: Local('s21'),
            H: Local('s'),
        }
    }

    return (states, transitions)



class AB_ex(Event): pass
class AC_ex(Event): pass
class BC_ex(Event): pass
class AB_loc(Event): pass
class AC_loc(Event): pass
class BC_loc(Event): pass
class BA_ex(Event): pass
class CA_ex(Event): pass
class CB_ex(Event): pass
class BA_loc(Event): pass
class CA_loc(Event): pass
class CB_loc(Event): pass


def make_nested_machine(use_logging):
    """
        Returns (states, transitions) tuple describing the machine layout with
        three nested states A[B[C]] (contained within 'top' state), having
        all 15 combinations of local and external transitions and self-loops:

            * loops: A-(A)->A, B-(B)->B, C-(C)->C
            * inwards: A-(AB)->B, A-(AC)->C, B-(BC)->C (local and external)
            * outwards: C-(CB)->B, C-(CA)->A, B-(BA)->A (local and external)
    """


    S, T, Local, Internal, Choice = logging if use_logging else regular

    states = {
        'top': S({
            'A': S({
                'B': S({
                    'C': S(),
                })
            })
        })
    }

    transitions = {
        'top': {
            Initial: T('A'),
        },
        'A': {
            Initial: T('B'),
            A: T('A'),
            AB_loc: Local('B'),
            AB_ex: T('B'),
            AC_loc: Local('C'),
            AC_ex: T('C'),
        },
        'B': {
            Initial: T('C'),
            B: T('B'),
            BC_loc: Local('C'),
            BC_ex: T('C'),
            BA_loc: Local('A'),
            BA_ex: T('A'),
        },
        'C': {
            C: T('C'),
            CB_loc: Local('B'),
            CB_ex: T('B'),
            CA_loc: Local('A'),
            CA_ex: T('A'),
        }
    }

    return (states, transitions)


def make_submachines_machine(use_logging):
    """
        Machine for testing "orthogonal" regions functionality aka
        submachines. It has two children states: *left* and *right*:
        *left* is an orthogonal state with one submachine, *right* is a
        composite state with one simple State and one orthogonal state with two
        submachines. All three submachines are identical and respond only to A
        and TERMINATE events. Toplevel machine responds to A, B and TERMINATE.
    """

    S, T, Local, Internal, Choice = logging if use_logging else regular

    sub_states = {
        'top': S({
            'start': S(),
            'right': S(),
            'final': S(),
        })
    }
    sub_trans = {
        'top': {
            Initial: T('start'),
            TERMINATE: Local('final'),
        },
        'start': {
            A: T('right'),
        },
        'right': {
            A: T('start'),
        }
    }

    states = {
        'top': S({
            'left': S([
                (sub_states, sub_trans),
            ]),
            'right': S({
                'dumb': S(),
                'subs': S([
                    (sub_states, sub_trans),
                    (sub_states, sub_trans),
                ]),
            }),
        })
    }

    trans = {
        'top': {
            Initial: T('left'),
        },
        'left': {
            A: T('right'),
            B: T('right'),
        },
        'right': {
            Initial: T('subs'),
            A: T('left'),  # dumb will ignore A thus transitioning to left
        },
        'subs': {
            A: T('dumb'),  # shouldn't fire if submachine responds
        }
    }

    return (states, trans)



def make_submachines_async_machine(use_logging):
    """ Machine for testing submachine behavior when not all submachines
        respond to event. Returns machine with two submachines, where one
        responds to A, and other responds to B.
    """

    S, T, Local, Internal, Choice = logging if use_logging else regular

    sub_states = {
        'top': S({
            'left': S(),
            'right': S(),
        })
    }

    sub_1_trans = {
        'top': {
            Initial: T('left'),
        },
        'left': {
            A: T('right'),
        },
    }

    sub_2_trans = {
        'top': {
            Initial: T('left'),
        },
        'left': {
            B: T('right'),
        },
    }


    states = {
        'top': S({
            'subs': S([
                (sub_states, sub_1_trans),
                (sub_states, sub_2_trans),
            ])
        })
    }

    trans = {
        'top': {
            Initial: T('subs'),
        }
    }

    return (states, trans)


def make_choice_machine(use_logging):
    """
        Machine for testing Choice transitions.
        Returns machine with a pair of nested states A[B[C]] D[E[F]] (contained
        within 'top' state), where A, B and C have Choice transitions to all
        states including self. Initial transitions are also Choice. There are
        variations in how transitions are specified, check the source.
    """

    S, T, Local, Internal, Choice = logging if use_logging else regular

    states = {
        'top': S({
            'A': S({
                'B': S({
                    'C': S(),
                })
            }),
            'D': S({
                'E': S({
                    'F': S(),
                })
            })
        })
    }

    init_key = lambda _, hsm: hsm.data.foo

    transitions = {
        'top': {
            Initial: Choice({
                1: 'A', 2: 'B', 3: 'C',
                4: 'D', 5: 'E', 6: 'F'}, key=init_key, default='C')
        },
        'A': {
            Initial: Choice({ 2: 'B', 3: 'C'}, key=init_key, default='C'),
            A: Choice({
                0: 'top',
                1: 'A', 2: 'B', 3: 'C',
                4: 'D', 5: 'E', 6: 'F'}, default='E'),
        },
        'B': {
            Initial: Choice({ 3: 'C'}, key=init_key, default='C'),
            A: Choice({
                0: 'top',
                1: 'A', 2: 'B', 3: 'C',
                4: 'D', 5: 'E', 6: 'F'},
                key=lambda e, h: e.data / 10.0, default='D'),  # custom key
        },
        'C': {
            A: Choice({
                0: 'top',
                1: 'A', 2: 'B', 3: 'C',
                4: 'D', 5: 'E', 6: 'F'}),  # no default
        },
        'D': {
            Initial: T('F'),
            A: T('B'),
        },
        'E': {
            Initial: T('F'),
        },
    }

    return (states, transitions)
