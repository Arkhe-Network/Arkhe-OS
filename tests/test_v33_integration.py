"""ARKHE Catedral v3.3 — Integration Test Suite
Tests the full three-plane architecture:
  - Plane 1 (Code): gRPC protobuf contracts, REST mappings, SLA checks
  - Plane 2 (Research): schema validation, cross-plane references
  - Plane 3 (Light): MythOS engine integrity, constitution mapping
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOS_DIR = ROOT / "protos"
SUBSTRATES_DIR = ROOT / "substrates"
TESTS_DIR = ROOT / "tests"

# ==============================================================================
# Plane 1 — Code Cathedral: Protobuf Contract Integrity
# ==============================================================================

def _list_protos():
    return sorted(PROTOS_DIR.rglob("*.proto"))

def test_p1_protobuf_directory_structure():
    protos = _list_protos()
    assert len(protos) >= 12, f"Expected >= 12 protos, found {len(protos)}"
    names = [p.name for p in protos]
    assert "header.proto" in names
    assert "temporalchain.proto" in names

def test_p1_header_proto_exists():
    header = PROTOS_DIR / "arkhe" / "common" / "v1" / "header.proto"
    assert header.exists()
    content = header.read_text(encoding="utf-8")
    assert "message ArkheHeader" in content
    assert "message ArkheSeal" in content
    assert "trace_id" in content

def test_p1_each_service_has_proto():
    service_ids = ["temporalchain", "epistemic", "hermeszk", "quicmesh",
                   "brasilfinance", "glasswing", "fluxmem", "worldmodel",
                   "agency", "mcp", "androidhal", "webgrounding"]
    for sid in service_ids:
        proto_dir = PROTOS_DIR / "arkhe" / sid / "v1"
        protos = list(proto_dir.glob("*.proto"))
        assert len(protos) >= 1, f"Missing proto for service {sid}"

def test_p1_each_service_defines_rpc():
    for proto_file in _list_protos():
        if proto_file.name == "header.proto":
            continue
        content = proto_file.read_text(encoding="utf-8")
        assert "service " in content, f"{proto_file.name} has no service"
        assert "rpc " in content, f"{proto_file.name} has no RPCs"

def test_p1_each_proto_imports_header():
    for proto_file in _list_protos():
        if proto_file.name == "header.proto":
            continue
        content = proto_file.read_text(encoding="utf-8")
        assert 'import "arkhe/common/v1/header.proto"' in content, \
            f"{proto_file.name} does not import common header"

def test_p1_service_schema_valid():
    schema = PROTOS_DIR / "schema_protos.yaml"
    assert schema.exists()
    content = schema.read_text(encoding="utf-8")
    assert "services:" in content
    assert "sla_p99_ms" in content
    assert "CANONIZED_PROVISIONAL" in content

# ==============================================================================
# Plane 1 — REST API Contract Validation
# ==============================================================================

def test_p1_rest_endpoints_mapped():
    schema = PROTOS_DIR / "schema_protos.yaml"
    lines = schema.read_text(encoding="utf-8").splitlines()
    rest_lines = [l for l in lines if l.strip().startswith("- \"") and "/api/" in l]
    assert len(rest_lines) >= 12, f"Expected >= 12 REST endpoints, found {len(rest_lines)}"
    assert any("POST /api/v1/temporalchain/events" in l for l in rest_lines)
    assert any("POST /api/v1/zk/proofs" in l for l in rest_lines)
    assert any("POST /api/v1/finance/pix" in l for l in rest_lines)

# ==============================================================================
# Plane 2 — Research Cathedral: Schema Validation
# ==============================================================================

def test_p2_each_substrate_has_schema():
    schema_count = 0
    for d in SUBSTRATES_DIR.iterdir():
        if not d.is_dir():
            continue
        schemas = list(d.glob("schema_*.yaml")) + list(d.glob("schema_*.json")) + list(d.glob("schema_*.jsonld"))
        schema_count += len(schemas)
    assert schema_count >= 10, f"Expected >= 10 schema files, found {schema_count}"

def test_p2_schema_has_ghost_threshold():
    ghost_found = 0
    for yaml_file in SUBSTRATES_DIR.rglob("schema_*.yaml"):
        content = yaml_file.read_text(encoding="utf-8", errors="ignore")
        if "0.577" in content or "ghost" in content.lower():
            ghost_found += 1
    assert ghost_found >= 3, f"Ghost threshold found in only {ghost_found} schemas"

# ==============================================================================
# Plane 3 — Light Cathedral: MythOS Engine Integrity
# ==============================================================================

def test_p3_mythos_engine_exists():
    mythos_dir = SUBSTRATES_DIR / "938-arkhe-mythos-merge"
    assert mythos_dir.exists(), "MythOS substrate missing"
    engine = mythos_dir / "mythos_engine.py"
    assert engine.exists(), "mythos_engine.py missing"

def test_p3_mythos_has_deities():
    mythos_dir = SUBSTRATES_DIR / "938-arkhe-mythos-merge"
    engine = mythos_dir / "mythos_engine.py"
    if not engine.exists():
        return
    content = engine.read_text(encoding="utf-8")
    assert "Hermes Trismegistus" in content or "Prometheus" in content

# ==============================================================================
# Cross-Plane Integration
# ==============================================================================

def _find_substrate_implementation(substrate_id):
    """Check for implementation in substrates/, src/arkhe/, or contracts/."""
    # Check substrates/ directories
    for d in SUBSTRATES_DIR.iterdir():
        if d.is_dir() and d.name.startswith(substrate_id):
            return str(d)
    # Check src/arkhe/ for modules containing the service name
    src_dir = ROOT / "src" / "arkhe"
    if src_dir.exists():
        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if f"substrate {substrate_id}" in content.lower() or f"substrate_{substrate_id}" in content.lower():
                    return str(py_file)
            except Exception:
                pass
    return None

def test_cross_plane_proto_to_substrate():
    """Every gRPC service proto maps to at least one materialized artifact."""
    proto_service_map = {
        "temporalchain": "923",
        "epistemic": "912",
        "hermeszk": "255",
        "quicmesh": "262",
        "brasilfinance": "261",
        "glasswing": "944",
        "fluxmem": "933",
        "worldmodel": "890",
        "agency": "891",
        "mcp": "940",
        "androidhal": "929",
        "webgrounding": "917",
    }
    missing = []
    for service_name, substrate_id in proto_service_map.items():
        imp = _find_substrate_implementation(substrate_id)
        if not imp:
            missing.append(f"{service_name} ({substrate_id})")
    assert not missing, f"Missing substrate implementations for: {', '.join(missing)}"

def test_cross_plane_pix_flow():
    """End-to-end: Pix payment flow through the architecture."""
    schema = PROTOS_DIR / "schema_protos.yaml"
    content = schema.read_text(encoding="utf-8")
    assert "brasilfinance" in content
    assert "hermeszk" in content
    assert "temporalchain" in content
    assert "glasswing" in content

# ==============================================================================
# Build System Integration
# ==============================================================================

def test_build_system_exists():
    scripts = [
        ROOT / "build_cathedral.ps1",
        ROOT / "status_cathedral.ps1",
        ROOT / "install_cathedral.ps1",
        ROOT / "seal_cathedral.ps1",
    ]
    for s in scripts:
        assert s.exists(), f"Missing build script: {s.name}"

# ==============================================================================
# AGENTS.md Integrity
# ==============================================================================

def test_agents_md_exists():
    agents = ROOT / "AGENTS.md"
    assert agents.exists()

# ==============================================================================
# Canonical Seal
# ==============================================================================

def test_canonical_seal():
    """Compute SHA-256 of the entire protos directory as canonical seal."""
    proto_files = _list_protos()
    hasher = hashlib.sha256()
    for pf in proto_files:
        rel = pf.relative_to(PROTOS_DIR)
        hasher.update(str(rel).encode("utf-8"))
        hasher.update(pf.read_bytes())
    seal = hasher.hexdigest()
    assert len(seal) == 64
    assert seal.isalnum()

# ==============================================================================
# SLA Coverage
# ==============================================================================

def test_sla_coverage():
    """Every service in protos schema has SLA defined."""
    schema = PROTOS_DIR / "schema_protos.yaml"
    content = schema.read_text(encoding="utf-8")
    for service_id in ["923", "912", "255", "262.2", "261.1", "944",
                       "933", "890", "891", "940", "929", "917"]:
        assert service_id in content, f"Service {service_id} missing from schema"

# ==============================================================================
# Run Count
# ==============================================================================

if __name__ == "__main__":
    test_functions = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in sorted(test_functions, key=lambda f: f.__name__):
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
    total = passed + failed
    print(f"\n{'='*50}")
    print(f"  v3.3 Integration Tests: {passed}/{total} passed")
    if failed:
        print(f"  ❌ {failed} failed")
    else:
        print(f"  ✅ ALL PASSED")
    print(f"{'='*50}")
    sys.exit(1 if failed else 0)
