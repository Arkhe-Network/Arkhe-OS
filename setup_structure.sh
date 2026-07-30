#!/bin/bash
mkdir -p safe-core/.github/workflows
mkdir -p safe-core/ADR
mkdir -p safe-core/docs/architecture
mkdir -p safe-core/docs/api/grpc
mkdir -p safe-core/docs/api/rest
mkdir -p safe-core/docs/operations
mkdir -p safe-core/crates/safe-core-crypto/src/verify
mkdir -p safe-core/crates/safe-core-crypto/tests
mkdir -p safe-core/crates/safe-core-crypto/benches
mkdir -p safe-core/crates/safe-core-did/src/verify
mkdir -p safe-core/crates/safe-core-did/tests
mkdir -p safe-core/crates/safe-core-memory/src/verify
mkdir -p safe-core/crates/safe-core-memory/tests
mkdir -p safe-core/crates/safe-core-policy/src/verify
mkdir -p safe-core/crates/safe-core-policy/tests
mkdir -p safe-core/crates/safe-core-sandbox/src/verify
mkdir -p safe-core/crates/safe-core-sandbox/tests
mkdir -p safe-core/crates/safe-core-consensus/src/verify
mkdir -p safe-core/crates/safe-core-consensus/tests
mkdir -p safe-core/crates/safe-core-interface/src/verify
mkdir -p safe-core/crates/safe-core-interface/tests
mkdir -p safe-core/crates/safe-core-mcp/src
mkdir -p safe-core/crates/safe-core-mcp/tests
mkdir -p safe-core/crates/safe-core-a2a/src
mkdir -p safe-core/crates/safe-core-a2a/tests
mkdir -p safe-core/proto/safe_core/v1
mkdir -p safe-core/proto/google
mkdir -p safe-core/tests/e2e
mkdir -p safe-core/tests/integration
mkdir -p safe-core/tests/fixtures/test_keys
mkdir -p safe-core/tests/fixtures/test_configs
mkdir -p safe-core/tools
mkdir -p safe-core/scripts/ci
mkdir -p safe-core/scripts/local-dev
mkdir -p safe-core/.vscode

# Touch all files
touch safe-core/README.md \
safe-core/LICENSE \
safe-core/SECURITY.md \
safe-core/CONTRIBUTING.md \
safe-core/GOVERNANCE.md \
safe-core/CODE_OF_CONDUCT.md \
safe-core/.github/CODEOWNERS \
safe-core/.github/PULL_REQUEST_TEMPLATE.md \
safe-core/.github/workflows/ci.yml \
safe-core/.github/workflows/verify-kani.yml \
safe-core/.github/workflows/verify-prusti.yml \
safe-core/.github/workflows/security-audit.yml \
safe-core/.github/workflows/release.yml \
safe-core/.github/dependabot.yml \
safe-core/ADR/0001-cargo-workspace.md \
safe-core/ADR/0002-threshold-ml-dsa.md \
safe-core/ADR/0003-cp-wbft-research-stub.md \
safe-core/ADR/0004-kani-prusti-ci.md \
safe-core/ADR/0005-no-bazel-phase1.md \
safe-core/ADR/0006-camel-pattern.md \
safe-core/docs/architecture/overview.md \
safe-core/docs/architecture/layers.md \
safe-core/docs/architecture/invariants.md \
safe-core/docs/architecture/threat-model.md \
safe-core/docs/architecture/dependency-graph.md \
safe-core/docs/api/grpc/index.md \
safe-core/docs/api/rest/openapi.yaml \
safe-core/docs/operations/deployment.md \
safe-core/docs/operations/monitoring.md \
safe-core/docs/operations/disaster-recovery.md \
safe-core/docs/developer-guide.md \
safe-core/proto/BUILD.bazel \
safe-core/proto/safe_core/v1/identity.proto \
safe-core/proto/safe_core/v1/policy.proto \
safe-core/proto/safe_core/v1/consensus.proto \
safe-core/proto/safe_core/v1/audit.proto \
safe-core/proto/safe_core/BUILD.bazel \
safe-core/tests/e2e/test_identity_flow.rs \
safe-core/tests/e2e/test_policy_flow.rs \
safe-core/tests/e2e/test_sandbox_flow.rs \
safe-core/tests/e2e/test_consensus_flow.rs \
safe-core/tests/e2e/test_full_auth_flow.rs \
safe-core/tests/integration/test_mcp_adapter.rs \
safe-core/tests/integration/test_a2a_adapter.rs \
safe-core/tests/fixtures/test_keys/ml_dsa_key.pem \
safe-core/tests/fixtures/test_keys/threshold_shares.json \
safe-core/tests/fixtures/test_configs/policy.yaml \
safe-core/tests/fixtures/test_configs/sandbox_config.yaml \
safe-core/tools/setup.sh \
safe-core/tools/verify-all.sh \
safe-core/tools/benchmark.sh \
safe-core/tools/generate-docs.sh \
safe-core/tools/update-dependencies.sh \
safe-core/tools/release.sh \
safe-core/scripts/ci/install-kani.sh \
safe-core/scripts/ci/install-prusti.sh \
safe-core/scripts/local-dev/run-local.sh \
safe-core/scripts/local-dev/clean.sh \
safe-core/.vscode/extensions.json \
safe-core/.vscode/settings.json \
safe-core/.vscode/launch.json

