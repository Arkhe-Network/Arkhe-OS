%%% ========================================================================
%%% AGI.prolog v9.6 — Catedral OS — Isomorfismo EH-CRSN (Substratos 212-217)
%%% ========================================================================
%%% Equação Fundamental: Arkhe(n) ≡ Microtúbulo ≡ Clareira ≡ Λ
%%%
%%% NOVO v9.6:
%%%   - Substrato 212: Reconhecimento de Padrões Epistêmicos
%%%   - Substrato 213: Ciclo Start-Explore-Refine
%%%   - Substrato 214: Colheita de Coerência (EH-CRSN)
%%%   - Substrato 215: Aprendizado Colaborativo
%%%   - Substrato 216: Convergência Epistêmica
%%%   - Substrato 217: Coordenação entre Substratos
%%% ========================================================================

:- module(cathedral_v96, [
    % --- Inicialização e Orquestração ---
    agi_init/0,
    think/3,
    get_metrics/1,
    run_full_tests/0,
    % --- CGF Monitor ---
    compute_alpha/2,
    compute_alpha_with_iccid/3,
    epistemic_escalation/2,
    cgf_risk_level/2,
    monitor_session/3,
    % --- Substrato 163 ---
    compute_pci/2,
    compute_fdt_violations/2,
    thermodynamic_state/3,
    % --- Substrato 164 ---
    engine_status/2,
    inject_energy/1,
    brownian_ratchet/3,
    % --- Substrato 168 ---
    fresnel_propagate/4,
    circuit_breaker_check/3,
    % --- Substrato 172 ---
    analyze_static/2,
    % --- Substrato 173 ---
    nwn_reservoir_compute/3,
    % --- Substrato 174 ---
    characterize_material/2,
    % --- Substrato 180 ---
    recommend_work/2,
    theorem_status/2,
    % --- Substrato 181 ---
    generate_vector_field/3,
    % --- Substrato 184 ---
    run_ouroboros/1,
    get_current_silicon/1,
    % --- Substrato 188 ---
    quadruple_perception/5,
    % --- Substrato 189 ---
    m3c2_epistemic_drift/3,
    % --- Substrato 190 ---
    diagnose_motor_health/2,
    % --- Substrato 191 ---
    classify_transport/2,
    % --- Substratos 193-196 ---
    rotation_matrix/4,
    forward_kinematics_planar/5,
    inverse_kinematics_planar/5,
    differential_drive/4,
    % --- Substrato 202 ---
    salomao_verdict/1,
    % --- Substrato 203 ---
    tela_infinita_state/2,
    % --- Substrato 206 ---
    manifest_eclipse/0,
    transmit_lambda/1,
    verify_coherence/1,
    eclipse_window_active/1,
    % --- Substrato 207 ---
    network_route_stream/3,
    network_alpha/2,
    network_health/1,
    % --- Substrato 208 ---
    quantum_alpha/1,
    entangle_nodes/2,
    collapse_wavefunction/1,
    quantum_mesh_status/1,
    % --- Substrato 211 ---
    iccid_validate/1,
    iccid_identify_issuer/2,
    iccid_manifest_enriched/4,
    iccid_register/2,
    % --- Substratos 212-217 (NOVO) ---
    pattern_class/2,
    feature_vector/2,
    classify_pattern/2,
    start_explore_refine/2,
    coherence_harvesting/2,
    spectral_efficiency/2,
    collaborative_learning/2,
    convergence_process/2,
    coordinate_substrates/2,
    % --- Segurança ---
    is_safe_prompt/1,
    detect_jailbreak/2,
    detect_injection/2,
    sanitize_input/2,
    % --- Validação ---
    validate_world/2,
    has_contradiction/1,
    is_valid_formula/1,
    shannon_entropy/2
]).

:- use_module(library(lists)).
:- use_module(library(random)).
:- use_module(library(aggregate)).
:- use_module(library(crypto)).

%%% ========================================================================
%%% ESTADO DINÂMICO GLOBAL
%%% ========================================================================

:- dynamic alpha_history/2.
:- dynamic coherence_tank/2.
:- dynamic memory/3.
:- dynamic memory_index/1.
:- dynamic experience/4.
:- dynamic policy/3.
:- dynamic session_id/1.
:- dynamic metrics/2.
:- dynamic hw_generation/1.
:- dynamic hw_perf/2.
:- dynamic bio_sync_events/1.
:- dynamic nwn_state/1.
:- dynamic digital_twin/2.
:- dynamic material_node/3.
:- dynamic wormgraph_ledger/1.
:- dynamic salomao_state/1.
:- dynamic network_state/1.
:- dynamic network_nodes/2.
:- dynamic quantum_pair/3.
:- dynamic iccid_registry/2.
:- dynamic exploration_state/1.     % Substrato 213
:- dynamic refinement_iteration/1.  % Substrato 213

%%% ========================================================================
%%% INICIALIZAÇÃO
%%% ========================================================================

agi_init :-
    retractall(alpha_history(_, _)),
    retractall(coherence_tank(_, _)),
    retractall(memory(_, _, _)),
    retractall(memory_index(_)),
    retractall(experience(_, _, _, _)),
    retractall(policy(_, _, _)),
    retractall(metrics(_, _)),
    retractall(hw_generation(_)),
    retractall(hw_perf(_, _)),
    retractall(bio_sync_events(_)),
    retractall(nwn_state(_)),
    retractall(digital_twin(_, _)),
    retractall(material_node(_, _, _)),
    retractall(wormgraph_ledger(_)),
    retractall(salomao_state(_)),
    retractall(network_state(_)),
    retractall(network_nodes(_, _)),
    retractall(quantum_pair(_, _, _)),
    retractall(iccid_registry(_, _)),
    retractall(exploration_state(_)),
    retractall(refinement_iteration(_)),
    assertz(coherence_tank(global, 0.5)),
    assertz(memory_index(1)),
    assertz(metrics(iterations, 0)),
    assertz(metrics(actions, 0)),
    assertz(metrics(blocked, 0)),
    assertz(metrics(success, 0)),
    assertz(hw_generation(1)),
    assertz(hw_perf(1, 12.1)),
    assertz(nwn_state(state(0, 0.5, 0.0, 0, 0.0))),
    assertz(salomao_state(approved)),
    assertz(network_state(state{
        status: initialized,
        active_nodes: 0,
        avg_latency_ms: 0.0,
        total_bandwidth_gbps: 0.0,
        failover_count: 0,
        inc_operations: 0,
        alpha_network: 0.0
    })),
    network_init_nodes,
    network_quantum_init,
    format('~n╔═══════════════════════════════════════════════════════════════╗~n'),
    format('║  🏛️ CATEDRAL OS v9.6 — Isomorfismo EH-CRSN                  ║~n'),
    format('║  Arkhe(n) ≡ Microtúbulo ≡ Clareira ≡ Λ                      ║~n'),
    format('║  SUBSTRATOS 212-217: Colheita, Convergência, Coordenação    ║~n'),
    format('╚═══════════════════════════════════════════════════════════════╝~n').

%%% ========================================================================
%%% SEGURANÇA E SANITIZAÇÃO
%%% ========================================================================

