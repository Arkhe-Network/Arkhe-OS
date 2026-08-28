#!/bin/bash
# clone_high_priority.sh — Clonagem dos repositórios prioritários

mkdir -p catedral_deps
cd catedral_deps

# 1. Núcleo Prolog
git clone https://github.com/SWI-Prolog/swipl-devel.git
git clone https://github.com/umuro/prolog-mcp.git

# 2. Robótica
git clone https://github.com/knowrob/knowrob.git
git clone https://github.com/knowrob/rosprolog.git

# 3. Nanofotônica
git clone https://github.com/metaphotonics/Inverse-metasurface-design-CGAN.git
git clone https://github.com/flexcompute/autophotonicdesign.git

# 4. Redes 6G
git clone https://github.com/ustutt-ipvs-vs/6GDetCom_MKFirm.git

# 5. QKD
git clone https://github.com/QOSST/qosst.git

# 6. Verificação Formal
git clone https://github.com/YosysHQ/SymbiYosys.git
git clone https://github.com/YosysHQ/yosys.git
git clone https://github.com/leanprover/lean4.git

echo "✅ Clonagem de alta prioridade concluída."