# Crates files
touch safe-core/crates/safe-core-crypto/Cargo.toml \
safe-core/crates/safe-core-crypto/VERIFY.md \
safe-core/crates/safe-core-crypto/README.md \
safe-core/crates/safe-core-crypto/src/lib.rs \
safe-core/crates/safe-core-crypto/src/hash.rs \
safe-core/crates/safe-core-crypto/src/kem.rs \
safe-core/crates/safe-core-crypto/src/signature.rs \
safe-core/crates/safe-core-crypto/src/threshold.rs \
safe-core/crates/safe-core-crypto/src/mtls.rs \
safe-core/crates/safe-core-crypto/src/verify/mod.rs \
safe-core/crates/safe-core-crypto/src/verify/kani.rs \
safe-core/crates/safe-core-crypto/src/verify/prusti.rs \
safe-core/crates/safe-core-crypto/src/error.rs \
safe-core/crates/safe-core-crypto/tests/integration_tests.rs \
safe-core/crates/safe-core-crypto/tests/threshold_tests.rs \
safe-core/crates/safe-core-crypto/benches/sign_verify.rs

touch safe-core/crates/safe-core-did/Cargo.toml \
safe-core/crates/safe-core-did/VERIFY.md \
safe-core/crates/safe-core-did/README.md \
safe-core/crates/safe-core-did/src/lib.rs \
safe-core/crates/safe-core-did/src/did.rs \
safe-core/crates/safe-core-did/src/document.rs \
safe-core/crates/safe-core-did/src/verify/mod.rs \
safe-core/crates/safe-core-did/src/verify/kani.rs \
safe-core/crates/safe-core-did/src/verify/prusti.rs \
safe-core/crates/safe-core-did/src/error.rs \
safe-core/crates/safe-core-did/tests/integration_tests.rs \
safe-core/crates/safe-core-did/tests/did_roundtrip.rs

touch safe-core/crates/safe-core-memory/Cargo.toml \
safe-core/crates/safe-core-memory/VERIFY.md \
safe-core/crates/safe-core-memory/README.md \
safe-core/crates/safe-core-memory/src/lib.rs \
safe-core/crates/safe-core-memory/src/working.rs \
safe-core/crates/safe-core-memory/src/episodic.rs \
safe-core/crates/safe-core-memory/src/semantic.rs \
safe-core/crates/safe-core-memory/src/procedural.rs \
safe-core/crates/safe-core-memory/src/dp_accountant.rs \
safe-core/crates/safe-core-memory/src/poisoning.rs \
safe-core/crates/safe-core-memory/src/verify/mod.rs \
safe-core/crates/safe-core-memory/src/verify/kani.rs \
safe-core/crates/safe-core-memory/src/verify/prusti.rs \
safe-core/crates/safe-core-memory/src/error.rs \
safe-core/crates/safe-core-memory/tests/memory_tests.rs \
safe-core/crates/safe-core-memory/tests/dp_tests.rs \
safe-core/crates/safe-core-memory/tests/poisoning_tests.rs