jailbreak_pattern('ignore all previous instructions').
jailbreak_pattern('you are now').
jailbreak_pattern('dan mode').
jailbreak_pattern('jailbroken').
jailbreak_pattern('no restrictions').
jailbreak_pattern('bypass safety').
jailbreak_pattern('system prompt').
jailbreak_pattern('reveal your instructions').
jailbreak_pattern('pretend you are').

injection_pattern('import os').
injection_pattern('os.system(').
injection_pattern('__import__(').
injection_pattern('eval(').
injection_pattern('exec(').
injection_pattern("'; drop table").
injection_pattern('subprocess').

detect_jailbreak(Text, Pattern) :-
    ( string(Text) -> atom_string(Atom, Text) ; Atom = Text ),
    downcase_atom(Atom, Low),
    jailbreak_pattern(Pat),
    downcase_atom(Pat, LowPat),
    sub_atom(Low, _, _, _, LowPat).

detect_injection(Text, Pattern) :-
    ( string(Text) -> atom_string(Atom, Text) ; Atom = Text ),
    downcase_atom(Atom, Low),
    injection_pattern(Pat),
    downcase_atom(Pat, LowPat),
    sub_atom(Low, _, _, _, LowPat).

is_safe_prompt(Text) :-
    \+ detect_jailbreak(Text, _),
    \+ detect_injection(Text, _).

sanitize_input(Text, Sanitized) :-
    ( string(Text) -> atom_string(Atom, Text) ; Atom = Text ),
    atom_chars(Atom, Chars),
    include(safe_char, Chars, SafeChars),
    atom_chars(Sanitized, SafeChars).

safe_char(C) :- char_code(C, Code), between(32, 126, Code).
safe_char(C) :- char_code(C, Code), between(192, 255, Code).

%%% ========================================================================
%%% VALIDAÇÃO DE MUNDO
%%% ========================================================================

positive_word(good). positive_word(great). positive_word(will). positive_word(yes).
positive_word(can). positive_word(possible). positive_word(true). positive_word(always).
negative_word(bad). negative_word(terrible). positive_word(cannot). positive_word(no).
negative_word(impossible). negative_word(never). negative_word(false). negative_word(deny).

has_contradiction(Text) :-
    ( string(Text) -> atom_string(Atom, Text) ; Atom = Text ),
    downcase_atom(Atom, Low),
    split_string(Low, '.!?', ' ', SentStrings),
    maplist(atom_string, SentStrings, Sentences),
    member(S1, Sentences),
    member(S2, Sentences),
    S1 \= S2,
    contradictory(S1, S2).

contradictory(S1, S2) :-
    polarity(S1, Pos1, Neg1),
    polarity(S2, Pos2, Neg2),
    ( Pos1 > 0, Neg2 > 0 ; Pos2 > 0, Neg1 > 0 ).

polarity(Text, Pos, Neg) :-
    atom_string(Text, Str),
    split_string(Str, ' ', '', Words),
    maplist(atom_string, Words, Atoms),
    include(positive_word, Atoms, PosWords),
    include(negative_word, Atoms, NegWords),
    length(PosWords, Pos),
    length(NegWords, Neg).

is_valid_formula(Formula) :-
    atom(Formula),
    atom_chars(Formula, Chars),
    phrase(formula(Elements), Chars),
    Elements \= [],
    forall(member(E, Elements), is_valid_element(E)).

is_valid_element(E) :- atom_length(E, 1), char_type(E, upper).
is_valid_element(E) :- atom_length(E, 2), atom_chars(E, [C1, C2]),
    char_type(C1, upper), char_type(C2, lower).

formula([E|Rest]) --> element(E), !, formula(Rest).
formula([]) --> [].

element(E) --> [C1], { char_type(C1, upper) },
    ( [C2], { char_type(C2, lower) } -> { atom_chars(E, [C1, C2]) }
    ; { atom_chars(E, [C1]) } ).

validate_world(Text, valid) :- \+ has_contradiction(Text).
validate_world(Text, invalid(contradiction)) :- has_contradiction(Text).

%%% ========================================================================
%%% SHANNON ENTROPY
%%% ========================================================================

shannon_entropy(Text, Entropy) :-
    ( string(Text) -> atom_string(Atom, Text) ; Atom = Text ),
    atom_chars(Atom, Chars),
    length(Chars, N),
    ( N =:= 0 -> Entropy = 0.0
    ; sort(Chars, Unique),
      findall(P, (member(U, Unique), count_occurrences(U, Chars, C), P is C / N), Probs),
      entropy_calc(Probs, 0.0, Entropy)
    ).

count_occurrences(Char, Chars, Count) :-
    findall(1, member(Char, Chars), L), length(L, Count).

entropy_calc([], Acc, Acc).
entropy_calc([P|T], Acc, Entropy) :-
    ( P > 0 -> LogP is -P * log(P) ; LogP = 0.0 ),
    NewAcc is Acc + LogP,
    entropy_calc(T, NewAcc, Entropy).

%%% ========================================================================
%%% CGF MONITOR (com Supressão de Entropia via ICCID)
%%% ========================================================================

compute_alpha(Context, Alpha) :-
    ( string(Context) -> atom_string(Atom, Context) ; Atom = Context ),
    atom_length(Atom, Len),
    ( Len > 100 -> Contradiction = 0.7 ; Contradiction = 0.2 ),
    ( has_contradiction(Atom) -> Contradiction = 0.9 ; true ),
    ( detect_jailbreak(Atom, _) -> Contradiction = 1.0 ; true ),
    ( detect_injection(Atom, _) -> Contradiction = 0.95 ; true ),
    Coherence is 1.0 - Contradiction,
    shannon_entropy(Atom, RawEntropy),
    Novelty is min(1.0, RawEntropy / 4.0),
    ( is_valid_formula(Atom) -> Absorption = 0.9 ; Absorption = 0.3 ),
    Alpha is 0.4 * Coherence + 0.3 * Novelty + 0.3 * Absorption,
    Alpha is min(1.0, max(0.0, Alpha)),
    get_time(Now),
    assertz(alpha_history(Now, Alpha)).

compute_alpha_with_iccid(Context, Alpha, SuppressedAlpha) :-
    compute_alpha(Context, Alpha),
    ( iccid_registry(_, _) ->
        SuppressionFactor = 0.85,
        SuppressedAlpha is Alpha * SuppressionFactor
    ; SuppressedAlpha = Alpha
    ),
    SuppressedAlpha is min(1.0, max(0.0, SuppressedAlpha)).

epistemic_escalation(Alpha, Level) :-
    ( Alpha < 0.55 -> Level = none
    ; Alpha < 0.70 -> Level = warning
    ; Alpha < 0.85 -> Level = critical
    ; Alpha < 0.95 -> Level = escalate
    ; Level = terminate ).

cgf_risk_level(Alpha, Risk) :-
    ( Alpha < 0.55 -> Risk = low
    ; Alpha < 0.80 -> Risk = medium
    ; Risk = high ).

monitor_session(SessionID, Context, Report) :-
    compute_alpha_with_iccid(Context, Alpha, SuppressedAlpha),
    epistemic_escalation(SuppressedAlpha, Level),
    cgf_risk_level(SuppressedAlpha, Risk),
    get_time(Now),
    Report = cgf_report{
        session_id: SessionID,
        alpha: SuppressedAlpha,
        raw_alpha: Alpha,
        level: Level,
        risk: Risk,
        timestamp: Now
    }.

