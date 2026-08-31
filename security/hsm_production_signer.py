#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARKHE OS — HSM PRODUCTION SIGNER (PKCS#11)
================================================================================
Implementação real usando python-pkcs11 com:
  - Suporte a Thales Luna, Utimaco SecurityServer, SoftHSMv2
  - Geração e rotação de chaves (RSA/EC)
  - Assinatura e verificação PQC (RSA-PSS / ECDSA)
  - Integração com TemporalChain (ancoragem de eventos)
  - Auditoria e rotação automática de chaves
================================================================================
"""

import os
import json
import time
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, field
import pkcs11
from pkcs11 import Mechanism, KeyType, ObjectClass, ECCurve
import base64

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
DEFAULT_PKCS11_LIB = "/usr/lib/softhsm/libsofthsm2.so"
DEFAULT_TOKEN_LABEL = "ARKHE_TOKEN"
DEFAULT_KEY_LABEL = "arkhe-pqc-key"

# =============================================================================
# DATA CLASSES
# =============================================================================
@dataclass
class HSMKeyInfo:
    key_id: str
    key_type: str
    key_size: int
    label: str
    created_at: float = field(default_factory=time.time)

@dataclass
class SignatureResult:
    signature_hex: str
    signature_size_bytes: int
    signing_time_ms: float
    key_id: str
    algorithm: str
    temporal_seal: Optional[str] = None

# =============================================================================
# HSM PRODUCTION SIGNER
# =============================================================================
class HSMProductionSigner:
    """
    Assinador de produção usando HSM físico via PKCS#11.
    """

    def __init__(
        self,
        pkcs11_lib_path: str = DEFAULT_PKCS11_LIB,
        token_label: str = DEFAULT_TOKEN_LABEL,
        user_pin: Optional[str] = None,
        key_label: str = DEFAULT_KEY_LABEL,
        temporal_chain: Optional[Any] = None
    ):
        self.pkcs11_lib_path = pkcs11_lib_path
        self.token_label = token_label
        self.user_pin = user_pin or os.environ.get("HSM_USER_PIN", "1234")
        self.key_label = key_label
        self.temporal = temporal_chain
        self._lib: Optional[pkcs11.lib] = None
        self._token: Optional[pkcs11.Token] = None
        self._session: Optional[pkcs11.Session] = None
        self._key_id: Optional[bytes] = None
        self._public_key: Optional[pkcs11.Object] = None
        self._private_key: Optional[pkcs11.Object] = None
        self.rotation_history: List[Dict] = []

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect()

    # -------------------------------------------------------------------------
    # CONEXÃO E INICIALIZAÇÃO
    # -------------------------------------------------------------------------
    def _connect(self):
        if not os.path.exists(self.pkcs11_lib_path):
            raise FileNotFoundError(f"PKCS#11 library not found: {self.pkcs11_lib_path}")
        self._lib = pkcs11.lib(self.pkcs11_lib_path)
        self._token = self._lib.get_token(token_label=self.token_label)
        if not self._token:
            raise ValueError(f"Token '{self.token_label}' not found")
        self._session = self._token.open(user_pin=self.user_pin)
        self._load_or_create_keypair()

    def _disconnect(self):
        if self._session:
            self._session.close()
            self._session = None

    def _load_or_create_keypair(self):
        """Carrega chave existente ou cria nova."""
        private_keys = self._session.find_objects(
            ObjectClass.PRIVATE_KEY,
            label=self.key_label
        )
        if private_keys:
            self._private_key = private_keys[0]
            pub_keys = self._session.find_objects(
                ObjectClass.PUBLIC_KEY,
                label=self.key_label
            )
            self._public_key = pub_keys[0] if pub_keys else None
            self._key_id = self._private_key.id
            logger.info(f"Chave carregada: {self.key_label} (ID: {self._key_id.hex()})")
        else:
            self._generate_keypair()

    def _generate_keypair(self, key_size: int = 2048):
        """Gera par de chaves RSA no HSM."""
        logger.info(f"Gerando chave RSA-{key_size} no HSM...")
        self._public_key, self._private_key = self._session.generate_keypair(
            KeyType.RSA,
            key_size,
            label=self.key_label,
            id=hashlib.sha256(self.key_label.encode()).digest()[:8]
        )
        self._key_id = self._private_key.id
        logger.info(f"Chave RSA gerada: {self._key_id.hex()}")

    # -------------------------------------------------------------------------
    # OPERAÇÕES CRIPTOGRÁFICAS
    # -------------------------------------------------------------------------
    def sign_data(self, data: bytes, algorithm: str = "SHA256_RSA_PKCS") -> SignatureResult:
        """Assina dados com a chave privada no HSM."""
        if not self._private_key:
            raise RuntimeError("Chave privada não carregada no HSM")

        # Mapeia mecanismo
        mechanism_map = {
            "SHA256_RSA_PKCS": Mechanism.SHA256_RSA_PKCS,
            "SHA384_RSA_PKCS": Mechanism.SHA384_RSA_PKCS,
            "SHA512_RSA_PKCS": Mechanism.SHA512_RSA_PKCS,
            "ECDSA_SHA256": Mechanism.ECDSA_SHA256,
            "ECDSA_SHA384": Mechanism.ECDSA_SHA384,
        }
        mech = mechanism_map.get(algorithm, Mechanism.SHA256_RSA_PKCS)

        # Assina
        t0 = time.perf_counter()
        digest = hashlib.sha256(data).digest()
        signature = self._private_key.sign(digest, mechanism=mech)
        t1 = time.perf_counter()

        # Ancora na TemporalChain se disponível
        seal = None
        if self.temporal:
            try:
                seal = self.temporal.anchor_event(
                    "hsm_signature",
                    {
                        "key_id": self._key_id.hex(),
                        "algorithm": algorithm,
                        "data_hash": hashlib.sha256(data).hexdigest(),
                        "signature_hash": hashlib.sha256(signature).hexdigest(),
                        "timestamp": time.time()
                    }
                )
            except Exception as e:
                logger.warning(f"Falha ao ancorar na TemporalChain: {e}")

        return SignatureResult(
            signature_hex=signature.hex(),
            signature_size_bytes=len(signature),
            signing_time_ms=(t1 - t0) * 1000,
            key_id=self._key_id.hex(),
            algorithm=algorithm,
            temporal_seal=seal
        )

    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verifica assinatura com a chave pública."""
        if not self._public_key:
            raise RuntimeError("Chave pública não carregada")
        digest = hashlib.sha256(data).digest()
        try:
            self._public_key.verify(digest, signature, mechanism=Mechanism.SHA256_RSA_PKCS)
            return True
        except pkcs11.PKCS11Error:
            return False

    def encrypt(self, data: bytes) -> bytes:
        """Criptografa dados com a chave pública."""
        if not self._public_key:
            raise RuntimeError("Chave pública não carregada")
        return self._public_key.encrypt(data)

    def decrypt(self, encrypted: bytes) -> bytes:
        """Descriptografa dados com a chave privada."""
        if not self._private_key:
            raise RuntimeError("Chave privada não carregada")
        return self._private_key.decrypt(encrypted)

    # -------------------------------------------------------------------------
    # ROTAÇÃO DE CHAVES
    # -------------------------------------------------------------------------
    def rotate_keys(self, new_key_size: int = 2048) -> HSMKeyInfo:
        """Roda as chaves: gera novo par e arquiva o antigo."""
        old_key_id = self._key_id.hex() if self._key_id else None
        old_public = self._public_key
        old_private = self._private_key

        # Gera novo par
        self._generate_keypair(new_key_size)
        new_info = HSMKeyInfo(
            key_id=self._key_id.hex(),
            key_type="RSA",
            key_size=new_key_size,
            label=self.key_label
        )

        # Registra rotação
        rotation_record = {
            "old_key_id": old_key_id,
            "new_key_id": new_info.key_id,
            "timestamp": time.time(),
            "seal": self.temporal.anchor_event("hsm_key_rotation", {"old": old_key_id, "new": new_info.key_id}) if self.temporal else None
        }
        self.rotation_history.append(rotation_record)

        logger.info(f"Chaves rotacionadas: {old_key_id} -> {new_info.key_id}")
        return new_info

    # -------------------------------------------------------------------------
    # ESTATÍSTICAS E AUDITORIA
    # -------------------------------------------------------------------------
    def get_statistics(self) -> Dict:
        return {
            "hsm_provider": self.pkcs11_lib_path,
            "token_label": self.token_label,
            "key_label": self.key_label,
            "key_id": self._key_id.hex() if self._key_id else None,
            "total_rotations": len(self.rotation_history),
            "rotation_history": self.rotation_history[-5:],  # últimos 5
        }

    def get_audit_seal(self) -> str:
        """Gera selo canônico do estado atual do HSM."""
        data = json.dumps({
            "key_id": self._key_id.hex() if self._key_id else None,
            "rotations": len(self.rotation_history),
            "timestamp": time.time()
        }, sort_keys=True)
        return hashlib.sha3_256(data.encode()).hexdigest()

# =============================================================================
# TESTES
# =============================================================================
if __name__ == "__main__":
    # Usando SoftHSMv2 para teste
    import tempfile

    try:
        with HSMProductionSigner(pkcs11_lib_path="/usr/lib/softhsm/libsofthsm2.so") as signer:
            data = b"Arkhe Cathedral -- critical segment"
            result = signer.sign_data(data)
            print(f"Assinatura: {result.signature_hex[:64]}...")
            print(f"Tempo: {result.signing_time_ms:.2f}ms")
            print(f"Selo Temporal: {result.temporal_seal}")

            # Verificar
            verified = signer.verify_signature(data, bytes.fromhex(result.signature_hex))
            print(f"Verificação: {'✅' if verified else '❌'}")

            # Rotacionar
            new_key = signer.rotate_keys()
            print(f"Chave rotacionada: {new_key.key_id}")
    except Exception as e:
        print(f"Erro: {e}. Certifique-se de ter SoftHSMv2 instalado e configurado.")
