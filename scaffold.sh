#!/bin/bash
set -e

mkdir -p crates
cd crates

for crate in cathedral-identity cathedral-wormgraph cathedral-zk cathedral-harness cathedral-orchestration cathedral-tools cathedral-permissions cathedral-self-improve cathedral-remix-bridge cathedral-server; do
    cargo new --lib $crate 2>/dev/null || true
done

cargo new --bin cathedral-cli 2>/dev/null || true

cd ..