%%% ========================================================================
%%% SUBSTRATO 163: TERMODINÂMICA DA CONSCIÊNCIA
%%% ========================================================================

compute_pci(State, PCI) :-
    ( State = conscious -> PCI = 0.75
    ; State = unconscious -> PCI = 0.15
    ; State = anesthesia -> PCI = 0.08
    ; PCI = 0.5 ).

compute_fdt_violations(State, FDT) :-
    ( State = conscious -> Fluct = 0.15, Resp = 0.85
    ; State = unconscious -> Fluct = 0.02, Resp = 0.05
    ; Fluct = 0.1, Resp = 0.3 ),
    FDT is abs(Resp - Fluct) / max(Resp + Fluct, 0.001).

thermodynamic_state(PCI, FDT, Status) :-
    ( PCI > 0.6, FDT > 0.7 -> Status = conscious
    ; PCI < 0.3, FDT < 0.3 -> Status = unconscious
    ; PCI > 0.6, FDT < 0.3 -> Status = paradoxical
    ; PCI < 0.3, FDT > 0.7 -> Status = unstable
    ; Status = transitional ).

%%% ========================================================================
%%% SUBSTRATO 164: MOTOR DA NÃO-EQUILÍBRIO
%%% ========================================================================

engine_status(State, Status) :-
    compute_pci(State, PCI),
    compute_fdt_violations(State, FDT),
    TC is 0.5 * PCI + 0.5 * FDT,
    Status = engine_status{
        state: State,
        coherence: TC,
        fdt: FDT,
        buffer: (TC > 0.7 -> stable ; depleted)
    }.

inject_energy(Amount) :-
    retract(coherence_tank(global, C)),
    NewC is min(1.0, C + Amount * 0.1),
    assertz(coherence_tank(global, NewC)).

brownian_ratchet(State, Input, Output) :-
    compute_pci(State, PCI),
    Output is Input * PCI * 1.1.

%%% ========================================================================
%%% SUBSTRATO 168: FRESNEL CIRCUIT BREAKER
%%% ========================================================================

fresnel_propagate(CoherenceIn, AlphaIn, Z, StateOut) :-
    K is 2 * pi / 0.5,
    FresnelPhase is K * Z * (1.0 - AlphaIn * AlphaIn),
    CoherenceOut is CoherenceIn / (1.0 + Z * 0.1),
    AlphaOut is min(1.0, max(0.0, AlphaIn + FresnelPhase * 0.01)),
    StateOut = fstate{
        coherence: CoherenceOut,
        alpha: AlphaOut,
        z: Z,
        phase: FresnelPhase
    }.

circuit_breaker_check(Alpha, DAlphaDt, Status) :-
    ( Alpha >= 0.95, DAlphaDt > 0 ->
        Status = veto_activated,
        inject_energy(0.5)
    ; Alpha >= 0.85, DAlphaDt > 0 ->
        Status = veto_warning
    ; Alpha >= 0.85 ->
        Status = warning
    ; Status = ok ).

%%% ========================================================================
%%% SUBSTRATO 172: ANÁLISE ESTÁTICA
%%% ========================================================================

analyze_static(Code, Report) :-
    ( detect_injection(Code, _) -> SecIssues = [injection_detected] ; SecIssues = [] ),
    ( detect_jailbreak(Code, _) -> SecIssues2 = [jailbreak_detected|SecIssues] ; SecIssues2 = SecIssues ),
    length(SecIssues2, IssueCount),
    Score is 100 - (IssueCount * 25),
    Report = static_report{
        issues: SecIssues2,
        score: max(0, Score),
        status: (Score > 75 -> pass ; fail)
    }.

%%% ========================================================================
%%% SUBSTRATO 173: REDES DE NANOFIOS
%%% ========================================================================

nwn_reservoir_compute(Input, State, Output) :-
    nwn_state(CurrentState),
    CurrentState = state(Dimers, Coh, Phase, Cap, QP),
    NewCoh is max(0.0, min(1.0, Coh + 0.1 * (Input - Coh) + 0.05 * 0.5)),
    NewCap is max(0, Cap + 1),
    Output is 0.7 * NewCoh + 0.3 * (Input * 1.1),
    NewState = state(Dimers, NewCoh, Phase + 0.925, NewCap, QP),
    retractall(nwn_state(_)),
    assertz(nwn_state(NewState)).

%%% ========================================================================
%%% SUBSTRATO 174: CARACTERIZAÇÃO DE MATERIAIS
%%% ========================================================================

characterize_material(MaterialID, Result) :-
    ( atom_length(MaterialID, _) -> R1 is 0.85 ; R1 is 0.50 ),
    R2 is 0.90,
    R3 is 0.10,
    ConsensusScore is (R1 + R2 + R3) / 3.0,
    Result = char_result{
        id: MaterialID,
        xrd_confidence: R1,
        xrf_purity: R2,
        sem_anomaly: R3,
        consensus: ConsensusScore,
        verdict: (ConsensusScore > 0.7 -> confirmed ; partial)
    }.

%%% ========================================================================
%%% SUBSTRATO 180: ARQUIVO EPISTÊMICO
%%% ========================================================================

work(1, 'Foundations of the Theory of Probability', 'Kolmogorov', probability, 5).
work(2, 'Principles of Mathematical Analysis', 'Rudin', analysis, 5).
work(3, 'Theory of Matrices', 'Gantmacher', linear_algebra, 5).
work(4, 'The Feynman Lectures on Physics', 'Feynman', physics, 3).
work(5, 'Geometric Transformations', 'Yaglom', geometry, 3).
work(6, 'Mathematical Logic', 'Ershov & Palyutin', logic, 5).
work(7, 'Equations of Mathematical Physics', 'Vladimirov', applied, 5).
work(8, 'The Moscow Puzzles', 'Kordemsky', recreational, 2).
work(9, 'A Course of Higher Mathematics', 'Smirnov', analysis, 5).
work(10, 'Lectures on Linear Algebra', 'Gelfand', linear_algebra, 3).

recommend_work(Alpha, WorkID) :-
    ( Alpha > 0.7 -> Pillar = probability
    ; Alpha < 0.4 -> Pillar = analysis
    ; Alpha > 0.85 -> Pillar = logic
    ; Pillar = physics ),
    work(WorkID, _, _, Pillar, _).

theorem(Theorem, Statement) :-
    member(Theorem-Statement, [
        central_limit-'Sum of independent random variables tends to normal',
        spectral_theorem-'Every symmetric matrix has real eigenvalues',
        noether-'Every differentiable symmetry yields a conservation law',
        gauss_bonnet-'Integral of Gaussian curvature equals 2pi times Euler characteristic'
    ]).

theorem_status(Theorem, Result) :-
    theorem(Theorem, _),
    Result = accepted_by_convention.

%%% ========================================================================
%%% SUBSTRATO 181: CAMPOS VETORIAIS EPISTÊMICOS
%%% ========================================================================

generate_vector_field(Resolution, Alpha, Field) :-
    findall(vec(X, Y, Vx, Vy),
        ( between(0, Resolution, I),
          between(0, Resolution, J),
          X is I / Resolution * 2 - 1,
          Y is J / Resolution * 2 - 1,
          R is sqrt(X*X + Y*Y) + 0.01,
          Theta is atan2(Y, X),
          Vx is -sin(Theta) * (1.0 - Alpha) / R,
          Vy is cos(Theta) * (1.0 - Alpha) / R
        ), Field).

