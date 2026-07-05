import math
from pathlib import Path

import pytest

from substrates.substrate_342 import (
    BountyStatus,
    CodePlagiarismEngine,
    HashtreeAnchorClient,
    OrkutLabsDev,
    PublicRepositoryIndex,
    ReviewVerdict,
    canonical_cid,
    compute_merkle_root,
    generate_merkle_proof,
    is_valid_orcid,
    merkle_leaf,
    verify_merkle_proof,
)
from substrates.substrate_342.orkut_labs_dev import GAP_MAX, GHOST, LOOPSEAL, PHI


ORCID = "orcid:0009-0005-2697-4668"
OTHER_ORCID = "orcid:0000-0002-1825-0097"


def test_orcid_identity_and_invariants():
    labs = OrkutLabsDev()
    profile = labs.register_developer(ORCID, "Arkhe Dev", "0x1111111111111111111111111111111111111111")

    assert is_valid_orcid(profile.orcid)
    assert len(profile.identity_seal) == 64
    assert math.isclose(GHOST, math.sqrt(3) / 3)
    assert math.isclose(LOOPSEAL, math.pi / 9)
    assert GAP_MAX < 1.0
    assert math.isclose(PHI, (1 + math.sqrt(5)) / 2)


def test_repository_commit_generates_ipfs_cids_and_append_only_history():
    labs = OrkutLabsDev()
    labs.register_developer(ORCID, "Arkhe Dev", "0x1111111111111111111111111111111111111111")
    repo = labs.create_repository(ORCID, "tau-contracts", "Substrate 342 contracts")

    commit = labs.commit_code(
        "tau-contracts",
        ORCID,
        {"BountyRegistry.sol": "contract BountyRegistry { event Paid(uint256 id); }"},
        "Add bounty registry",
    )

    assert commit.nonce == 0
    assert commit.ipfs_cid.startswith("bafyarkhe342")
    assert commit.file_cids["BountyRegistry.sol"] == canonical_cid("contract BountyRegistry { event Paid(uint256 id); }")
    assert repo.head == commit
    assert len(repo.commits) == 1
    assert commit.hashtree_anchor is not None
    assert commit.hashtree_anchor.share_url.startswith("https://hashtree.cc/#")
    assert len(commit.hashtree_anchor.canonical_seal) == 64
    assert len(commit.merkle_root) == 64
    assert "BountyRegistry.sol" in commit.merkle_proofs
    assert verify_merkle_proof(commit.merkle_proofs["BountyRegistry.sol"])


def test_merkle_proof_detects_tampering():
    leaves = [
        merkle_leaf("a.sol", "contract A {}"),
        merkle_leaf("b.sol", "contract B {}"),
        merkle_leaf("c.sol", "contract C {}"),
    ]
    proof = generate_merkle_proof(leaves, 1)

    assert proof.root == compute_merkle_root(leaves)
    assert verify_merkle_proof(proof)

    tampered = proof.to_payload()
    tampered["leaf"] = merkle_leaf("b.sol", "contract Evil {}")
    assert not verify_merkle_proof(tampered)


def test_plagiarism_engine_detects_renamed_structural_clone():
    code_a = """
contract Vault {
    mapping(address => uint256) public balance;
    function release(address user) external {
        require(balance[user] > 0, "empty");
        balance[user] = 0;
    }
}
"""
    code_b = """
contract Treasury {
    mapping(address => uint256) public credit;
    function withdraw(address account) external {
        require(credit[account] > 0, "none");
        credit[account] = 0;
    }
}
"""

    result = CodePlagiarismEngine().detect_plagiarism(code_a, code_b)

    assert result["verdict"] in {"MEDIUM", "HIGH"}
    assert result["attribution_required"] is True
    assert result["similarity"] <= GAP_MAX
    assert verify_merkle_proof(result["merkle_proof"])
    assert len(result["merkle_root"]) == 64
    assert len(result["canonical_seal"]) == 64


def test_ai_code_review_blocks_high_similarity_and_warns_on_tx_origin():
    labs = OrkutLabsDev()
    code = "contract A { function auth() external { require(tx.origin == msg.sender, 'bad'); } }"
    review = labs.review_code(code, reference_code=code, language="solidity")

    assert review.verdict == ReviewVerdict.BLOCK
    assert any("tx.origin" in issue for issue in review.issues)
    assert len(review.canonical_seal) == 64


def test_bounty_lifecycle_settles_with_x402_receipt():
    labs = OrkutLabsDev()
    labs.register_developer(ORCID, "Sponsor", "0x1111111111111111111111111111111111111111")
    labs.register_developer(OTHER_ORCID, "Builder", "0x2222222222222222222222222222222222222222")

    bounty = labs.create_bounty(ORCID, "Implement CodeCommitRegistry", "Ship Solidity event registry", 25_000_000, 4_102_444_800)
    assert bounty.status == BountyStatus.OPEN

    labs.assign_bounty(bounty.bounty_id, OTHER_ORCID)
    labs.submit_solution(bounty.bounty_id, OTHER_ORCID, {"CodeCommitRegistry.sol": "contract CodeCommitRegistry {}"})
    paid = labs.approve_bounty(bounty.bounty_id, ORCID)

    assert paid.status == BountyStatus.PAID
    assert len(paid.x402_receipt) == 64
    assert paid.reward_usdc == 25_000_000
    assert bounty.hashtree_anchor is not None
    assert bounty.hashtree_anchor.base_url == "https://hashtree.cc"


