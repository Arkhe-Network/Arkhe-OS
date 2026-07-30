--------------------- MODULE substrate ---------------------
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS
    \* Tipos básicos
    Artifact,
    Evidence,
    Assertion,
    Claim,
    Version

VARIABLES
    artifacts,          \* Conjunto de Artifacts
    evidence_registry,  \* Conjunto de Evidências
    assertions,         \* Conjunto de Assertions
    claims,             \* Conjunto de Claims
    version_graph,      \* Grafo de versões
    substrate           \* Estado atual do substrato

\* ────────────────────────────────────────────────────────────────
\* IC1 — Canonical Identity
\* Cada Artifact possui exatamente uma identidade canônica.
\* ────────────────────────────────────────────────────────────────

CanonicalId(a) == CHOOSE id : id \in DOMAIN artifacts /\ artifacts[id] = a

IC1 == \A a, b \in artifacts :
    CanonicalId(a) = CanonicalId(b) => a = b

\* ────────────────────────────────────────────────────────────────
\* IC2 — Provenance Preservation
\* Toda Assertion referencia apenas evidências existentes.
\* ────────────────────────────────────────────────────────────────

EvidenceOf(a) == { e \in evidence_registry : e \in a.evidence }

IC2 == \A a \in assertions :
    EvidenceOf(a) \subseteq evidence_registry

\* ────────────────────────────────────────────────────────────────
\* IC3 — Projection Purity
\* Projeção nunca altera o substrato.
\* ────────────────────────────────────────────────────────────────

Projection(s) == VIEW(s)  \* função abstrata

IC3 == Projection(substrate) = view \* não modifica substrate

\* ────────────────────────────────────────────────────────────────
\* IC4 — Determinismo
\* Mesmo substrato → mesma projeção.
\* ────────────────────────────────────────────────────────────────

IC4 == \A s1, s2 \in Substrate :
    s1 = s2 => Projection(s1) = Projection(s2)

\* ────────────────────────────────────────────────────────────────
\* IC5 — Monotonicidade
\* Adicionar informação nunca invalida evidências.
\* ────────────────────────────────────────────────────────────────

IC5 == \A s, s' \in Substrate :
    s \subseteq s' => Claims(s) \subseteq Claims(s')

\* ────────────────────────────────────────────────────────────────
\* IC6 — Referential Integrity
\* Nenhuma Assertion referencia Artifact inexistente.
\* ────────────────────────────────────────────────────────────────

References(a) == { x \in Artifact : x \in a.references }

IC6 == \A a \in assertions :
    References(a) \subseteq artifacts

\* ────────────────────────────────────────────────────────────────
\* IC7 — Version Linearity
\* Versões formam DAG (acíclico).
\* ────────────────────────────────────────────────────────────────

IC7 == Acyclic(version_graph)

\* ────────────────────────────────────────────────────────────────
\* IC8 — Temporal Consistency
\* Nenhuma Evidence pode existir antes do Artifact.
\* ────────────────────────────────────────────────────────────────

TimestampOf(e) == e.timestamp

IC8 == \A e \in evidence_registry :
    TimestampOf(e) >= TimestampOf(e.artifact)

\* ────────────────────────────────────────────────────────────────
\* IC9 — Trust Monotonicity
\* Adicionar evidências nunca reduz confiança.
\* ────────────────────────────────────────────────────────────────

Confidence(c) == c.confidence

IC9 == \A s, s' \in Substrate :
    s \subseteq s' => Confidence(s) <= Confidence(s')

\* ────────────────────────────────────────────────────────────────
\* IC10 — Audit Completeness
\* Todo Claim pode ser reconstruído.
\* ────────────────────────────────────────────────────────────────

Reconstruction(c) == CHOOSE a \in assertions : a.claim = c

IC10 == \A c \in claims :
    Reconstruction(c) \in assertions

\* ────────────────────────────────────────────────────────────────
\* Estado Inicial
\* ────────────────────────────────────────────────────────────────

Init ==
    artifacts = {}
    /\ evidence_registry = {}
    /\ assertions = {}
    /\ claims = {}
    /\ version_graph = {}
    /\ substrate = {}

\* ────────────────────────────────────────────────────────────────
\* Transições
\* ────────────────────────────────────────────────────────────────

Next ==
    \/ AddArtifact
    \/ AddEvidence
    \/ AddAssertion
    \/ AddClaim
    \/ Project

AddArtifact ==
    \E a \in Artifact :
        artifacts' = artifacts \cup {a}
        /\ UNCHANGED <<evidence_registry, assertions, claims, version_graph, substrate>>

AddEvidence ==
    \E e \in Evidence :
        evidence_registry' = evidence_registry \cup {e}
        /\ UNCHANGED <<artifacts, assertions, claims, version_graph, substrate>>

AddAssertion ==
    \E a \in Assertion :
        assertions' = assertions \cup {a}
        /\ UNCHANGED <<artifacts, evidence_registry, claims, version_graph, substrate>>

AddClaim ==
    \E c \in Claim :
        claims' = claims \cup {c}
        /\ UNCHANGED <<artifacts, evidence_registry, assertions, version_graph, substrate>>

Project ==
    \E v \in View :
        substrate' = substrate
        /\ UNCHANGED <<artifacts, evidence_registry, assertions, claims, version_graph>>

Spec == Init /\ [][Next]_<<artifacts, evidence_registry, assertions, claims, version_graph, substrate>>

THEOREM IC1 == Spec => []IC1
THEOREM IC2 == Spec => []IC2
THEOREM IC3 == Spec => []IC3
THEOREM IC4 == Spec => []IC4
THEOREM IC5 == Spec => []IC5
THEOREM IC6 == Spec => []IC6
THEOREM IC7 == Spec => []IC7
THEOREM IC8 == Spec => []IC8
THEOREM IC9 == Spec => []IC9
THEOREM IC10 == Spec => []IC10

============================= END MODULE substrate =============================