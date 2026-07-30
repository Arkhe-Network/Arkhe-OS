#!/usr/bin/env bash
set -e

echo "======================================"
echo "Initializing Cathedral ARKHE v28.3 Stack"
echo "======================================"

# 1. Check for required dependencies
command -v docker >/dev/null 2>&1 || { echo >&2 "Docker is required but it's not installed. Aborting."; exit 1; }
command -v cargo >/dev/null 2>&1 || { echo >&2 "Rust (cargo) is required but it's not installed. Aborting."; exit 1; }

echo "[+] Dependencies OK."

# 2. Build the Rust orchestrator (if necessary)
echo "[+] Building Orchestrator..."
cd orchestrator
cargo build --release || { echo >&2 "Cargo build failed. Aborting."; exit 1; }
cd ..

# 3. Create necessary data directories for docker-compose
echo "[+] Setting up volume directories..."
mkdir -p runtime/models runtime/agent runtime/core runtime/trust
cp -r agent/* runtime/agent/ 2>/dev/null || true
cp -r core/* runtime/core/ 2>/dev/null || true
cp -r trust/* runtime/trust/ 2>/dev/null || true

# 4. Start the stack
echo "[+] Starting Docker Compose stack..."
cd runtime
docker-compose up -d --build

echo "======================================"
echo "Stack is starting in the background."
echo "Use 'docker-compose logs -f' to monitor."
echo "======================================"
