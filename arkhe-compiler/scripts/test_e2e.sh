#!/bin/bash
# test_e2e.sh – Teste completo do pipeline

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "🧪 TESTE E2E: MHD → MLIR → C/G‑code/VHDL → Ancoragem"

# 1. Gerar MLIR a partir da especificação MHD
echo "🔹 Gerando MLIR..."
python3 integrations/idealMHD/generate_mlir.py

# 2. LLM sugere pipeline (simulado)
echo "🔹 Sugerindo pipeline com LLM..."
export PIPELINE_PASSES="arkhe.lower-to-c,arkhe.generate-geometry,arkhe.verify-lean"

# 3. Executar MLIR Pass Manager
echo "🔹 Executando passes MLIR..."
mlir-opt integrations/idealMHD/mhd_spec.mlir \
    --arkhe.lower-to-c \
    --arkhe.generate-geometry \
    --arkhe.verify-lean \
    -o outputs/mhd_spec.c.mlir

# 4. Converter para C
mlir-translate --mlir-to-c outputs/mhd_spec.c.mlir -o outputs/solver.c

# 5. Gerar G‑code (geometria)
mlir-translate --mlir-to-gcode outputs/mhd_spec.c.mlir -o outputs/coils.gcode

# 6. Gerar VHDL (hardware)
mlir-translate --mlir-to-vhdl outputs/mhd_spec.c.mlir -o outputs/plasma_accel.vhdl

# 7. Ancorar artefatos
echo "🔹 Ancorando artefatos..."
python3 integrations/artifact_anchor/anchor.py \
    --source integrations/idealMHD/mhd_spec.mlir \
    --artifact outputs/solver.c \
    --passes "$PIPELINE_PASSES"
python3 integrations/artifact_anchor/anchor.py \
    --source integrations/idealMHD/mhd_spec.mlir \
    --artifact outputs/coils.gcode \
    --passes "$PIPELINE_PASSES"
python3 integrations/artifact_anchor/anchor.py \
    --source integrations/idealMHD/mhd_spec.mlir \
    --artifact outputs/plasma_accel.vhdl \
    --passes "$PIPELINE_PASSES"

echo "✅ Teste E2E concluído com sucesso!"
echo "   Artefatos gerados em outputs/"