def test_hashtree_anchor_client_is_deterministic_for_same_payload():
    client = HashtreeAnchorClient()
    payload = {"commit_hash": "abc123", "ipfs_cid": "bafyarkhe342abc"}

    a = client.anchor("code_commit", "abc123", payload)
    b = client.anchor("code_commit", "abc123", payload)

    assert a == b
    assert a.share_url == f"https://hashtree.cc/#{a.canonical_seal}"


def test_public_repository_index_finds_submitted_clone():
    index = PublicRepositoryIndex()
    reference = """
contract Treasury {
    mapping(address => uint256) public credit;
    function withdraw(address account) external {
        require(credit[account] > 0, "none");
        credit[account] = 0;
    }
}
"""
    submission = reference.replace("Treasury", "Vault").replace("credit", "balance")

    reference_id = index.add_reference("github", "https://github.com/example/repo", "Treasury.sol", reference)
    matches = index.compare_submission(submission)

    assert matches[0]["reference_id"] == reference_id
    assert matches[0]["source"] == "github"
    assert matches[0]["attribution_required"] is True


def test_solidity_contracts_contain_required_substrate_342_controls():
    root = Path(__file__).resolve().parents[1]
    code_commit = (root / "contracts/orkut_2/CodeCommitRegistry.sol").read_text(encoding="utf-8")
    code_commit_hashtree = (root / "contracts/orkut_2/CodeCommitRegistryHashtree.sol").read_text(encoding="utf-8")
    hashtree_verifier = (root / "contracts/orkut_2/HashtreeVerifier.sol").read_text(encoding="utf-8")
    bounty = (root / "contracts/orkut_2/BountyRegistry.sol").read_text(encoding="utf-8")
    facilitator = (root / "contracts/orkut_2/BountyPaymentFacilitator.sol").read_text(encoding="utf-8")

    assert "contract CodeCommitRegistry" in code_commit
    assert "event CodeCommitted" in code_commit
    assert "mapping(uint256 => uint256) public commitNonces" in code_commit
    assert "committedSeals" in code_commit
    assert "ownerOf(authorTokenId) == msg.sender" in code_commit
    assert "contract CodeCommitRegistryHashtree" in code_commit_hashtree
    assert "CodeCommittedHashtree" in code_commit_hashtree
    assert "verifyFileInCommit" in code_commit_hashtree
    assert "library HashtreeVerifier" in hashtree_verifier
    assert "verifyProof" in hashtree_verifier

    assert "contract BountyRegistry" in bounty
    assert "enum BountyStatus" in bounty
    assert "event X402Receipt" in bounty
    assert "PHI_FEE_PPM" in bounty
    assert "function approveBounty" in bounty
    assert "approveBountyWithPayment" in bounty

    assert "contract BountyPaymentFacilitator" in facilitator
    assert "consumedAuthorizations" in facilitator
    assert "tx.origin" not in facilitator
    assert "transferFrom(sponsor, assignee, amountUsdc)" in facilitator


def test_subgraph_frontend_and_audit_artifacts_exist():
    root = Path(__file__).resolve().parents[1]
    subgraph = (root / "subgraphs/substrate_342/subgraph.yaml").read_text(encoding="utf-8")
    schema = (root / "subgraphs/substrate_342/schema.graphql").read_text(encoding="utf-8")
    mapping = (root / "subgraphs/substrate_342/src/mapping.ts").read_text(encoding="utf-8")
    frontend = (root / "projects/orkut-labs-dev-mvp/index.html").read_text(encoding="utf-8")
    runbook = (root / "deploy/substrate_342_testnet_runbook.md").read_text(encoding="utf-8")
    audit = (root / "security/substrate_342_bounty_audit_checklist.md").read_text(encoding="utf-8")

    assert "CodeCommitted" in subgraph
    assert "X402Receipt" in subgraph
    assert "type CodeCommit" in schema
    assert "type CommitFile" in schema
    assert "type PlagiarismCheck" in schema
    assert "type Bounty" in schema
    assert "handleCodeCommitted" in mapping
    assert "CodeCommitRegistryHashtree" in subgraph
    assert "https://hashtree.cc/#" in frontend
    assert "Hashtree" in runbook
    assert "tx.origin" in audit


def test_unregistered_developer_cannot_create_repository():
    labs = OrkutLabsDev()
    with pytest.raises(KeyError):
        labs.create_repository(ORCID, "missing")
