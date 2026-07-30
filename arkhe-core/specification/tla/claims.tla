--------------------- MODULE claims ---------------------
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Claim, Assertion, Evidence

VARIABLES claims, assertions, evidence_registry

\* IC2 — Provenance Preservation
IC2 == \A a \in assertions :
    EvidenceOf(a) \subseteq evidence_registry

\* IC10 — Audit Completeness
IC10 == \A c \in claims :
    \E a \in assertions : a.claim = c

Init ==
    claims = {}
    /\ assertions = {}
    /\ evidence_registry = {}

Next ==
    \/ AddClaim
    \/ AddAssertion
    \/ AddEvidence

AddClaim ==
    \E c \in Claim :
        claims' = claims \cup {c}
        /\ UNCHANGED <<assertions, evidence_registry>>

AddAssertion ==
    \E a \in Assertion :
        assertions' = assertions \cup {a}
        /\ UNCHANGED <<claims, evidence_registry>>

AddEvidence ==
    \E e \in Evidence :
        evidence_registry' = evidence_registry \cup {e}
        /\ UNCHANGED <<claims, assertions>>

Spec == Init /\ [][Next]_<<claims, assertions, evidence_registry>>

THEOREM IC2 == Spec => []IC2
THEOREM IC10 == Spec => []IC10

============================= END MODULE claims =============================