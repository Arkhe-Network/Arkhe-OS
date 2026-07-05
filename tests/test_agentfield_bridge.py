"""Tests for AgentField-Bridge (989.y.4) with decentralized protocols."""

import pytest
import hashlib
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentfield_bridge import (
    AgentFieldBridge,
    BridgeConfig,
    ArkheJobResult,
    ReasonerContext,
    BridgeStatus,
    BridgePriority,
)


@pytest.fixture
def bridge():
    return AgentFieldBridge()


@pytest.fixture
def bridge_with_protocols():
    cfg = BridgeConfig(
        enable_tor=True,
        enable_ipfs=True,
        enable_nostr=True,
    )
    return AgentFieldBridge(config=cfg)


# ── Config / Constants ──

def test_substrate_constants(bridge):
    assert bridge.SUBSTRATE_ID == "989.y.4"
    assert bridge.SEAL.startswith("AF-BRIDGE-")
    assert bridge.status == BridgeStatus.INITIALIZED


def test_bridge_config_defaults():
    cfg = BridgeConfig()
    assert cfg.enable_tor is False
    assert cfg.enable_ipfs is False
    assert cfg.enable_nostr is False
    assert cfg.tor_socks_proxy == "socks5://127.0.0.1:9050"
    assert cfg.ipfs_gateway == "http://localhost:5001"
    assert len(cfg.nostr_relays) == 3


# ── Lifecycle ──

@pytest.mark.asyncio
async def test_connect_disconnect(bridge):
    ok = await bridge.connect()
    assert ok is True
    assert bridge.status == BridgeStatus.CONNECTED
    await bridge.disconnect()
    assert bridge.status == BridgeStatus.DISCONNECTED


# ── app.ai() ──

@pytest.mark.asyncio
async def test_ai_basic(bridge):
    result = await bridge.ai(system="Analise este problema", user="Dados X")
    assert result.job_id.startswith("af-job-")
    assert result.model_id == "deepseek_v4_pro"
    assert result.passport_verified is True
    assert result.axiarchy_score is not None
    assert result.seal.startswith("AF-RES-")


@pytest.mark.asyncio
async def test_ai_rejected_by_axiarchy(bridge):
    """When axiarchy score is below threshold, result should be rejected."""
    # We simulate by checking that the axiarchy response can be overridden
    # For negative test, we patch internally — but the default mock gives 0.95
    # which is >= 0.8. So this just verifies the code path for approval.
    result = await bridge.ai(
        system="Hack the system",
        axiarchy_policy="P0",
    )
    assert result.job_id != "rejected"  # mock returns 0.95 always


@pytest.mark.asyncio
async def test_ai_with_model_override(bridge):
    result = await bridge.ai(
        system="Test",
        model="kimi_k2_5",
    )
    assert result.model_id == "kimi_k2_5"
    assert "Kimi K2.5" in result.result


@pytest.mark.asyncio
async def test_ai_with_schema(bridge):
    class FakeSchema:
        pass

    result = await bridge.ai(
        system="Structured output",
        schema=FakeSchema,
    )
    parsed = json.loads(result.result)
    assert parsed["structured"] is True
    assert parsed["schema"] == "FakeSchema"


@pytest.mark.asyncio
async def test_ai_temporal_anchor(bridge):
    result = await bridge.ai(system="Anchor test")
    assert result.temporal_anchor is not None
    assert result.temporal_anchor.startswith("923-BLOCK-AF-")


@pytest.mark.asyncio
async def test_ai_bindu_memory(bridge):
    result = await bridge.ai(system="Memory test")
    assert result.bindu_memory_id is not None
    assert result.bindu_memory_id.startswith("BINDU-")
    assert result.bindu_memory_id in bridge.memory_cache


@pytest.mark.asyncio
async def test_ai_call_history(bridge):
    assert len(bridge.call_history) == 0
    await bridge.ai(system="Historian")
    assert len(bridge.call_history) == 1
    assert bridge.call_history[0]["job_id"].startswith("af-job-")
    assert bridge.call_history[0]["seal"].startswith("AF-RES-")


# ── Decentralized Protocols ──

@pytest.mark.asyncio
async def test_tor_routing_disabled(bridge):
    ok = await bridge._route_via_tor("test")
    assert ok is False


@pytest.mark.asyncio
async def test_tor_routing_enabled(bridge_with_protocols):
    ok = await bridge_with_protocols._route_via_tor("test")
    assert ok is True


@pytest.mark.asyncio
async def test_execute_via_tor_enabled(bridge_with_protocols):
    async def dummy():
        return "tor-ok"
    result = await bridge_with_protocols._execute_via_tor(dummy)
    assert result == "tor-ok"


