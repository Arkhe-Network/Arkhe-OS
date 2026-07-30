--------------------- MODULE projection ---------------------
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Artifact, Substrate, View, Claim

VARIABLES substrate, view, claims

\* Projeção pura
Projection(s) == CHOOSE v \in View : v = view

\* Invariante: projeção nunca altera o substrato
IC3 == Projection(substrate) = view => substrate' = substrate

\* Determinismo
IC4 == \A s, s' \in Substrate :
    s = s' => Projection(s) = Projection(s')

\* Monotonicidade
IC5 == \A s, s' \in Substrate :
    s \subseteq s' => Claims(s) \subseteq Claims(s')

Init ==
    substrate = {}
    /\ view = {}
    /\ claims = {}

Next ==
    \/ Projection
    \/ AddClaim

Projection ==
    view' = Projection(substrate)
    /\ UNCHANGED <<substrate, claims>>

AddClaim ==
    \E c \in Claim :
        claims' = claims \cup {c}
        /\ UNCHANGED <<substrate, view>>

Spec == Init /\ [][Next]_<<substrate, view, claims>>

THEOREM IC3 == Spec => []IC3
THEOREM IC4 == Spec => []IC4
THEOREM IC5 == Spec => []IC5

============================= END MODULE projection =============================