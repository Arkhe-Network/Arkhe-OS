import json
import pytest
import sys
import os

# Adiciona o diretório raiz ao path se necessário
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cathedral_mcp import (
    AntigravityCathedralConfig,
    CathedralToolsForAntigravity,
    CathedralPolicies,
    CathedralTriggers,
    AntigravityMCPCathedralServer,
    CathedralMultimodalAssets,
    AntigravityCathedralIntegration,
    PHI,
    LAMBDA_THESIS,
    ETA_PLASTICITY
)

def test_constants():
    assert PHI > 1.6
    assert LAMBDA_THESIS == 0.5334
    assert ETA_PLASTICITY == 0.5334

def test_config():
    config = AntigravityCathedralConfig(gemini_api_key="test_key")
    assert config.gemini_api_key == "test_key"
    assert config.enable_mcp is True
    assert len(config.cathedral_substrates) > 0

def test_tools():
    tools = CathedralToolsForAntigravity()
    
    # test theosis_probe
    probe_res = json.loads(tools.theosis_probe("Hello world test"))
    assert "theosis" in probe_res
    
    # test substrate_query
    sub_res = json.loads(tools.substrate_query("1077"))
    assert sub_res["substrate_id"] == "1077"
    assert sub_res["name"] == "GOOSE-CATHEDRAL-BRIDGE"
    
    # test substrate_query for non-numeric/sub-properties
    sub_res_non_num = json.loads(tools.substrate_query("989.y.6.1"))
    assert sub_res_non_num["status"] == "CANONIZED_PROVISIONAL"
    
    # test axiarchia_gate
    gate_res = json.loads(tools.axiarchia_gate("Process control design"))
    assert "compliance" in gate_res
    
    # test hamiltonian_implosion
    impl_res = json.loads(tools.hamiltonian_implosion(3))
    assert impl_res["reverse_time_steps"] == 3
    
    # test dkes_gram_compute
    dkes_res = json.loads(tools.dkes_gram_compute([1.0, 2.0], T=2, K=2))
    assert dkes_res["T"] == 2
    
    # test bio_digital_oracle
    bio_res = json.loads(tools.bio_digital_oracle("0xabc"))
    assert bio_res["verified"] is True
    
    # test rbb_bridge_query
    rbb_res = json.loads(tools.rbb_bridge_query("merkle_anchor"))
    assert rbb_res["query_type"] == "merkle_anchor"
    
    # test kleros_dispute
    kleros_res = json.loads(tools.kleros_dispute("submit"))
    assert kleros_res["action"] == "submit"
    
    # test constitution_ai_audit
    audit_res = json.loads(tools.constitution_ai_audit("Audit text"))
    assert "mean_score" in audit_res
    
    # test os_wide_scan
    scan_res = json.loads(tools.os_wide_scan("process"))
    assert scan_res["subsystem"] == "process"
    
    # test proof_refactor
    ref_res = json.loads(tools.proof_refactor("def test:\n  pass"))
    assert ref_res["status"] == "REFACTORED"
    
    # test plastic_memory_read
    mem_res = json.loads(tools.plastic_memory_read("ETHICS", "CONSCIOUSNESS"))
    assert mem_res["domain_a"] == "ETHICS"
    
    # test cathedral_seal
    seal_val = tools.cathedral_seal()
    assert seal_val.startswith("CATHEDRAL-SEAL-v5.0-")

def test_policies():
    policies = CathedralPolicies.get_policies(strict=True)
    assert len(policies) > 0
    types = {p["type"] for p in policies}
    assert "deny" in types
    assert "allow" in types
    assert "ask_user" in types
    assert "enforce" in types

def test_triggers():
    triggers = CathedralTriggers.get_triggers()
    assert len(triggers) == 3
    assert triggers[0][0] == 60
    assert triggers[0][1].__name__ == "check_theosis"

class MockCtx:
    def __init__(self):
        self.messages = []
    def send(self, msg):
        self.messages.append(msg)

def test_trigger_callbacks():
    ctx = MockCtx()
    CathedralTriggers.check_theosis(ctx)
    CathedralTriggers.audit_substrates(ctx)
    CathedralTriggers.generate_seal(ctx)
    assert len(ctx.messages) == 3

def test_mcp_server():
    server = AntigravityMCPCathedralServer()
    
    # test initialize
    init_res = server.handle_request({"method": "initialize", "id": 1})
    assert init_res["protocolVersion"] == "2024-11-05"
    assert init_res["seal"] == server.seal
    
    # test tools/list
    list_res = server.handle_request({"method": "tools/list", "id": 2})
    assert len(list_res["tools"]) > 0
    
    # test tools/call
    call_res = server.handle_request({
        "method": "tools/call",
        "params": {"name": "theosis_probe", "arguments": {"input": "test text"}},
        "id": 3
    })
    content = json.loads(call_res["content"][0]["text"])
    assert "theosis" in content

def test_multimodal_assets():
    assets = CathedralMultimodalAssets()
    img = assets.get_seal_image()
    assert img["type"] == "Image"
    
    doc = assets.get_substrate_document("1042")
    assert doc["type"] == "Document"
    assert "RBB-CATHEDRAL-BRIDGE" in doc["data"]

def test_integration():
    integration = AntigravityCathedralIntegration()
    config = integration.get_config()
    assert len(config["tools"]) == 13
    assert len(config["policies"]) > 0
    assert len(config["triggers"]) == 3
    
    prompt = integration.get_multimodal_prompt("Audit this", "1046.7")
    assert len(prompt) == 3
    assert prompt[0] == "Audit this"
    assert prompt[1]["type"] == "Image"
    assert prompt[2]["type"] == "Document"
