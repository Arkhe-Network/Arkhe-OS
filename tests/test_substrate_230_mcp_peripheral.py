import hashlib

from substrates.substrate_230 import (
    Arkhe230Verifier,
    CANONICAL_PHI_C,
    MCPClient,
    MCPDocsSnapshot,
    MCPRequest,
    MCPServer,
    Severity,
    main,
)


def test_docs_snapshot_uses_official_plural_methods():
    docs = MCPDocsSnapshot()

    assert docs.jsonrpc == "2.0"
    assert docs.protocol_version == "2025-06-18"
    assert docs.tools_list_method == "tools/list"
    assert docs.tools_call_method == "tools/call"
    assert docs.list_changed_notification == "notifications/tools/list_changed"


def test_server_tools_list_returns_six_sorted_descriptors():
    server = MCPServer("memory")
    response = server.handle_request(MCPRequest(method="tools/list", params={}, id=1))
    tools = response.to_dict()["result"]["tools"]

    assert len(tools) == 6
    assert [tool["name"] for tool in tools] == sorted(tool["name"] for tool in tools)
    assert all("inputSchema" in tool for tool in tools)


def test_client_discovers_and_calls_tool():
    server = MCPServer("blockchain")
    client = MCPClient("AGI-000")

    tools = client.discover_tools(server)
    response = client.call_tool(server, "blockchain_trade", {"asset": "INJ", "amount": "100"})

    assert "blockchain_trade" in tools
    assert not response.error
    assert response.result["structuredContent"] == {"asset": "INJ", "amount": "100"}


def test_memory_server_persists_between_tool_calls():
    server = MCPServer("memory")
    client = MCPClient("AGI-001")

    client.call_tool(server, "memory_store", {"key": "alert_threshold", "value": "M8.0"})
    recall = client.call_tool(server, "memory_recall", {"key": "alert_threshold"})

    assert recall.result["structuredContent"]["value"] == "M8.0"


def test_security_rejects_unsafe_database_write_as_tool_error_result():
    server = MCPServer("filesystem")
    client = MCPClient("AGI-002")

    response = client.call_tool(server, "database_query", {"sql": "DROP TABLE users"})

    assert response.error is None
    assert response.result["isError"] is True
    assert "read-only" in response.result["content"][0]["text"]


def test_unknown_tool_returns_jsonrpc_error():
    server = MCPServer("github")
    client = MCPClient("AGI-003")

    response = client.call_tool(server, "missing_tool", {})

    assert response.error
    assert response.error.code == -32601


def test_verifier_runs_and_bridges_to_substrate_229():
    verifier = Arkhe230Verifier()
    verifier.run()
    report = verifier.report()
    checks = [check for result in verifier.results for check in result.checks]

    assert report["total_checks"] == 10
    assert report["passed_checks"] == 10
    assert report["ideal_phi_c"] == 1.0
    assert report["canonical_phi_c"] == CANONICAL_PHI_C
    assert any(inv == "MCP_OCTRA_BRIDGE" and sev == Severity.PASS for inv, sev, _, _ in checks)


def test_proof_packets_are_hash_bound():
    verifier = Arkhe230Verifier()
    verifier.run()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.platform_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_main_returns_report():
    report = main()

    assert report["substrate"] == 230
    assert report["status"] == "CANONIZED_SIMULATION"
    assert report["methods"] == ["tools/list", "tools/call"]
