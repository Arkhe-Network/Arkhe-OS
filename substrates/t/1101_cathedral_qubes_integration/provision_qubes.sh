#!/bin/bash
# ============================================================
# CATHEDRAL ARKHE v12.0 — Provisionamento de Qubes OS
# Selo: CATHEDRAL-QUBES-1101-v1.0.0-2026-06-12
# ============================================================

set -e

echo "[+] Clonando template base (fedora-39-minimal)..."
qvm-clone fedora-39-minimal cathedral-template

echo "[+] Instalando dependencias no template..."
qvm-run -u root cathedral-template "dnf install -y python3 python3-pip rust cargo golang postgresql-server postgresql-contrib"
qvm-run -u root cathedral-template "cargo install blst"
qvm-run -u root cathedral-template "dnf upgrade -y"

echo "[+] Provisionando agi-core (Brain)..."
qvm-create -l red -t cathedral-template agi-core
qvm-prefs agi-core netvm sys-firewall
qvm-prefs agi-core provides_network false
qvm-prefs agi-core memory 4096
qvm-prefs agi-core maxmem 8192
qvm-prefs agi-core vcpus 4

echo "[+] Provisionando llm-inference (Mind)..."
qvm-create -l black -t cathedral-template llm-inference
qvm-prefs llm-inference netvm none
qvm-prefs llm-inference memory 16384
qvm-prefs llm-inference maxmem 32768
qvm-prefs llm-inference vcpus 8
# Note: GPU passthrough requires manual PCI BDF detection
echo "[!] Lembrete: Execute 'qvm-pci attach llm-inference dom0:<BDF> --persistent' para a GPU."

echo "[+] Provisionando knowledge-base (Memory)..."
qvm-create -l black -t cathedral-template knowledge-base
qvm-prefs knowledge-base netvm none
qvm-prefs knowledge-base memory 4096
qvm-prefs knowledge-base maxmem 8192

echo "[+] Provisionando governance (Conscience)..."
qvm-create -l black -t cathedral-template governance
qvm-prefs governance netvm none
qvm-prefs governance memory 2048
qvm-prefs governance maxmem 4096

echo "[+] Provisionando crypto-vm (Air-gapped)..."
qvm-create -l black -t cathedral-template crypto-vm
qvm-prefs crypto-vm netvm none
qvm-prefs crypto-vm memory 2048

echo "[+] Provisionando VMs de acao (Muscles)..."
qvm-create -l yellow -t cathedral-template browser-vm
qvm-prefs browser-vm netvm sys-whonix
qvm-prefs browser-vm memory 2048

qvm-create -l yellow -t cathedral-template email-vm
qvm-prefs email-vm netvm sys-firewall
qvm-prefs email-vm memory 2048

qvm-create -l yellow -t cathedral-template code-vm
qvm-prefs code-vm netvm sys-firewall
qvm-prefs code-vm memory 4096

echo "[+] Provisionando dispVM template..."
qvm-create -l green -t cathedral-template cathedral-dvm
qvm-prefs cathedral-dvm template_for_dispvms True

echo "[+] Provisionamento concluido."
