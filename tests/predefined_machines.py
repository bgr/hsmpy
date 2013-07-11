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
        'top': CompositeState({
            'A': CompositeState({
                'B': CompositeState({
                    'C': State(),
                })
            })
        })
    }

    transitions = {
        'top': {
            'initial': T('A'),
        },
        'A': {
            'initial': T('B'),
            A: T('A'),
            AB_loc: Local('B'),
            AB_ex: T('B'),
            AC_loc: Local('C'),
            AC_ex: T('C'),
        },
        'B': {
            'initial': T('C'),
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
