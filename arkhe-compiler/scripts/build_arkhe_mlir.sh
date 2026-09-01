#!/bin/bash
# build_arkhe_mlir.sh – Compila o MLIR com o dialeto arkhe

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
MLIR_DIR="$ROOT_DIR/mlir"
BUILD_DIR="$MLIR_DIR/build"

# Clone MLIR se não existir (para CI)
if [ ! -d "$MLIR_DIR/llvm-project" ]; then
    echo "Clonando LLVM/MLIR..."
    git clone --depth 1 --branch llvmorg-18.1.8 https://github.com/llvm/llvm-project.git "$MLIR_DIR/llvm-project"
fi

# Configuração
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_PROJECTS=mlir \
    -DLLVM_TARGETS_TO_BUILD="X86;NVPTX" \
    -DLLVM_ENABLE_ASSERTIONS=ON \
    -DLLVM_INSTALL_UTILS=ON \
    -DMLIR_ENABLE_BINDINGS_PYTHON=ON \
    -DCMAKE_C_COMPILER=clang \
    -DCMAKE_CXX_COMPILER=clang++ \
    "$MLIR_DIR/llvm-project/llvm"

# Compilar
ninja mlir-opt
ninja mlir-translate

# Compilar o dialeto Arkhe (adicionado como subdiretório)
# Assume que o dialeto está em $MLIR_DIR/arkhe-dialect/
ln -sf "$MLIR_DIR/arkhe-dialect" "$BUILD_DIR/lib/arkhe"
ninja ArkheDialect

echo "✅ Dialeto Arkhe compilado com sucesso!"
echo "   mlir-opt: $BUILD_DIR/bin/mlir-opt"
echo "   Dialeto: $BUILD_DIR/lib/libArkheDialect.so"