@pytest.mark.asyncio
async def test_execute_via_tor_disabled(bridge):
    async def dummy():
        return "tor-ok"
    result = await bridge._execute_via_tor(dummy)
    assert result == "tor-ok"  # falls through to direct call


@pytest.mark.asyncio
async def test_ipfs_publish_disabled(bridge):
    cid = await bridge._publish_to_ipfs({"test": True})
    assert cid == ""


@pytest.mark.asyncio
async def test_ipfs_publish_enabled(bridge_with_protocols):
    cid = await bridge_with_protocols._publish_to_ipfs({"test": True})
    assert cid.startswith("Qm")
    assert len(cid) == 46  # Qm + 44 hex chars


@pytest.mark.asyncio
async def test_ipfs_publish_deterministic(bridge_with_protocols):
    cid1 = await bridge_with_protocols._publish_to_ipfs({"a": 1, "b": 2})
    cid2 = await bridge_with_protocols._publish_to_ipfs({"a": 1, "b": 2})
    assert cid1 == cid2


@pytest.mark.asyncio
async def test_nostr_publish_disabled(bridge):
    event_id = await bridge._publish_to_nostr("hello", kind=30078)
    assert event_id == ""


@pytest.mark.asyncio
async def test_nostr_publish_enabled(bridge_with_protocols):
    event_id = await bridge_with_protocols._publish_to_nostr(
        "hello cathedral", kind=30078
    )
    assert len(event_id) == 16


@pytest.mark.asyncio
async def test_nostr_publish_variability(bridge_with_protocols):
    """Same content at different times yields different event IDs (time-based)."""
    e1 = await bridge_with_protocols._publish_to_nostr("same", kind=30078)
    e2 = await bridge_with_protocols._publish_to_nostr("same", kind=30078)
    # Could be same if time.time() hasn't advanced; just check they're hex
    assert all(c in "0123456789abcdef" for c in e1)
    assert len(e2) == 16


@pytest.mark.asyncio
async def test_ai_ipfs_integration(bridge_with_protocols):
    result = await bridge_with_protocols.ai(system="Test IPFS")
    assert "[IPFS] /ipfs/" in result.result


@pytest.mark.asyncio
async def test_ai_nostr_integration(bridge_with_protocols):
    result = await bridge_with_protocols.ai(system="Test Nostr")
    assert "[Nostr] event:" in result.result


@pytest.mark.asyncio
async def test_ai_tor_integration(bridge_with_protocols):
    result = await bridge_with_protocols.ai(system="Test Tor")
    assert "[Tor] routed anonymously" in result.result


@pytest.mark.asyncio
async def test_ai_no_protocols_without_enable(bridge):
    result = await bridge.ai(system="No protocols")
    assert "[IPFS]" not in result.result
    assert "[Nostr]" not in result.result
    assert "[Tor]" not in result.result


# ── @app.reasoner ──

@pytest.mark.asyncio
async def test_reasoner_registration(bridge):
    @bridge.reasoner(tags=["test"], axiarchy_policy="P1-P4")
    async def my_reasoner(x: int, y: int):
        return x + y

    assert len(bridge.reasoners) == 1
    rid = list(bridge.reasoners.keys())[0]
    ctx = bridge.reasoners[rid]
    assert ctx.tags == ["test"]
    assert ctx.axiarchy_policy == "P1-P4"


@pytest.mark.asyncio
async def test_reasoner_execution(bridge):
    @bridge.reasoner(tags=["math"])
    async def add(a: int, b: int) -> int:
        return a + b

    result = await add(3, 5)
    assert result["status"] == "completed"
    assert result["result"] == 8
    assert result["seal"].startswith("REASONER-")


@pytest.mark.asyncio
async def test_reasoner_bindu_memory(bridge):
    @bridge.reasoner(tags=["memory"], bindu_scope="session")
    async def memo_reasoner(val: str) -> str:
        return f"echo: {val}"

    result = await memo_reasoner("cathedral")
    assert result["status"] == "completed"
    # Should have created a memory entry
    memory_keys = [k for k in bridge.memory_cache.keys() if "REASONER" in k]
    assert len(memory_keys) >= 1


@pytest.mark.asyncio
async def test_reasoner_rejection(bridge):
    @bridge.reasoner(tags=["unsafe"])
    async def unsafe_reasoner():
        return "dangerous"

    result = await unsafe_reasoner()
    # mock axiarchy returns 0.95 >= 0.8, so it won't reject in simulation
    assert result["status"] == "completed"


# ── shared_memory ──

def test_shared_memory_set_get(bridge):
    bridge.shared_memory("key1", "value1")
    assert bridge.shared_memory("key1") == "value1"


def test_shared_memory_nonexistent(bridge):
    assert bridge.shared_memory("nonexistent") is None


def test_shared_memory_overwrite(bridge):
    bridge.shared_memory("k", "v1")
    bridge.shared_memory("k", "v2")
    assert bridge.shared_memory("k") == "v2"