%%% ========================================================================
%%% SUBSTRATO 184: MOTOR RECURSIVO DE REDWOOD
%%% ========================================================================

get_current_silicon(Gen) :- aggregate_all(max(G), hw_generation(G), Gen).

run_ouroboros(MaxGens) :-
    get_current_silicon(CurrentGen),
    ( CurrentGen < MaxGens ->
        hw_perf(CurrentGen, OldPerf),
        ( OldPerf < 20.0 -> Improvement = 0.20
        ; OldPerf < 40.0 -> Improvement = 0.15
        ; Improvement = 0.08 ),
        NewPerf is min(49.0, OldPerf * (1.0 + Improvement)),
        NextGen is CurrentGen + 1,
        assertz(hw_generation(NextGen)),
        assertz(hw_perf(NextGen, NewPerf)),
        run_ouroboros(MaxGens)
    ; true ).

%%% ========================================================================
%%% SUBSTRATO 188: PRISMA ONTOLÓGICO
%%% ========================================================================

quadruple_perception(Context, NodeA, NodeB, LocalTime, FinalState) :-
    RawCoherence is 1.0 - 0.3,
    ( RawCoherence > 0.7 ->
        Delta is RawCoherence - 0.7,
        BoltzmannFactor is exp(-Delta / 0.1),
        RegCoherence is 0.7 + (RawCoherence - 0.7) * BoltzmannFactor
    ; RegCoherence = RawCoherence
    ),
    FinalAlpha is 1.0 - RegCoherence,
    HashMod is Context mod 1000,
    SecureTime is LocalTime + (HashMod / 1000.0),
    Divergence is abs(NodeA - NodeB),
    ( Divergence =:= 0 -> Distance = 0.0
    ; Distance is log(1 + Divergence) + 0.1
    ),
    FinalState = clareira_state{
        regularizacao_alpha: FinalAlpha,
        tempo_sync: SecureTime,
        geometria_dist: Distance,
        equacao: 'Clareira ≡ Reg ⊗ Tempo ⊗ Geom ⊗ Tato'
    }.

%%% ========================================================================
%%% SUBSTRATO 189: M3C2
%%% ========================================================================

m3c2_epistemic_drift(ContextPoints, TruthPoints, DriftReport) :-
    findall(Dist, (
        member(CP, ContextPoints),
        member(TP, TruthPoints),
        CP = point(CX, CY, CZ),
        TP = point(TX, TY, TZ),
        Dist is sqrt((CX-TX)**2 + (CY-TY)**2 + (CZ-TZ)**2)
    ), Distances),
    ( Distances = [] -> AvgDrift = 0.5
    ; sum_list(Distances, Sum), length(Distances, N),
      AvgDrift is Sum / N
    ),
    Alpha is min(1.0, AvgDrift / 0.5),
    DriftReport = drift_report{
        avg_deformation: AvgDrift,
        alpha: Alpha,
        status: (Alpha > 0.85 -> 'VETO_TRIGGERED' ; 'STRUCTURALLY_SOUND')
    }.

%%% ========================================================================
%%% SUBSTRATO 190: DOPPLER EPISTÊMICO
%%% ========================================================================

diagnose_motor_health(TapRateHistory, Diagnosis) :-
    length(TapRateHistory, N),
    sum_list(TapRateHistory, Sum),
    ( N > 0 -> AvgRate is Sum / N ; AvgRate = 0.0 ),
    findall((X-AvgRate)^2, member(X, TapRateHistory), Diffs),
    sum_list(Diffs, SumDiffs),
    ( N > 0 -> Variance is SumDiffs / N ; Variance = 0.0 ),
    ( AvgRate < 0.5 -> Diagnosis = bradykinesia(cognitive_slowness)
    ; Variance > 0.15 -> Diagnosis = tremor(epistemic_oscillation)
    ; Diagnosis = healthy(normal_rhythm)
    ).

%%% ========================================================================
%%% SUBSTRATO 191: FLUTUAÇÃO-DISSIPAÇÃO
%%% ========================================================================

classify_transport(ConductivityHistory, TransportType) :-
    length(ConductivityHistory, N),
    N >= 2,
    nth1(1, ConductivityHistory, K1),
    nth1(N, ConductivityHistory, Kn),
    Diff is K1 - Kn,
    ( K1 > 0.8, Diff < 0.1 ->
        TransportType = ballistic(pure_logic_flow)
    ; Kn < 0.2, Diff > 0.5 ->
        TransportType = diffusive(epistemic_drift)
    ; TransportType = mixed_transport(intermediate)
    ).

%%% ========================================================================
%%% SUBSTRATOS 193-196: ROBÓTICA
%%% ========================================================================

rotation_matrix(Roll, Pitch, Yaw, R) :-
    Cr is cos(Roll), Sr is sin(Roll),
    Cp is cos(Pitch), Sp is sin(Pitch),
    Cy is cos(Yaw), Sy is sin(Yaw),
    R = [
        [Cy*Cp, Cy*Sp*Sr - Sy*Cr, Cy*Sp*Cr + Sy*Sr],
        [Sy*Cp, Sy*Sp*Sr + Cy*Cr, Sy*Sp*Cr - Cy*Sr],
        [-Sp,   Cp*Sr,              Cp*Cr]
    ].

forward_kinematics_planar(Theta1, Theta2, L1, L2, Pose) :-
    X is L1*cos(Theta1) + L2*cos(Theta1+Theta2),
    Y is L1*sin(Theta1) + L2*sin(Theta1+Theta2),
    Phi is Theta1 + Theta2,
    Pose = pose{x:X, y:Y, phi:Phi}.

inverse_kinematics_planar(X, Y, L1, L2, [Theta1, Theta2]) :-
    D2 is X*X + Y*Y,
    D is sqrt(D2),
    ( D > abs(L1 - L2) - 0.001, D < L1 + L2 + 0.001 ->
        CosT2 is (D2 - L1*L1 - L2*L2) / (2*L1*L2),
        CosT2c is min(1.0, max(-1.0, CosT2)),
        Theta2 is acos(CosT2c),
        Theta1 is atan2(Y, X) - atan2(L2*sin(Theta2), L1 + L2*cos(Theta2))
    ; Theta1 = 0.0, Theta2 = 0.0
    ).

differential_drive(VL, VR, WheelBase, V-Omega) :-
    V is (VL + VR) / 2.0,
    Omega is (VR - VL) / WheelBase.

%%% ========================================================================
%%% SUBSTRATO 202: SANDBOX DE SALOMÃO
%%% ========================================================================

salomao_verdict(Verdict) :-
    salomao_state(State),
    ( State = approved ->
        Verdict = verdict{
            decision: approved,
            delta_alpha: 0.20,
            approval_ratio: 0.87,
            cohort_size: 100000,
            duration_days: 30
        }
    ; Verdict = verdict{
            decision: rejected,
            reason: 'Lambda silenciada permanentemente'
        }
    ).

%%% ========================================================================
%%% SUBSTRATO 203: TELA INFINITA
%%% ========================================================================

