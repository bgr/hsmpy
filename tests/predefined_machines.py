from hsmpy import Event, State, CompositeState
from hsmpy import Transition as T
from hsmpy import InternalTransition as Internal
from hsmpy import LocalTransition as Local

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

    def foo_is_False(hsm):
        return hsm.data.foo is False

    def foo_is_True(hsm):
        return hsm.data.foo is True

    # transition actions

    def set_foo_False(hsm):
        hsm.data.foo = False

    def set_foo_True(hsm):
        hsm.data.foo = True

    def do_nothing(hsm):
        pass

    # states with additional behavior
    class S(CompositeState):
        interests = {
            I: Internal(guard=foo_is_True, action=set_foo_False),
        }


    class S1(CompositeState):
        interests = {
            I: Internal(action=do_nothing),
        }


    class S2(CompositeState):
        interests = {
            I: Internal(guard=foo_is_False, action=set_foo_True),
        }


    states = {
        'top': CompositeState({
            's': S({
                's1': S1({
                    's11': State(),
                }),
                's2': S2({
                    's21': CompositeState({
                        's211': State()
                    })
                })
            }),
            'final': State()
        })
    }

    transitions = {
        'top': {
            'initial': T('s2', action=set_foo_False),
        },
        's': {
            'initial': T('s11'),
            E: T('s11'),
            TERMINATE: T('final'),
        },
        's1': {
            'initial': T('s11'),
            A: T('s1'),  # loop into self
            B: Local('s11'),
            C: T('s2'),
            D: Local('s', guard=foo_is_False, action=set_foo_True),
            F: T('s211'),
        },
        's11': {
            D: Local('s1', guard=foo_is_True, action=set_foo_False),
            G: T('s211'),
            H: Local('s1'),
        },
        's2': {
            'initial': T('s211'),
            C: T('s1'),
            F: T('s11'),
        },
        's21': {
            'initial': T('s211'),
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
