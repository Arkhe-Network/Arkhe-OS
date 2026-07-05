from pathlib import Path

import pytest

from substrate_251.orcid import (
    ArkheOrcidOracle,
    OrcidOAuthConfig,
    TokenArkheBusBridge,
    WalletSignatureProof,
    is_valid_orcid,
)
from substrate_251.orcid.orcid_oracle import OrcidOAuthClient


WALLET = "0x1111111111111111111111111111111111111111"
ORCID = "0009-0005-2697-4668"


def test_orcid_validator_accepts_canonical_and_checksum_x():
    assert is_valid_orcid(ORCID)
    assert is_valid_orcid("0000-0002-1825-009X")
    assert not is_valid_orcid("0009000526974668")
    assert not is_valid_orcid("0009-0005-2697-466Z")


def test_orcid_oauth_client_builds_sandbox_authorization_url():
    config = OrcidOAuthConfig(
        client_id="APP-ARKHE",
        client_secret="secret",
        redirect_uri="https://arkhe.example/callback",
    )
    client = OrcidOAuthClient(config)
    url = client.authorization_url("state-123")
    assert url.startswith("https://sandbox.orcid.org/oauth/authorize?")
    assert "client_id=APP-ARKHE" in url
    assert "scope=%2Fauthenticate" in url


def test_orcid_oracle_attestation_has_solidity_args():
    oracle = ArkheOrcidOracle("arkhe-oracle-1", "local-dilithium-secret")
    wallet_proof = WalletSignatureProof(
        wallet=WALLET,
        message=oracle.build_wallet_challenge(WALLET, ORCID, "nonce-1"),
        signature="0x" + "ab" * 65,
        signed_at=1779119844,
    )
    oauth_proof = oracle.build_oauth_proof(ORCID, "orcid-access-token", wallet_proof)
    attestation = oracle.attest(WALLET, oauth_proof, erc8004_token_id=8004)
    args = attestation.solidity_args()

    assert len(attestation.oauth_proof_hash) == 64
    assert len(attestation.pqc_signature) >= 64
    assert len(attestation.temporal_chain_seal) == 64
    assert args["wallet"] == WALLET
    assert args["oauthProofHash"].startswith("0x")
    assert args["erc8004TokenId"] == 8004


def test_orcid_oracle_rejects_invalid_wallet_and_orcid():
    oracle = ArkheOrcidOracle("arkhe-oracle-1", "local-dilithium-secret")
    with pytest.raises(ValueError):
        oracle.build_wallet_challenge("0x1234", ORCID, "nonce")
    with pytest.raises(ValueError):
        oracle.build_wallet_challenge(WALLET, "bad-orcid", "nonce")


def test_token_arkhe_bus_bridge_writes_sealed_event(tmp_path: Path):
    oracle = ArkheOrcidOracle("arkhe-oracle-1", "local-dilithium-secret")
    wallet_proof = WalletSignatureProof(WALLET, "message", "0xabc", 1779119844)
    oauth_proof = oracle.build_oauth_proof(ORCID, "orcid-access-token", wallet_proof)
    attestation = oracle.attest(WALLET, oauth_proof, erc8004_token_id=8004)

    spool = tmp_path / "identity.jsonl"
    envelope = TokenArkheBusBridge(spool).emit_orcid_verified(attestation)

    assert envelope.event_type == "ORCID_VERIFIED"
    assert envelope.payload["orcid_id"] == ORCID
    assert len(envelope.canonical_seal) == 64
    assert "ORCID_VERIFIED" in spool.read_text(encoding="utf-8")


def test_arkhe_orcid_identity_contract_contains_required_controls():
    root = Path(__file__).resolve().parents[1]
    contract = root / "usage/financial_services/contracts/ArkheOrcidIdentity.sol"
    source = contract.read_text(encoding="utf-8")

    assert "contract ArkheOrcidIdentity" in source
    assert "mapping(address => bool) public authorizedOracles" in source
    assert "function verifyOrcid(" in source
    assert "function revokeOrcid(" in source
    assert "function linkErc8004Token(" in source
    assert "event OrcidVerified" in source
    assert "event Erc8004Linked" in source
    assert "_isValidOrcid" in source