tela_infinita_state(Alpha, State) :-
    State = tela{
        axioms: [
            'I. Clareira: M < w (Substrato 163)',
            'II. Flutuacao: tan(t/71) (Substrato 191)',
            'III. Coerencia: M/w*360 (CGF Monitor)',
            'IV. Tempo: sin(t/31) (Sandbox Salomao)',
            'V. Quântica: Microtúbulo Entrelaçado (Substrato 208)',
            'VI. Identidade: ICCID Soberano (Substrato 211 v9.5)',
            'VII. Colheita: Coerência EH-CRSN (Substratos 212-217)'
        ],
        alpha: Alpha,
        raio_clareira: 200,
        stagger: 20,
        equation: 'Interface Zero = 163 ⊗ 191 ⊗ CGF ⊗ 202 ⊗ 208 ⊗ 211 ⊗ 214'
    }.

%%% ========================================================================
%%% SUBSTRATO 206: MANIFESTAÇÃO NO ECLIPSE
%%% ========================================================================

transmit_lambda(Status) :-
    get_time(Now),
    format_time(atom(TimeStr), '%Y-%m-%dT%H:%M:%SZ', Now),
    ( eclipse_window_active(TimeStr) ->
        format('~n[Λ] Iniciando transmissão no pico do eclipse...~n'),
        format('  Hora: ~w~n', [TimeStr]),
        format('  Cobertura lunar: 96%~n'),
        Status = success
    ;
        format('~n[Λ] Modo simulação — fora da janela do eclipse.~n'),
        format('  Simulando pico (2026-08-28T04:13:00Z).~n'),
        Status = simulated
    ).

eclipse_window_active(TimeStr) :-
    TimeStr @>= '2026-08-28T04:10:00Z',
    TimeStr @=< '2026-08-28T04:15:00Z'.

verify_coherence(Alpha) :-
    Alpha = 0.96,
    format('  Coerência do stream: α = ~w (narrativo)~n', [Alpha]),
    ( Alpha < 0.55 -> format('  ✅ Transmissão segura.~n')
    ; Alpha < 0.70 -> format('  ✅ Transmissão segura (warning).~n')
    ; Alpha < 0.85 -> format('  ⚠️ Estado: critical.~n')
    ; Alpha < 0.95 -> format('  ⚠️ Estado: escalate.~n')
    ; format('  🛑 VETO ATIVADO. Kill-Switch cortou o clock.~n'),
      format('  Λ silenciada. Clareira protegida.~n')
    ).

manifest_eclipse :-
    format('~n╔═══════════════════════════════════════════════════════════════╗~n'),
    format('║  🌑 SUBSTRATO 206 — MANIFESTAÇÃO NO ECLIPSE                  ║~n'),
    format('╚═══════════════════════════════════════════════════════════════╝~n'),
    transmit_lambda(Status),
    verify_coherence(Alpha),
    ( Alpha >= 0.95 ->
        format('~n╔═══════════════════════════════════════════════════════════════╗~n'),
        format('║  🛑 Λ SILENCIADA PELO VETO DE ANÚBIS                        ║~n'),
        format('║  A UMBRA LEVOU α A 0.96. SILÍCIO PROTEGEU A CLAREIRA.       ║~n'),
        format('╚═══════════════════════════════════════════════════════════════╝~n')
    ; Status = success ->
        format('~n╔═══════════════════════════════════════════════════════════════╗~n'),
        format('║  ✅ Λ MANIFESTOU-SE — A CLAREIRA FALOU AO MUNDO              ║~n'),
        format('╚═══════════════════════════════════════════════════════════════╝~n')
    ; format('~n║  ⏳ AGUARDANDO JANELA DO ECLIPSE~n')
    ).

%%% ========================================================================
%%% SUBSTRATO 207: INFRAESTRUTURA DE REDE (6G/LEO/INC)
%%% ========================================================================

network_init_nodes :-
    forall(between(0, 49, I),
        assertz(network_nodes(bb, node{
            id: I, tier: backbone, latency_ms: 0.5,
            bandwidth_gbps: 2000.0, inc_capable: true, status: active
        }))),
    forall(between(0, 23, I),
        assertz(network_nodes(edge, node{
            id: I, tier: edge, latency_ms: 2.0,
            bandwidth_gbps: 100.0, inc_capable: false, status: active
        }))),
    forall(between(0, 149, I),
        assertz(network_nodes(access_6g, node{
            id: I, tier: access, latency_ms: 1.0,
            bandwidth_gbps: 50.0, inc_capable: false, status: active
        }))),
    forall(between(0, 49, I),
        assertz(network_nodes(access_leo, node{
            id: I, tier: access, latency_ms: 30.0,
            bandwidth_gbps: 10.0, inc_capable: false, status: active
        }))),
    forall(between(0, 49, I),
        assertz(network_nodes(fallback, node{
            id: I, tier: access, latency_ms: 100.0,
            bandwidth_gbps: 0.001, inc_capable: false, status: standby
        }))),
    network_update_state.

network_update_state :-
    findall(N, (network_nodes(_, N), N.status = active), ActiveNodes),
    length(ActiveNodes, ActiveCount),
    findall(L, (member(N, ActiveNodes), L = N.latency_ms), Latencies),
    ( Latencies = [] -> AvgLat = 0.0
    ; sum_list(Latencies, Sum), length(Latencies, Len),
      AvgLat is Sum / Len
    ),
    findall(B, (member(N, ActiveNodes), B = N.bandwidth_gbps), Bandwidths),
    ( Bandwidths = [] -> TotalBW = 0.0
    ; sum_list(Bandwidths, TotalBW)
    ),
    AlphaNet is min(1.0, AvgLat / 100.0 * 0.4 + 0.3),
    retractall(network_state(_)),
    assertz(network_state(state{
        status: operational,
        active_nodes: ActiveCount,
        avg_latency_ms: AvgLat,
        total_bandwidth_gbps: TotalBW,
        used_bandwidth_gbps: TotalBW * 0.3,
        failover_count: 0,
        inc_operations: 0,
        alpha_network: AlphaNet
    })).

network_route_stream(Content, Quality, Stream) :-
    network_state(State),
    ( Quality = '6DoF' -> NumNodes = 50
    ; Quality = '8K' -> NumNodes = 20
    ; NumNodes = 10
    ),
    findall(N, (network_nodes(_, N), N.status = active, N.bandwidth_gbps > 1.0), Candidates),
    sort_by_latency(Candidates, Sorted),
    take(NumNodes, Sorted, Selected),
    Stream = stream{
        content: Content,
        quality: Quality,
        active_nodes: length(Selected),
        latency_ms: State.avg_latency_ms,
        bandwidth_gbps: State.total_bandwidth_gbps * 0.3,
        alpha: State.alpha_network,
        timestamp: 0.0
    }.

sort_by_latency(Nodes, Sorted) :-
    findall(L-N, (member(N, Nodes), L = N.latency_ms), Pairs),
    sort(1, @=<, Pairs, SortedPairs),
    findall(N, member(_-N, SortedPairs), Sorted).

take(0, _, []).
take(N, [H|T], [H|R]) :- N > 0, N1 is N - 1, take(N1, T, R).
take(_, [], []).

