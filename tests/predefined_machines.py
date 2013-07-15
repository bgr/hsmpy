from hsmpy import Event, State, CompositeState, SubmachinesState, Initial
from hsmpy import Transition as T
from hsmpy import InternalTransition as Internal
from hsmpy import LocalTransition as Local



# utility states that log entries and exits into their hsm.data._log dict


def hsmlog(instance, hsm, action):
    if not hasattr(hsm.data, '_log'):
        hsm.data._log = {}
    log = hsm.data._log
    log_id = '{0}_{1}'.format((instance._log_id or instance.name), action)
    if log_id in log:
        log[log_id] += 1
    else:
        log[log_id] = 1


class LoggingState(State):
    def __init__(self, log_id=None):
        super(LoggingState, self).__init__()
        self._log_id = log_id

    def enter(self, evt, hsm):
        hsmlog(self, hsm, 'enter')

    def exit(self, evt, hsm):
        hsmlog(self, hsm, 'exit')


class LoggingCompositeState(CompositeState):
    def __init__(self, states, log_id=None):
        super(LoggingCompositeState, self).__init__(states)
        self._log_id = log_id

    def enter(self, evt, hsm):
        hsmlog(self, hsm, 'enter')

    def exit(self, evt, hsm):
        hsmlog(self, hsm, 'exit')


class LoggingSubmachinesState(SubmachinesState):
    def __init__(self, machines, log_id=None):
        super(LoggingSubmachinesState, self).__init__(machines)
        self._log_id = log_id

    def enter(self, evt, hsm):
        hsmlog(self, hsm, 'enter')

    def exit(self, evt, hsm):
        hsmlog(self, hsm, 'exit')


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


def make_miro_machine():
    """
        Returns (states, transitions) tuple describing the test machine layout
        as featured in Miro Samek's "A Crash Course in UML State Machines":
        http://classes.soe.ucsc.edu/cmpe013/Spring13/LectureNotes/A_Crash_Course_in_UML_State_Machines.pdf

        States in this machine don't have any entry/exit actions assigned,
        that functionality is tested separately.
    """
    # transition guards

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
        'top': LoggingCompositeState({
            's': LoggingCompositeState({
                's1': LoggingCompositeState({
                    's11': LoggingState(),
                }),
                's2': LoggingCompositeState({
                    's21': LoggingCompositeState({
                        's211': LoggingState()
                    })
                })
            }),
            'final': LoggingState()
        })
    }

    transitions = {
        'top': {
            Initial: T('s2', action=set_foo_False),
        },
        's': {
            Initial: T('s11'),
            E: T('s11'),
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


def make_nested_machine():
    """
        Returns (states, transitions) tuple describing the machine layout with
        three nested states A[B[C]] (contained within 'top' state), having
        all 15 combinations of local and external transitions and self-loops:

            * loops: A-(A)->A, B-(B)->B, C-(C)->C
            * inwards: A-(AB)->B, A-(AC)->C, B-(BC)->C (local and external)
            * outwards: C-(CB)->B, C-(CA)->A, B-(BA)->A (local and external)
    """

    states = {
        'top': LoggingCompositeState({
            'A': LoggingCompositeState({
                'B': LoggingCompositeState({
                    'C': LoggingState(),
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


def make_submachines_machine():
    """
        Machine testing "orthogonal" regions functionality aka
        SubmachinesState. It has two children states: *left* and *right*:
        *left* is a SubmachinesState with one submachine, *right* is a
        CompositeState with one simple State and one SubmachinesState with two
        submachines. All three submachines are identical and respond only to A
        and TERMINATE events. Toplevel machine responds to A, B and TERMINATE.
    """
    submachines = []
    for i in range(3):  # make a couple of identical machines
        sub_states = {
            'top': LoggingCompositeState({
                'start': LoggingState(),
                'right': LoggingState(),
                'final': LoggingState(),
            })
        }
        sub_trans = {
            'top': {
                Initial: T('start'),
                TERMINATE: Local('final'),
            },
            'left': {
                A: T('right'),
            },
            'right': {
                A: Local('start'),  # should fail validation
            }
        }
        submachines += [(sub_states, sub_trans)]

    states = {
        'top': LoggingCompositeState({
            'left': LoggingSubmachinesState([
                submachines[0],
            ]),
            'right': LoggingCompositeState({
                'dumb': LoggingState(),
                'subs': LoggingSubmachinesState([
                    submachines[1],
                    submachines[2],
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
