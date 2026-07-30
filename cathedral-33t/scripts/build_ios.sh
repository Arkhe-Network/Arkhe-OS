#!/bin/bash
set -e

# Instalar cargo-lipo se não estiver instalado
if ! command -v cargo-lipo &> /dev/null; then
    cargo install cargo-lipo
fi

# Build para iOS com Metal
cargo lipo --release --features "tensor-backend-metal"

# Gerar XCFramework
mkdir -p mobile/ios/Cathedral.xcframework
# Usar xcodebuild para criar o framework

echo "iOS build complete"