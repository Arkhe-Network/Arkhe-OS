#!/bin/bash
# fork_and_patch.sh — Cria forks e aplica patches específicos

# 1. Fork do SWI-Prolog (via GitHub CLI)
gh repo fork SWI-Prolog/swipl-devel --clone --remote

# 2. Aplica patch para o Substrato 209 (Controle de Fase)
cd swipl-devel
mkdir -p patches
cat > patches/phase_control.pl << 'EOF'
%%% ========================================================================
%%% SUBSTRATO 209 — CONTROLE DE FASE EPISTÊMICA (PATCH PARA SWI-Prolog)
%%% ========================================================================
:- module(phase_control, [
    effective_coherence/2,
    phase_gradient/4,
    spatial_null/3,
    array_factor/2
]).

effective_coherence(Substrates, Coherence) :-
    findall(Power * cos(Phase), (
        member(S, Substrates),
        substratum_power(S, Power),
        substratum_phase(S, Phase)
    ), Contributions),
    sum_list(Contributions, Coherence).
%%% ========================================================================
EOF

# 3. Compila e testa
make && make install
cd ..