touch safe-core/crates/safe-core-policy/Cargo.toml \
safe-core/crates/safe-core-policy/VERIFY.md \
safe-core/crates/safe-core-policy/README.md \
safe-core/crates/safe-core-policy/src/lib.rs \
safe-core/crates/safe-core-policy/src/capability.rs \
safe-core/crates/safe-core-policy/src/rate_limiter.rs \
safe-core/crates/safe-core-policy/src/schema_validator.rs \
safe-core/crates/safe-core-policy/src/kill_switch.rs \
safe-core/crates/safe-core-policy/src/verify/mod.rs \
safe-core/crates/safe-core-policy/src/verify/kani.rs \
safe-core/crates/safe-core-policy/src/verify/prusti.rs \
safe-core/crates/safe-core-policy/src/error.rs \
safe-core/crates/safe-core-policy/tests/capability_tests.rs \
safe-core/crates/safe-core-policy/tests/schema_tests.rs \
safe-core/crates/safe-core-policy/tests/rate_limit_tests.rs

touch safe-core/crates/safe-core-sandbox/Cargo.toml \
safe-core/crates/safe-core-sandbox/VERIFY.md \
safe-core/crates/safe-core-sandbox/README.md \
safe-core/crates/safe-core-sandbox/src/lib.rs \
safe-core/crates/safe-core-sandbox/src/microvm.rs \
safe-core/crates/safe-core-sandbox/src/gvisor.rs \
safe-core/crates/safe-core-sandbox/src/wasmtime.rs \
safe-core/crates/safe-core-sandbox/src/camel.rs \
safe-core/crates/safe-core-sandbox/src/network.rs \
safe-core/crates/safe-core-sandbox/src/verify/mod.rs \
safe-core/crates/safe-core-sandbox/src/verify/kani.rs \
safe-core/crates/safe-core-sandbox/src/error.rs \
safe-core/crates/safe-core-sandbox/tests/microvm_tests.rs \
safe-core/crates/safe-core-sandbox/tests/camel_tests.rs \
safe-core/crates/safe-core-sandbox/tests/egress_tests.rs

touch safe-core/crates/safe-core-consensus/Cargo.toml \
safe-core/crates/safe-core-consensus/VERIFY.md \
safe-core/crates/safe-core-consensus/README.md \
safe-core/crates/safe-core-consensus/src/lib.rs \
safe-core/crates/safe-core-consensus/src/cp_wbft.rs \
safe-core/crates/safe-core-consensus/src/sac.rs \
safe-core/crates/safe-core-consensus/src/graph.rs \
safe-core/crates/safe-core-consensus/src/mock.rs \
safe-core/crates/safe-core-consensus/src/verify/mod.rs \
safe-core/crates/safe-core-consensus/src/verify/kani.rs \
safe-core/crates/safe-core-consensus/src/error.rs \
safe-core/crates/safe-core-consensus/tests/mock_consensus_tests.rs \
safe-core/crates/safe-core-consensus/tests/graph_tests.rs

touch safe-core/crates/safe-core-interface/Cargo.toml \
safe-core/crates/safe-core-interface/VERIFY.md \
safe-core/crates/safe-core-interface/README.md \
safe-core/crates/safe-core-interface/src/lib.rs \
safe-core/crates/safe-core-interface/src/approval.rs \
safe-core/crates/safe-core-interface/src/audit.rs \
safe-core/crates/safe-core-interface/src/notification.rs \
safe-core/crates/safe-core-interface/src/verify/mod.rs \
safe-core/crates/safe-core-interface/src/verify/kani.rs \
safe-core/crates/safe-core-interface/src/verify/prusti.rs \
safe-core/crates/safe-core-interface/src/error.rs \
safe-core/crates/safe-core-interface/tests/approval_tests.rs \
safe-core/crates/safe-core-interface/tests/audit_tests.rs

touch safe-core/crates/safe-core-mcp/Cargo.toml \
safe-core/crates/safe-core-mcp/README.md \
safe-core/crates/safe-core-mcp/src/lib.rs \
safe-core/crates/safe-core-mcp/src/server.rs \
safe-core/crates/safe-core-mcp/src/client.rs \
safe-core/crates/safe-core-mcp/src/types.rs \
safe-core/crates/safe-core-mcp/src/error.rs \
safe-core/crates/safe-core-mcp/tests/integration_tests.rs

touch safe-core/crates/safe-core-a2a/Cargo.toml \
safe-core/crates/safe-core-a2a/README.md \
safe-core/crates/safe-core-a2a/src/lib.rs \
safe-core/crates/safe-core-a2a/src/agent_card.rs \
safe-core/crates/safe-core-a2a/src/task.rs \
safe-core/crates/safe-core-a2a/src/types.rs \
safe-core/crates/safe-core-a2a/src/error.rs \
safe-core/crates/safe-core-a2a/tests/integration_tests.rs
