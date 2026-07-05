import json

from substrates.substrate_228 import AMLCompiler, compile_aml


SOURCE = """
contract VisibleToken {
    storage balances: map[address]int;
    storage grants: map[address]map[address]int;
    storage encrypted_votes: map[address]ciphertext;

    fn transfer(to: address, amount: int) -> bool {
        require amount > 0;
        balances[caller] = balances[caller] - amount;
        balances[to] = balances[to] + amount;
        emit Transfer(caller, to, amount);
        return true;
    }

    fn encrypted_tally(a: ciphertext, b: ciphertext) -> ciphertext {
        return hfhe_add(a, b);
    }
}
"""


def test_parser_extracts_storage_functions_and_abi():
    program = AMLCompiler().parse(SOURCE)

    assert program.name == "VisibleToken"
    assert [item.name for item in program.storage] == ["balances", "grants", "encrypted_votes"]
    assert [fn.name for fn in program.functions] == ["transfer", "encrypted_tally"]
    assert program.abi[0]["inputs"] == [
        {"name": "to", "type": "address"},
        {"name": "amount", "type": "int"},
    ]


def test_storage_keys_are_visible_composite_keys():
    artifact = compile_aml(SOURCE)

    assert "balances:<address>" in artifact.storage_keys
    assert "grants:<address>:<address>" in artifact.storage_keys
    assert any(line == "STORAGE_STORE balances:caller" for line in artifact.assembly)
    assert any(line == "STORAGE_STORE balances:to" for line in artifact.assembly)


def test_lowering_exposes_require_events_return_and_bytecode():
    artifact = compile_aml(SOURCE)

    assert "EVAL amount > 0" in artifact.assembly
    assert "REVERT_IF_FALSE" in artifact.assembly
    assert "EMIT Transfer(caller, to, amount)" in artifact.assembly
    assert artifact.bytecode.startswith("OCTB:")
    assert len(artifact.bytecode) == len("OCTB:") + 64


def test_source_to_assembly_proofs_are_hash_bound():
    artifact = compile_aml(SOURCE)
    proof = next(p for p in artifact.proofs if p.source == "balances[caller] = balances[caller] - amount")

    assert proof.rule == "storage_store"
    assert proof.assembly == ("EVAL balances[caller] - amount", "STORAGE_STORE balances:caller")
    assert len(proof.digest) == 64


def test_artifact_json_is_auditable_and_stable_for_same_source():
    first = compile_aml(SOURCE)
    second = compile_aml(SOURCE)
    payload = json.loads(first.to_json())

    assert first.bytecode == second.bytecode
    assert first.source_hash == second.source_hash
    assert payload["schema"] == "arkhe.substrate228.visible_lowering.v1"
    assert payload["program"] == "VisibleToken"
