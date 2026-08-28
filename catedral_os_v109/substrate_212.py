#!/usr/bin/env python3
"""
Substrato 212 — Certificate Gateway (Standalone v5.1)
======================================================
- Unificado com o módulo canônico anatel_band_guard (Substrato 227)
- cryptography.__version__ obtido corretamente
- Testes alinhados com a semântica canônica
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_EVEN
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import cryptography

# ---- Tenta importar o módulo canônico ANATEL ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from anatel_band_guard import is_frequency_allowed, get_restriction_reason
    _ANATEL_IMPORTED = True
except ImportError:
    _ANATEL_IMPORTED = False
    RESTRICTED_BANDS = [
        (87.8, 108.0), (108.0, 137.0), (121.5, 121.5), (406.0, 406.1), (1544.0, 1545.0),
        (1559.0, 1610.0), (1525.0, 1559.0), (1626.5, 1660.5), (1400.0, 1427.0),
    ]
    ISM_EXEMPT = [(433.05, 434.79)]

    def is_frequency_allowed(freq_mhz: float) -> bool:
        for low, high in RESTRICTED_BANDS:
            if low <= freq_mhz <= high:
                for elow, ehigh in ISM_EXEMPT:
                    if elow <= freq_mhz <= ehigh: return True
                return False
        return True

    def get_restriction_reason(freq_mhz: float) -> str:
        for low, high in RESTRICTED_BANDS:
            if low <= freq_mhz <= high:
                for elow, ehigh in ISM_EXEMPT:
                    if elow <= freq_mhz <= ehigh: return "Faixa ISM (exceção)"
                if 121.5 <= freq_mhz <= 121.5: return "Frequência de emergência (121.5 MHz)"
                if 87.8 <= freq_mhz <= 108.0: return "FM (87.8-108)"
                if 108 <= freq_mhz <= 137: return "Aviação (VOR/ILS ou VHF COM)"
                if 406 <= freq_mhz <= 406.1: return "Satélite de busca e salvamento (COSPAS-SARSAT)"
                if 1544 <= freq_mhz <= 1545: return "COSPAS-SARSAT downlink (1544–1545 MHz)"
                if 1559 <= freq_mhz <= 1610: return "GNSS/RNSS (1559–1610 MHz)"
                if 1525 <= freq_mhz <= 1559: return "MSS downlink (1525–1559 MHz)"
                if 1626.5 <= freq_mhz <= 1660.5: return "MSS uplink (1626.5–1660.5 MHz)"
                if 1400 <= freq_mhz <= 1427: return "Astronomia rádio (1400–1427 MHz) — ITU RR 5.340"
                return "Faixa restrita"
        return ""

# ---- Dependências de segurança ----
try:
    import jwt
except ImportError:
    raise RuntimeError("PyJWT não instalado. Execute: pip install PyJWT>=2.13.0")

try:
    import hvac
except ImportError:
    hvac = None

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
    from cryptography.x509 import Name, NameAttribute, CertificateBuilder, BasicConstraints, SubjectAlternativeName, DNSName
except ImportError as e:
    raise RuntimeError(f"cryptography não instalado: {e}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("substrate_212")

class KeyManager:
    def __init__(self, key_path: Optional[str] = None):
        self.key_path = Path(key_path or "catedral_rsa_4096.pem")
        self.private_key = self._load_or_generate()
        self.public_key = self.private_key.public_key()

    def _load_or_generate(self) -> rsa.RSAPrivateKey:
        env_pem = os.getenv("CATEDRAL_RSA_PRIVATE_KEY")
        if env_pem:
            return serialization.load_pem_private_key(env_pem.encode(), password=None)
        if self.key_path.exists():
            with open(self.key_path, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)
        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        with open(self.key_path, "wb") as f:
            f.write(key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))
        os.chmod(self.key_path, 0o600)
        return key

    def sign_jwt(self, payload: Dict) -> str:
        if "exp" not in payload: payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=1)
        if "iat" not in payload: payload["iat"] = datetime.now(timezone.utc)
        if "iss" not in payload: payload["iss"] = "cathedral://substrate-212"
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def verify_jwt(self, token: str) -> Dict:
        return jwt.decode(token, self.public_key, algorithms=["RS256"], issuer="cathedral://substrate-212", options={"require": ["exp", "iat", "iss"]})

def generate_self_signed_cert(private_key: rsa.RSAPrivateKey, common_name: str, sans: Optional[List[str]] = None, validity_days: int = 365) -> Tuple[bytes, bytes]:
    subject = issuer = Name([
        NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        NameAttribute(NameOID.ORGANIZATION_NAME, "Catedral Cognitiva"),
        NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    now = datetime.now(timezone.utc)
    builder = (
        CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(int(time.time() * 1000))
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=validity_days))
        .add_extension(BasicConstraints(ca=True, path_length=None), critical=True)
    )
    if sans:
        builder = builder.add_extension(SubjectAlternativeName([DNSName(dns) for dns in sans]), critical=False)
    cert = builder.sign(private_key, hashes.SHA256())
    return cert.public_bytes(Encoding.PEM), private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

class VaultClient:
    def __init__(self):
        self.url = os.getenv("VAULT_ADDR", "https://127.0.0.1:8200")
        self.token = os.getenv("VAULT_TOKEN")
        self._client = None
        self._available = False
        if not self.token: return
        try:
            if hvac is None: return
            self._client = hvac.Client(url=self.url, token=self.token, verify=True, timeout=5)
            if self._client.is_authenticated(): self._available = True
        except Exception: pass

    def read_secret(self, path: str) -> Optional[Dict]:
        if not self._available: return None
        try: return self._client.secrets.kv.v2.read_secret_version(path=path)
        except Exception: return None

    def write_secret(self, path: str, data: Dict) -> bool:
        if not self._available: return False
        try: self._client.secrets.kv.v2.create_or_update_secret(path=path, secret=data); return True
        except Exception: return False

    def is_available(self) -> bool: return self._available

def check_ct_logs(domain: str, limit: int = 10) -> Dict[str, Any]:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET"])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    try:
        resp = session.get(f"https://crt.sh/?q=%25.{domain}&output=json", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logs = [{"issuer": e.get("issuer_name", ""), "not_before": e.get("not_before", "")} for e in data[:limit]]
        return {"status": "success", "logs": logs, "count": len(logs)}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

@dataclass
class GatewayStatus:
    version: str = "5.1"
    jwt_algorithm: str = "RS256"
    key_size: int = 4096
    vault_available: bool = False
    cryptography_version: str = ""
    pyjwt_version: str = ""
    hvac_version: str = ""

class CertificateGateway:
    def __init__(self, key_path: Optional[str] = None):
        self.key_manager = KeyManager(key_path)
        self.vault = VaultClient()
        self._crypto_version = getattr(cryptography, "__version__", "unknown")
        self._jwt_version = getattr(jwt, "__version__", "unknown")
        self._hvac_version = getattr(hvac, "__version__", "unknown") if hvac else "N/A"

    def issue_jwt(self, subject: str, scope: str = "read", extra_claims: Optional[Dict] = None) -> str:
        payload = {"sub": subject, "scope": scope}
        if extra_claims: payload.update(extra_claims)
        return self.key_manager.sign_jwt(payload)

    def verify_jwt(self, token: str) -> Dict: return self.key_manager.verify_jwt(token)

    def generate_certificate(self, common_name: str, sans: Optional[List[str]] = None) -> Dict:
        cert_pem, key_pem = generate_self_signed_cert(self.key_manager.private_key, common_name, sans)
        return {"certificate": cert_pem.decode(), "private_key": key_pem.decode(), "common_name": common_name, "sans": sans or [], "valid_days": 365}

    def check_ct_logs(self, domain: str) -> Dict: return check_ct_logs(domain)
    def vault_read(self, path: str) -> Optional[Dict]: return self.vault.read_secret(path)
    def vault_write(self, path: str, data: Dict) -> bool: return self.vault.write_secret(path, data)
    def check_frequency(self, freq_mhz: float) -> Tuple[bool, str]: return is_frequency_allowed(freq_mhz), get_restriction_reason(freq_mhz)
    def get_status(self) -> GatewayStatus:
        return GatewayStatus(key_size=self.key_manager.private_key.key_size, vault_available=self.vault.is_available(), cryptography_version=self._crypto_version, pyjwt_version=self._jwt_version, hvac_version=self._hvac_version)