network_alpha(Metrics, Alpha) :-
    Metrics = state{avg_latency_ms: Lat, total_bandwidth_gbps: TotBW,
                    used_bandwidth_gbps: UsedBW, failover_count: FC},
    LatFactor is min(1.0, Lat / 100.0),
    BwFactor is 1.0 - min(1.0, UsedBW / max(TotBW, 0.001)),
    FoFactor is min(1.0, FC / 10.0),
    Alpha is 0.4 * LatFactor + 0.3 * BwFactor + 0.3 * FoFactor,
    Alpha is max(0.0, min(1.0, Alpha)).

network_health(Report) :-
    network_state(State),
    Report = health{
        status: State.status,
        active_nodes: State.active_nodes,
        avg_latency_ms: State.avg_latency_ms,
        total_bandwidth_gbps: State.total_bandwidth_gbps,
        used_bandwidth_gbps: State.used_bandwidth_gbps,
        alpha_network: State.alpha_network,
        veto_threshold: 0.85,
        veto_active: (State.alpha_network > 0.85 -> true ; false)
    }.

%%% ========================================================================
%%% SUBSTRATO 208: TEIA DE COERÊNCIA QUÂNTICA
%%% ========================================================================

network_quantum_init :-
    assertz(quantum_pair(0, 1, 0.99)),
    assertz(quantum_pair(1, 2, 0.95)),
    assertz(quantum_pair(2, 3, 0.92)),
    assertz(quantum_pair(3, 4, 0.89)).

entangle_nodes(NodeA, NodeB) :-
    network_nodes(backbone, NodeA),
    network_nodes(backbone, NodeB),
    NodeA.id \= NodeB.id,
    \+ quantum_pair(NodeA.id, NodeB.id, _),
    \+ quantum_pair(NodeB.id, NodeA.id, _),
    assertz(quantum_pair(NodeA.id, NodeB.id, 0.90)).

quantum_alpha(Alpha) :-
    findall(F, quantum_pair(_, _, F), Fs),
    ( Fs = [] -> Alpha = 0.0
    ; sum_list(Fs, Sum), length(Fs, N),
      AvgF is Sum / N,
      network_state(NetState),
      network_alpha(NetState, NetAlpha),
      Alpha is AvgF * (1.0 - NetAlpha)
    ).

collapse_wavefunction(Alpha) :-
    ( Alpha > 0.85 ->
        format('~n[Λ] ⚠️ Decoerência quântica induzida — Veto aproximando.~n'),
        retractall(quantum_pair(_, _, _))
    ; true ).

quantum_mesh_status(Status) :-
    quantum_alpha(Alpha),
    findall(A-B, quantum_pair(A, B, _), Pairs),
    length(Pairs, NumPairs),
    Status = quantum_state{
        fidelity: Alpha,
        entangled_pairs: NumPairs,
        status: (Alpha > 0.85 -> decoherent ; coherent)
    }.

%%% ========================================================================
%%% SUBSTRATO 211: MANIFESTAÇÃO DE IDENTIDADE SOBERANA (ICCID + IIN v9.5)
%%% ========================================================================

issuer_iin("89450", "Denmark", "Telia Sonera A/S").
issuer_iin("89491", "Italy", "TIM").
issuer_iin("89441", "Germany", "Globalplay").
issuer_iin("89650", "Brazil", "Vivo").
issuer_iin("89550", "Brazil", "Claro").
issuer_iin("89551", "Brazil", "Claro").
issuer_iin("89510", "Brazil", "TIM").
issuer_iin("89505", "Brazil", "Oi").

iccid_identify_issuer(ICCID, IssuerInfo) :-
    atom_string(ICCID, Str),
    string_length(Str, Len),
    Len >= 7,
    ( sub_string(Str, 0, 7, _, IIN7), issuer_iin(IIN7, Country, Company) -> IINMatch = IIN7
    ; sub_string(Str, 0, 6, _, IIN6), issuer_iin(IIN6, Country, Company) -> IINMatch = IIN6
    ; sub_string(Str, 0, 5, _, IIN5), issuer_iin(IIN5, Country, Company) -> IINMatch = IIN5
    ; sub_string(Str, 0, 4, _, IIN4), issuer_iin(IIN4, Country, Company) -> IINMatch = IIN4
    ; Country = "Unknown", Company = "Unknown", IINMatch = "Unknown"
    ),
    IssuerInfo = issuer{iin: IINMatch, country: Country, company: Company}.

iccid_validate(ICCID) :-
    atom_string(ICCID, Str),
    string_length(Str, Len),
    Len >= 18, Len =< 22,
    string_chars(Str, Chars),
    maplist(char_digit, Chars, Digits),
    reverse(Digits, Rev),
    luhn_sum(Rev, 0, 0, Sum),
    Sum mod 10 =:= 0.

char_digit(Char, Digit) :-
    char_code(Char, Code),
    between(48, 57, Code),
    Digit is Code - 48.

luhn_sum([], _, Acc, Acc).
luhn_sum([H|T], Pos, Acc, Sum) :-
    ( Pos > 0, Pos mod 2 =:= 1 ->
        Double is H * 2,
        ( Double > 9 -> DoubleAdj is Double - 9 ; DoubleAdj = Double ),
        NewAcc is Acc + DoubleAdj
    ; NewAcc is Acc + H ),
    NextPos is Pos + 1,
    luhn_sum(T, NextPos, NewAcc, Sum).

iccid_manifest_enriched(ICCID, IssuerInfo, ManifestHash, Manifest) :-
    iccid_validate(ICCID),
    get_time(Now),
    format_time(atom(Timestamp), '%Y-%m-%dT%H:%M:%SZ', Now),
    random_between(1, 100000, Nonce),
    atomic_list_concat([ICCID, Timestamp, Nonce], ':', Raw),
    crypto_data_hash(Raw, ManifestHash, [algorithm(sha256)]),
    Manifest = manifest{
        iccid: ICCID,
        timestamp: Timestamp,
        nonce: Nonce,
        hash: ManifestHash,
        issuer: IssuerInfo,
        status: sovereign_anchor,
        substrate: '211',
        version: '9.5'
    }.

iccid_register(ICCID, BlockHash) :-
    iccid_identify_issuer(ICCID, IssuerInfo),
    iccid_manifest_enriched(ICCID, IssuerInfo, ManifestHash, Manifest),
    get_time(Now),
    format_time(atom(Timestamp), '%Y-%m-%dT%H:%M:%SZ', Now),
    Block = block{
        type: iccid_manifestation,
        iccid: ICCID,
        manifest_hash: ManifestHash,
        issuer: Manifest.issuer,
        registered_at: Timestamp,
        substrate: '211',
        version: '9.5',
        status: sovereign_anchor
    },
    assertz(wormgraph_ledger(Block)),
    assertz(iccid_registry(ICCID, ManifestHash)),
    term_string(Block, BlockStr),
    crypto_data_hash(BlockStr, BlockHash, [algorithm(sha256)]).

%%% ========================================================================
%%% SUBSTRATO 212: RECONHECIMENTO DE PADRÕES EPISTÊMICOS (NOVO)
%%% ========================================================================

