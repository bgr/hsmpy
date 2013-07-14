Hierarchical State Machine for Python
=====================================

**!! In development !!**

Aim of this project is to provide easy way to implement behavior of reactive
systems.

Event handling logic is the weakest point of reactive systems (programs such as
GUI applications and games), and is the usual cause of bugs in such programs,
along with code bloat. Textbook way to alleviate that is by using State pattern
or some form of Finite state machine, however they quickly prove to be
under-powered for even moderately complex behavior due to their limited flat
nature. Hierarchical state machines aim to provide solution, and this project
implements some of the features proposed by [UML state machine][UML_wiki].


Currently supported features
----------------------------

* composite states
* local and external transitions
* internal transitions
* event queuing
* validation of machine's structure, with checks for:
    * machine having single top (container) state
    * unreachable states
    * multiple occurrences of same State object instance
    * multiple states with same name
    * transitions that start from or point to nonexistent states
    * composite states with missing or invalid initial transitions
    * invalid local transitions


Missing HSM features
--------------------

* orthogonal regions
    * forks and joins
    * final pseudostate
* deferred events
* conditional junctions
* history pseudostate (probably won't implement)

A big warning should be put here that this implementation is totally not
thread-safe (and won't be). That shouldn't be a problem for GUI applications
since all widget toolkits in use are single-threaded AFAIK.


TODOs
-----

* documentation and examples
* validation check that initial condition doesn't have a guard
* maybe change initial transition to be LocalTransition
* what happens when same state has both internal and outgoing transition for
  same event? maybe internal transitions should be defined in trans dict too
* State and Transition are inconsistent, one defines actions as methods, other
  takes them as arguments; maybe switch to namedtuples if it proves to be
  reasonable
* HSM should'n modify states in states dict, make copies instead
* tests for hsm._validate
* declaring events is kinda ugly


Setting up
==========

    python bootstrap.py
    bin/buildout

Running tests
-------------

    bin/py.test tests/



[UML_wiki]: http://en.wikipedia.org/wiki/UML_state_machine
