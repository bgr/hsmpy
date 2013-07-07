from hsmpy.eventbus import EventBus, Event
from hsmpy.statemachine import State, CompositeState
from hsmpy.statemachine import Transition as T
from hsmpy.statemachine import InternalTransition as Internal
from hsmpy.statemachine import LocalTransition as Local

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


# transition guards

def foo_eq_0(fsm):
    return fsm.data['foo'] == 0

def foo_eq_1(fsm):
    return fsm.data['foo'] == 1


# transition actions

def set_foo_0(fsm):
    fsm.data['foo'] = 0

def set_foo_1(fsm):
    fsm.data['foo'] = 1

def ignore(fsm):
    pass


# states

class S(CompositeState):
    interests = {
        I: Internal(action=set_foo_0, guard=foo_eq_1),
    }


class S1(CompositeState):
    interests = {
        I: Internal(action=ignore),
    }


class S2(CompositeState):
    interests = {
        I: Internal(guard=foo_eq_0, action=set_foo_1),
    }


class Top(CompositeState): pass
class Final(State): pass
class S11(State): pass
class S21(CompositeState): pass
class S211(State): pass


def create_test_machine():
    """
        Creates a test machine featured in Miro Samek's
        "A Crash Course in UML State Machines":
        http://classes.soe.ucsc.edu/cmpe013/Spring13/LectureNotes/A_Crash_Course_in_UML_State_Machines.pdf
    """
    top = Top()
    final = Final()
    s = S()
    s1 = S1()
    s11 = S11()
    s2 = S2()
    s21 = S21()
    s211 = S211()

    # structure format 1
    top(
        s(
            s1(
                s11 ),
            s2(
                s21(
                    s211 ))),
        final
    )

    # structure format 2
    states = {
        top: {
            s: {
                s1: {
                    s11: {} },
                s2: {
                    s21: {
                        s211: {} }
                }
            },
            final: {}
        }
    }

    # structure format 3 (states and transitions together) - too confusing
    # states = {
    #     'top': CompositeState(
    #     initial=T('s.s2', action=set_foo_0),
    #     trans={
    #         TERMINATE: T('final')},
    #     states={
    #         's': CompositeState(
    #         initial=T('s1.s11'),
    #         trans={
    #             E: Local('s1.s11')},
    #         states={
    #             's1': CompositeState(
    #             initial=T('s11'),
    #             trans={
    #                 A: Loop(),
    #                 B: Local('s11'),
    #                 C: T('s2'),
    #                 D: Local('^s', guard=foo_eq_0, action=set_foo_1),},
    #             states={
    #                 's11': State(
    #                 trans={
    #                     D: Local('^s1', guard=foo_eq_1, action=set_foo_0),
    #                     G: T('^^s.s2.s21.s211'),
    #                     H: Local('^^s'),}
    #             )}
    #             ),
    #             's2': CompositeState(
    #             initial=T('s21.s211'),
    #             trans=[
    #                 C: T('s1'),
    #                 F: T('s1.s11'),],
    #             states={
    #                 's21': CompositeState(
    #                 initial=T('s211'),
    #                 trans={
    #                     A: Loop(),
    #                     B: Local('s211'),}
    #                 states={
    #                     's211': State(
    #                     trans={
    #                         D: Local('^s21'),
    #                         H: Local('^^^s'),}
    #                     )
    #                 },
    #             )]
    #         )]
    #     ),
    #     State('final')
    #     ])

    # structure format take 4
    states = {
        'top': CompositeState({
            's': CompositeState({
                's1': CompositeState({
                    's11': State(),
                }),
                's2': CompositeState({
                    's21': CompositeState({
                        's211': State()
                    })
                })
            }),
            'final': State()
        })
    }

    # transitions format 1
    transitions = {
        'top': {
            'initial': T('s2', action=set_foo_0),
            TERMINATE: T('final')
        },
        's': {
            'initial': T('s11'),
            E: T('s11'),
        },
        's1': {
            'initial': T('s11'),
            A: T('s1'),  # loop into self
            B: Local('s11'),
            C: T('s2'),
            D: Local('s', guard=foo_eq_0, action=set_foo_1)
        },
        's11': {
            D: Local('s1', guard=foo_eq_1, action=set_foo_0),
            G: T('s211'),
            H: Local('s1'),
        },
        's2': {
            C: T('s1'),
            F: T('s11'),
        },
        's21': {
            A: T('s21'),  # loop into self
            B: Local('s211'),
        },
        's211': {
            D: Local('s21'),
            H: Local('s'),
        }
    }

    # transitions format 2
    top.initial(s2, set_foo_0)
    top.trans(
        T(TERMINATE, final)
    )

    s.initial(s11)
    s.trans(
        Local(E, s11),
    )

    s1.initial(s11)
    s1.trans(
        T(A, s1),
        Local(B, s11),
        T(C, s2),
        Local(D, s, guard=foo_eq_0, action=set_foo_1),
    )

    s11.initial(s11)  # raises error
    # check: transition kind local doesn't apply to all, only to parents

    s11.trans(
        Local(D, s1, guard=foo_eq_1, action=set_foo_0),
        T(G, s211),
        Local(H, s1),
    )

    s2.initial(s211)
    s2.trans(
        T(C, s1),
        T(F, s11),
    )

    s21.initial(s211)
    s21.trans(
        T(A, s21),
        Local(B, s211),
    )

    s211.trans(
        Local(D, s21),
        Local(H, s),
    )

    # return top
    return (states, transitions)  # this format is better


class Test_Miro_Samek_machine(object):

    def setup_class(self):
        states, transitions = create_test_machine()
        self.hsm = hsmpy.bundle(states, transitions)
        # now it should check for validity
        assert self.hsm._log == []

    def test_start(self):
        self.hsm.start()
        assert len(self.hsm._log) == 1
        assert self.hsm._log[-1] == ['Top-initial', 'S-entry', 'S2-entry',
                                     'S2-initial', 'S21-entry', 'S211-entry']
        assert self.hsm._current_state == set([Top, S, S2, S21, S211])

    def test_dispatch_1_G(self):
        self.hsm.dispatch(G())
        assert len(self.hsm._log) == 2
        assert self.hsm._log[-1] == ['S21-respond-G', 'S211-exit', 'S21-exit',
                                     'S2-exit', 'S1-entry', 'S1-initial',
                                     's11-entry']
        assert self.hsm._current_state == set([Top, S, S1, S11])

    def test_dispatch_2_I(self):
        self.hsm.dispatch(I())
        assert len(self.hsm._log) == 3
        assert self.hsm._log[-1] == ['S1-internal-I']
        assert self.hsm._current_state == set([Top, S, S1, S11])

    def test_dispatch_3_A(self):
        self.hsm.dispatch(A())
        assert len(self.hsm._log) == 4
        assert self.hsm._log[-1] == ['S1-respond-A', 'S11-exit', 'S1-exit',
                                     'S1-entry', 'S1-initial', 'S11-entry']
        assert self.hsm._current_state == set([Top, S, S1, S11])