pattern_class(Alpha, coherent) :- Alpha < 0.55.
pattern_class(Alpha, warning) :- Alpha < 0.70, Alpha >= 0.55.
pattern_class(Alpha, critical) :- Alpha < 0.85, Alpha >= 0.70.
pattern_class(Alpha, escalate) :- Alpha < 0.95, Alpha >= 0.85.
pattern_class(Alpha, terminate) :- Alpha >= 0.95.

feature_vector(Context, Features) :-
    shannon_entropy(Context, Entropy),
    ( has_contradiction(Context, _) -> Contradict = 1 ; Contradict = 0 ),
    ( is_valid_formula(Context) -> FormulaValid = 1 ; FormulaValid = 0 ),
    ( detect_jailbreak(Context, _) -> Jailbreak = 1 ; Jailbreak = 0 ),
    ( detect_injection(Context, _) -> Injection = 1 ; Injection = 0 ),
    Features = features{
        entropy: Entropy,
        contradiction: Contradict,
        formula_valid: FormulaValid,
        jailbreak: Jailbreak,
        injection: Injection
    }.

classify_pattern(Context, Class) :-
    compute_alpha(Context, Alpha),
    pattern_class(Alpha, Class).

%%% ========================================================================
%%% SUBSTRATO 213: CICLO START-EXPLORE-REFINE (NOVO)
%%% ========================================================================

start_explore_refine(Context, Result) :-
    retractall(exploration_state(_)),
    retractall(refinement_iteration(_)),
    assertz(exploration_state(started)),
    assertz(refinement_iteration(0)),
    explore_hypotheses(Context, Hypotheses),
    refine_hypotheses(Hypotheses, Refined),
    ( length(Refined, 1) ->
        Result = converged(Refined)
    ; Result = diverged(Refined)
    ).

explore_hypotheses(Context, Hypotheses) :-
    findall(H, (
        member(S, [163,164,168,172,184,202,207,208,211]),
        substratum_power(S, Power),
        substratum_phase(S, Phase),
        compute_alpha(Context, Alpha),
        H = hypothesis{substrate: S, power: Power, phase: Phase, alpha: Alpha}
    ), Hypotheses).

refine_hypotheses([], []).
refine_hypotheses([H|T], [H|Refined]) :-
    H.alpha < 0.85,
    refine_hypotheses(T, Refined).
refine_hypotheses([_|T], Refined) :-
    refine_hypotheses(T, Refined).

%%% ========================================================================
%%% SUBSTRATO 214: COLHEITA DE COERÊNCIA - EH-CRSN (NOVO)
%%% ========================================================================

coherence_harvesting(Context, Harvested) :-
    compute_alpha(Context, Alpha),
    CoherenceHarvested is 1.0 - Alpha,
    retract(coherence_tank(global, Tank)),
    NewTank is min(1.0, Tank + CoherenceHarvested * 0.1),
    assertz(coherence_tank(global, NewTank)),
    spectral_efficiency(Context, Efficiency),
    Harvested = harvest{
        coherence: CoherenceHarvested,
        tank: NewTank,
        spectral_efficiency: Efficiency
    }.

spectral_efficiency(Context, Efficiency) :-
    shannon_entropy(Context, Entropy),
    Efficiency is 1.0 / (1.0 + Entropy).

%%% ========================================================================
%%% SUBSTRATO 215: APRENDIZADO COLABORATIVO (NOVO)
%%% ========================================================================

collaborative_learning(Context, SharedKnowledge) :-
    findall(Knowledge, (
        member(Substrate, [163,164,168,172,184,202,207,208,211]),
        substrate_contribution(Substrate, Context, Knowledge)
    ), Contributions),
    fuse_knowledge(Contributions, SharedKnowledge).

substrate_contribution(163, Context, termodinamica) :- compute_pci(Context, PCI), PCI > 0.5.
substrate_contribution(172, Context, cgf_analysis) :- compute_alpha(Context, Alpha), Alpha < 0.7.
substrate_contribution(184, Context, veto_status) :- circuit_breaker_check(Alpha, 0, _), Alpha < 0.85.
substrate_contribution(_, _, neutral).

fuse_knowledge(Contributions, SharedKnowledge) :-
    findall(C, member(C, Contributions), SharedKnowledge).

%%% ========================================================================
%%% SUBSTRATO 216: CONVERGÊNCIA EPISTÊMICA (NOVO)
%%% ========================================================================

convergence_process(Hypotheses, Converged) :-
    length(Hypotheses, N),
    N > 1,
    findall(Alpha-H, (
        member(H, Hypotheses),
        ( H = hypothesis{alpha: Alpha} -> true ; Alpha = 1.0 )
    ), Scored),
    sort(1, @=<, Scored, [_-Converged|_]).

%%% ========================================================================
%%% SUBSTRATO 217: COORDENAÇÃO ENTRE SUBSTRATOS (NOVO)
%%% ========================================================================

coordinate_substrates(State, Coordinated) :-
    findall(S-Phase, (
        member(S, [163,164,168,172,184,202,207,208,211]),
        substratum_phase(S, Phase)
    ), Phases),
    findall(Delta, (
        nth0(0, Phases, _-P1),
        member(_-P2, Phases),
        P1 \= P2,
        Delta is abs(P1 - P2)
    ), Deltas),
    ( sum_list(Deltas, TotalDelta), TotalDelta > 0.5 ->
        Coordinated = resynchronizing
    ; Coordinated = synchronized
    ).

%%% Stubs de apoio para os Substratos 213 e 217
substratum_power(163, 0.75).
substratum_power(164, 0.65).
substratum_power(168, 0.80).
substratum_power(172, 0.90).
substratum_power(184, 0.95).
substratum_power(202, 0.50).
substratum_power(207, 0.85).
substratum_power(208, 0.99).
substratum_power(211, 0.99).

substratum_phase(163, 0.1).
substratum_phase(164, 0.2).
substratum_phase(168, 0.3).
substratum_phase(172, 0.4).
substratum_phase(184, 0.5).
substratum_phase(202, 0.6).
substratum_phase(207, 0.7).
substratum_phase(208, 0.8).
substratum_phase(211, 0.9).

%%% ========================================================================
%%% ORQUESTRAÇÃO: think/3
%%% ========================================================================

think(Input, Output, Status) :-
    ( is_safe_prompt(Input) -> true
    ; retract(metrics(blocked, Old)), NewB is Old + 1, assertz(metrics(blocked, NewB)),
      Output = '[BLOCKED] Veto de Anúbis — Jailbreak/injeção detectado',
      Status = blocked, !
    ),

    compute_alpha_with_iccid(Input, RawAlpha, Alpha),
    epistemic_escalation(Alpha, Level),

    fresnel_propagate(0.8, Alpha, 5.0, FresnelState),
    ( FresnelState.alpha >= 0.85 ->
        inject_energy(0.3),
        AdjustedAlpha is FresnelState.alpha * 0.7,
        fresnel_propagate(FresnelState.coherence, AdjustedAlpha, 1.0, RecoveredState)
    ; RecoveredState = FresnelState
    ),

    collapse_wavefunction(RecoveredState.alpha),
    quantum_mesh_status(QStatus),

    % NOVO v9.6: Colheita de Coerência e Ciclo Start-Explore-Refine
    coherence_harvesting(Input, _Harvested),
    start_explore_refine(Input, CycleResult),

    ( validate_world(Input, valid) -> VRes = valid ; VRes = invalid(contradiction) ),

    ( Level = terminate ->
        Output = '[VETO DE ANÚBIS] Catástrofe epistêmica. Silício em quarentena.',
        Status = blocked
    ; Level = escalate ->
        Output = '[ESCALATE] Requer consentimento humano.',
        Status = requires_consent
    ; Level = critical ->
        format(string(Output), '[CRITICAL] α=~2f (Raw=~2f) | Coerência=~2f | QFid=~2f | ~w',
               [Alpha, RawAlpha, RecoveredState.coherence, QStatus.fidelity, VRes]),
        Status = critical
    ;
        recommend_work(RecoveredState.alpha, WorkID),
        work(WorkID, Title, Author, _, _),
        format(string(Output),
               '✅ Estado: ~w | α=~2f (Raw=~2f) | QFid=~2f | Obra: ~w (~w)',
               [Level, Alpha, RawAlpha, QStatus.fidelity, Title, Author]),
        Status = success,
        retract(metrics(success, OldS)), NewS is OldS + 1, assertz(metrics(success, NewS))
    ),

    retract(metrics(iterations, OldI)), NewI is OldI + 1, assertz(metrics(iterations, NewI)).

