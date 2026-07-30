#!/usr/bin/env python3
"""
CATHEDRAL ARKHE — Supply Chain Verification Script v1.0
Verifica a integridade do binário Rust antes do carregamento FFI.
Impede ataques de cadeia de suprimentos (Supply Chain Attacks).
"""
import os
import sys
import hashlib
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

EXPECTED_HASHES = {
    # Hash SHA3-256 do .so gerado pelo 'cargo auditable build'
    # ATUALIZE ESTE VALOR após a primeira compilação bem-sucedida!
    "libcathedral_blockchain.so": "40a80de0ee2d72ddae92a31e0bbb4b923c0ea4fd49bd2028bdd74a8730d437ad"
}

def verify_library(lib_path: str) -> bool:
    lib_name = os.path.basename(lib_path)

    if not os.path.exists(lib_path):
        logging.error(f"Arquivo não encontrado: {lib_path}")
        return False

    expected_hash = EXPECTED_HASHES.get(lib_name)
    if not expected_hash or expected_hash == "COLOQUE_O_HASH_AQUI_APOS_COMPILAR":
        logging.warning(f"Hash de auditoria não configurado para {lib_name}. Verifique manualmente.")
        return True # Permite passagem em modo dev

    logging.info(f"Lendo binário: {lib_path} ({os.path.getsize(lib_path)} bytes)...")

    # Calcula SHA3-256 (Keccak-256)
    sha3 = hashlib.sha3_256()
    with open(lib_path, "rb") as f:
        while chunk := f.read(8192):
            sha3.update(chunk)

    real_hash = sha3.hexdigest()

    if real_hash == expected_hash:
        logging.info(f"✅ SUPPLY CHAIN VERIFIED: {lib_name} é íntegro.")
        logging.info(f"   Hash: {real_hash[:32]}...")
        return True
    else:
        logging.critical(f"❌ VIOLAÇÃO DE SUPPLY CHAIN em {lib_name}!")
        logging.critical(f"   Esperado: {expected_hash[:32]}...")
        logging.critical(f"   Encontrado: {real_hash[:32]}...")
        return False

if __name__ == "__main__":
    lib_path = sys.argv[1] if len(sys.argv) > 1 else "target/release/libcathedral_blockchain.so"

    if not verify_library(lib_path):
        sys.exit(1) # Aborta o kernel da ARKHE imediatamente
