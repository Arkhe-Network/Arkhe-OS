#!/usr/bin/env python3
import pytest
import jwt
import time
from pathlib import Path
from substrate_212 import (
    KeyManager,
    CertificateGateway,
    is_frequency_allowed,
    get_restriction_reason,
)

@pytest.fixture
def temp_key_path(tmp_path):
    return str(tmp_path / "test_key.pem")

@pytest.fixture
def gateway(temp_key_path):
    return CertificateGateway(key_path=temp_key_path)

def test_key_persistence(temp_key_path):
    km1 = KeyManager(temp_key_path)
    assert Path(temp_key_path).exists()
    km2 = KeyManager(temp_key_path)
    n1 = km1.private_key.private_numbers().public_numbers.n
    n2 = km2.private_key.private_numbers().public_numbers.n
    assert n1 == n2

def test_jwt_rs256(gateway):
    token = gateway.issue_jwt("test-user", "admin")
    payload = gateway.verify_jwt(token)
    assert payload["sub"] == "test-user"
    assert payload["scope"] == "admin"
    assert payload["iss"] == "cathedral://substrate-212"
    assert "exp" in payload
    assert "iat" in payload

def test_jwt_expired(gateway):
    payload = {"sub": "test", "exp": int(time.time()) - 10}
    token = gateway.key_manager.sign_jwt(payload)
    with pytest.raises(jwt.ExpiredSignatureError):
        gateway.verify_jwt(token)

def test_certificate_generation(gateway):
    cert_data = gateway.generate_certificate("test.cathedral.local", ["test.cathedral.local"])
    assert "BEGIN CERTIFICATE" in cert_data["certificate"]
    assert "PRIVATE KEY" in cert_data["private_key"]
    assert cert_data["common_name"] == "test.cathedral.local"

def test_anatel_frequencies():
    assert is_frequency_allowed(100.0) is False      # FM (87.8-108)
    assert is_frequency_allowed(120.0) is False     # Aviação
    assert is_frequency_allowed(121.5) is False     # Emergência
    assert is_frequency_allowed(433.05) is True     # ISM (exceção)
    assert is_frequency_allowed(915.0) is True      # ISM
    assert is_frequency_allowed(406.05) is False    # COSPAS
    assert is_frequency_allowed(1559.0) is False    # GNSS
    assert is_frequency_allowed(2400.0) is True     # ISM

def test_anatel_reason():
    assert "emergência" in get_restriction_reason(121.5).lower() or "Emergência" in get_restriction_reason(121.5)
    assert "aviação" in get_restriction_reason(120.0).lower() or "Aviação" in get_restriction_reason(120.0)
    assert "cospas-sarsat" in get_restriction_reason(406.05).lower() or "COSPAS-SARSAT" in get_restriction_reason(406.05)
    assert get_restriction_reason(915.0) == ""

def test_ct_logs(gateway):
    result = gateway.check_ct_logs("github.com")
    if result["status"] == "success":
        assert "logs" in result
        assert isinstance(result["logs"], list)
    else:
        pytest.skip("crt.sh indisponível no momento")

def test_vault_fallback(gateway):
    assert gateway.vault.is_available() is False
    assert gateway.vault_read("secret/test") is None
    assert gateway.vault_write("secret/test", {}) is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
