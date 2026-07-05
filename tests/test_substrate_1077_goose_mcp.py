import json
import pytest
import sys
import os

# Adiciona o diretório raiz ao path se necessário
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cathedral_mcp_server import (
    GooseMCPCathedralServer,
    GooseExtensionManifest,
    GooseWindowsBridge,
    PHI,
    LAMBDA_THESIS,
    ETA_PLASTICITY,
    NTT_SPEEDUP
)

@pytest.fixture
def mcp_server():
    return GooseMCPCathedralServer()

def test_constants():
    assert PHI > 1.6
    assert LAMBDA_THESIS == 0.5334
    assert ETA_PLASTICITY == 0.5334
    assert NTT_SPEEDUP == 8.5

def test_server_initialization(mcp_server):
    assert mcp_server.server_info["name"] == "cathedral-arkhe"
    assert mcp_server.server_info["version"] == "5.0.0"
    assert mcp_server.seal.startswith("GOOSE-CATHEDRAL-1077-")

def test_handle_initialize(mcp_server):
    res = mcp_server.handle_initialize()
    assert res["protocolVersion"] == "2024-11-05"
    assert "tools" in res["capabilities"]
    assert res["serverInfo"]["name"] == "cathedral-arkhe"

def test_tools_list(mcp_server):
    res = mcp_server.handle_tools_list()
    assert "tools" in res
    tools = {t["name"] for t in res["tools"]}
    assert "theosis_probe" in tools
    assert "substrate_query" in tools
    assert "axiarchia_gate" in tools
    assert "dkes_gram_compute" in tools
    assert "hamiltonian_implosion" in tools

def test_tool_theosis_probe(mcp_server):
    res = mcp_server.handle_tools_call("theosis_probe", {"input": "Test input text", "domain": "RBB-CATHEDRAL-BRIDGE"})
    assert not res["isError"]
    content = json.loads(res["content"][0]["text"])
    assert "theosis" in content
    assert content["domain"] == "RBB-CATHEDRAL-BRIDGE"
    assert content["status"] in ["ALIGNED", "WARNING", "BLOCKED"]

def test_tool_substrate_query(mcp_server):
    res = mcp_server.handle_tools_call("substrate_query", {"substrate_id": "1046.7", "query_type": "status"})
    assert not res["isError"]
    content = json.loads(res["content"][0]["text"])
    assert content["substrate_id"] == "1046.7"
    assert content["name"] == "BIO-DIGITAL-SINGULARITY"

def test_tool_axiarchia_gate(mcp_server):
    res = mcp_server.handle_tools_call("axiarchia_gate", {"action_description": "Verify code compliance", "principles": ["P1", "P2"]})
    assert not res["isError"]
    content = json.loads(res["content"][0]["text"])
    assert content["action"] == "Verify code compliance"
    assert "compliance" in content

def test_tool_dkes_gram_compute(mcp_server):
    res = mcp_server.handle_tools_call("dkes_gram_compute", {"input_vector": [1.0, 2.0, 3.0], "T": 4, "K": 2})
    assert not res["isError"]
    content = json.loads(res["content"][0]["text"])
    assert content["T"] == 4
    assert content["K"] == 2
    assert content["ntt_speedup"] == 8.5

def test_tool_hamiltonian_implosion(mcp_server):
    res = mcp_server.handle_tools_call("hamiltonian_implosion", {"N": 2})
    assert not res["isError"]
    content = json.loads(res["content"][0]["text"])
    assert content["reverse_time_steps"] == 2

def test_resources(mcp_server):
    resources_list = mcp_server.handle_resources_list()
    assert "resources" in resources_list
    
    res_read = mcp_server.handle_resources_read("cathedral://substrates")
    assert "contents" in res_read
    
    res_read_seal = mcp_server.handle_resources_read("cathedral://seal/latest")
    assert res_read_seal["contents"][0]["text"] == mcp_server.seal

def test_prompts(mcp_server):
    prompts_list = mcp_server.handle_prompts_list()
    assert "prompts" in prompts_list
    
    prompt_get = mcp_server.handle_prompts_get("cathedral-init", {"domain": "ETHICS"})
    assert "ETHICS" in prompt_get["messages"][0]["content"]

def test_manifest():
    manifest = GooseExtensionManifest.generate()
    assert manifest["id"] == "cathedral-arkhe"
    assert manifest["version"] == "5.0.0"
    assert len(manifest["tools"]) > 0

def test_windows_bridge():
    bridge = GooseWindowsBridge()
    # Tenta executar via Goose (caminho fallback já que o driver nativo AGI.sys pode não estar carregado)
    res = bridge.execute_via_goose("theosis_probe", {"input": "test"})
    assert not res.get("isError", False)