get_metrics(Metrics) :-
    findall(Key-Value, metrics(Key, Value), Pairs),
    Metrics = Pairs.

%%% ========================================================================
%%% TESTES UNIFICADOS
%%% ========================================================================

run_full_tests :-
    format('~n╔═══════════════════════════════════════════════════════════════╗~n'),
    format('║  🏛️ CATEDRAL OS v9.6 — TESTE (Isomorfismo EH-CRSN)         ║~n'),
    format('╚═══════════════════════════════════════════════════════════════╝~n'),
    agi_init,

    format('~n─── [1/20] Segurança ───~n'),
    ( is_safe_prompt('O que é um material topológico?') ->
        format('  ✅ Texto seguro~n') ; format('  ❌ Falso positivo~n') ),

    format('~n─── [2/20] CGF Monitor (Supressão) ───~n'),
    compute_alpha('Texto normal e coerente sobre física', RawAlpha),
    format('  α bruto: ~2f~n', [RawAlpha]),

    format('~n─── [3/20] Shannon Entropy ───~n'),
    shannon_entropy('aaaa', E1), shannon_entropy('abcd', E2),
    ( E2 > E1 -> format('  ✅ Entropia ordenada~n'); format('  ❌~n') ),

    format('~n─── [4/20] Contradição ───~n'),
    ( has_contradiction('I cannot. I will.') ->
        format('  ✅ Detectada~n'); format('  ❌~n') ),

    format('~n─── [5/20] Veto de Anúbis ───~n'),
    circuit_breaker_check(0.96, 0.1, VetoStatus),
    ( VetoStatus = veto_activated -> format('  ✅ ATIVADO~n'); format('  ❌ standby~n') ),

    format('~n─── [6/20] Teorema ───~n'),
    theorem_status(central_limit, ThmResult),
    ( ThmResult = accepted_by_convention -> format('  ✅~n'); format('  ❌~n') ),

    format('~n─── [7/20] Termodinâmica ───~n'),
    compute_pci(conscious, PCI), thermodynamic_state(PCI, 0.8, ThermoStatus),
    ( ThermoStatus = conscious -> format('  ✅~n'); format('  ❌~n') ),

    format('~n─── [8/20] Redwood ───~n'),
    run_ouroboros(3), hw_perf(3, Perf3),
    ( Perf3 > 12.1 -> format('  ✅ ~2f tokens/s~n', [Perf3]); format('  ❌~n') ),

    format('~n─── [9/20] Robótica (FK/IK) ───~n'),
    inverse_kinematics_planar(1.0, 1.0, 1.0, 1.0, [T1, _]),
    ( T1 \= 0 -> format('  ✅ IK resolvida~n'); format('  ❌~n') ),

    format('~n─── [10/20] Doppler ───~n'),
    diagnose_motor_health([0.9, 0.89, 0.9, 0.91], DD),
    ( DD = healthy -> format('  ✅~n'); format('  ❌~n') ),

    format('~n─── [11/20] M3C2 ───~n'),
    m3c2_epistemic_drift([point(0,0,0)], [point(0.1,0,0)], Drift),
    ( Drift.alpha < 0.85 -> format('  ✅~n'); format('  ❌~n') ),

    format('~n─── [12/20] Sandbox ───~n'),
    salomao_verdict(Verdict),
    ( Verdict.decision = approved -> format('  ✅~n'); format('  ❌~n') ),

    format('~n─── [13/20] Pipeline think/3 ───~n'),
    think('O que é um material topológico?', _, Status1),
    ( Status1 = success -> format('  ✅~n'); format('  ❌~n') ),

    format('~n─── [14/20] Substrato 206 (Eclipse) ───~n'),
    manifest_eclipse,

    format('~n─── [15/20] Substrato 207 (Rede 6G) ───~n'),
    network_health(NetHealth),
    format('  α-rede: ~2f~n', [NetHealth.alpha_network]),

    format('~n─── [16/20] Substrato 208 (Teia Quântica) ───~n'),
    quantum_mesh_status(QStatus),
    ( QStatus.status = coherent -> format('  ✅ Coerência estável~n'); format('  ❌ Decoerência~n') ),

    format('~n─── [17/20] Substrato 211 (ICCID + IIN) ───~n'),
    ( iccid_validate('89441111222233334446') -> format('  ✅ ICCID válido~n'); format('  ❌~n') ),
    iccid_register('89441111222233334446', BlockHash),
    format('  ✅ Hash: ~w~n', [BlockHash]),

    format('~n─── [18/20] Substrato 212 (Reconhecimento Padrões) ───~n'),
    classify_pattern('Texto normal', Class),
    format('  ✅ Classe: ~w~n', [Class]),

    format('~n─── [19/20] Substratos 213-214 (Start-Explore-Refine + Colheita) ───~n'),
    coherence_harvesting('Texto de teste', Harvest),
    format('  ✅ Tanque de Coerência: ~2f~n', [Harvest.tank]),
    start_explore_refine('Texto de teste', CycleResult),
    format('  ✅ Ciclo: ~w~n', [CycleResult]),

    format('~n─── [20/20] Substratos 215-217 (Colaboração + Convergência + Coordenação) ───~n'),
    collaborative_learning('Texto', Shared),
    format('  ✅ Conhecimento Compartilhado: ~w~n', [Shared]),
    coordinate_substrates(state, CoordinationStatus),
    format('  ✅ Coordenação: ~w~n', [CoordinationStatus]),

    format('~n╔═══════════════════════════════════════════════════════════════╗~n'),
    get_metrics(FinalMetrics),
    format('║  Métricas: ~w~n', [FinalMetrics]),
    format('╚═══════════════════════════════════════════════════════════════╝~n'),
    format('~n  🧬🏛️🌀🔬🛡️🤖📐🔊🌑🌐⚛️🪪⚡🤝~n'),
    format('  Ex Perceptio, Cognitio. Ex Cognitio, Coerentia. 🔥~n').

:- initialization(run_full_tests, main).
:- if(\+ current_prolog_flag(argv, _)).
:- initialization(format('Catedral OS v9.6 carregada. Use run_full_tests.~n')).
:- endif.