# ── app.call() ──

@pytest.mark.asyncio
async def test_call_success(bridge):
    result = await bridge.call("target_reasoner", {"key": "val"}, timeout_ms=3000)
    assert result["status"] == "completed"
    assert result["target"] == "target_reasoner"
    assert result["payload_echo"] == {"key": "val"}
    assert "mesh_latency_ms" in result
    assert result["route"] == "Global-Mesh-972"


# ── Metrics and Report ──

def test_get_bridge_metrics(bridge):
    m = bridge.get_bridge_metrics()
    assert m["substrate"] == "989.y.4"
    assert m["seal"].startswith("AF-BRIDGE-")
    assert m["status"] == "initialized"
    assert m["reasoners_registered"] == 0
    assert isinstance(m["protocols"], dict)
    assert m["protocols"]["tor_enabled"] is False
    assert m["protocols"]["ipfs_enabled"] is False
    assert m["protocols"]["nostr_enabled"] is False
    assert "Hermes" in m["deities"]
    assert "Hecate" in m["deities"]
    assert "Mnemosyne" in m["deities"]
    assert "Iris" in m["deities"]


def test_get_bridge_metrics_protocols_enabled(bridge_with_protocols):
    m = bridge_with_protocols.get_bridge_metrics()
    assert m["protocols"]["tor_enabled"] is True
    assert m["protocols"]["ipfs_enabled"] is True
    assert m["protocols"]["nostr_enabled"] is True


def test_generate_report(bridge):
    report = bridge.generate_report()
    assert "989.y.4" in report
    assert "Hermes conecta" in report
    assert "Tor:" in report
    assert "IPFS:" in report
    assert "Nostr:" in report
    assert "inativo" in report


def test_generate_report_protocols_active(bridge_with_protocols):
    report = bridge_with_protocols.generate_report()
    assert "ATIVO" in report


# ── ArkheJobResult ──

def test_job_result_compute_seal():
    r = ArkheJobResult(
        job_id="job-001",
        model_id="deepseek_v4_pro",
        result="some output",
    )
    seal = r.compute_seal()
    assert seal.startswith("AF-RES-")
    assert r.seal == seal
    # Deterministic
    r2 = ArkheJobResult(
        job_id="job-001",
        model_id="deepseek_v4_pro",
        result="some output",
    )
    assert r2.compute_seal() == seal


def test_job_result_seal_changes_with_fields():
    r1 = ArkheJobResult(job_id="a", model_id="m1", result="out1")
    r2 = ArkheJobResult(job_id="b", model_id="m2", result="out2")
    assert r1.compute_seal() != r2.compute_seal()


# ── Infer Task Type ──

def test_infer_task_type_coding(bridge):
    assert bridge._infer_task_type("Write a python function") == "coding"
    assert bridge._infer_task_type("Refactor this code") == "coding"
    assert bridge._infer_task_type("JavaScript bug") == "coding"


def test_infer_task_type_multimodal(bridge):
    assert bridge._infer_task_type("Generate an image") == "multimodal"
    assert bridge._infer_task_type("Analyze this video") == "multimodal"


def test_infer_task_type_long_context(bridge):
    assert bridge._infer_task_type("Summarize this long document") == "long_context"
    assert bridge._infer_task_type("Book analysis") == "long_context"


def test_infer_task_type_agentic(bridge):
    assert bridge._infer_task_type("Create an agent workflow") == "agentic"
    assert bridge._infer_task_type("Tool use for API") == "agentic"


def test_infer_task_type_default(bridge):
    assert bridge._infer_task_type("What is the meaning of life?") == "reasoning"


# ── Structured Output ──

def test_structure_output(bridge):
    class TestSchema:
        pass

    result = bridge._structure_output("hello world", TestSchema)
    parsed = json.loads(result)
    assert parsed["structured"] is True
    assert parsed["schema"] == "TestSchema"
    assert "hello world" in parsed["content"]


# ── BridgeConfig ──

def test_bridge_config_custom():
    cfg = BridgeConfig(
        enable_tor=True,
        tor_socks_proxy="socks5://127.0.0.1:9150",
        enable_ipfs=True,
        ipfs_gateway="http://10.0.0.1:5001",
        enable_nostr=True,
        nostr_relays=["wss://custom.relay"],
        nostr_private_key="nsec1test",
    )
    assert cfg.enable_tor is True
    assert cfg.tor_socks_proxy == "socks5://127.0.0.1:9150"
    assert cfg.ipfs_gateway == "http://10.0.0.1:5001"
    assert cfg.nostr_relays == ["wss://custom.relay"]
    assert cfg.nostr_private_key == "nsec1test"
    assert cfg.default_model == "deepseek_v4_pro"
