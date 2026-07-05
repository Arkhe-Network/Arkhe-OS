import json

from substrate_292_timelock import TimelockCommitmentEngine
from substrate_292_timelock.timelock_commitment import BitcoinTimelockBounty, HASH_ALGORITHM


FIXED_IVS = [bytes([i + 1]) * 32 for i in range(4)]


def test_create_timelock_commitment_is_deterministic_with_fixed_ivs():
    engine = TimelockCommitmentEngine(assumed_hash_rate=400)
    first = engine.create(b"arkhe sealed payload", delay_seconds=8, num_chains=4, ivs=FIXED_IVS)
    second = engine.create(b"arkhe sealed payload", delay_seconds=8, num_chains=4, ivs=FIXED_IVS)
    assert first.commitment_id == second.commitment_id
    assert first.total_iterations == 3200
    assert HASH_ALGORITHM == "sha256"


def test_precompute_all_chains_creates_watch_only_bounties():
    engine = TimelockCommitmentEngine(assumed_hash_rate=200)
    commitment = engine.create(b"tau-field", delay_seconds=4, num_chains=4, ivs=FIXED_IVS)
    bounties = engine.precompute_all_chains(commitment)
    assert len(bounties) == 4
    assert all(isinstance(bounty, BitcoinTimelockBounty) for bounty in bounties)
    assert all(bounty.watch_address.startswith("arkhe1tl") for bounty in bounties)


def test_locked_view_hides_all_but_first_iv():
    engine = TimelockCommitmentEngine(assumed_hash_rate=200)
    commitment = engine.create(b"future release", delay_seconds=4, num_chains=4, ivs=FIXED_IVS)
    engine.precompute_all_chains(commitment)
    locked = engine.lock_for_release(commitment)
    ivs = [chain["iv"] for chain in locked["chains"]]
    assert ivs[0] is not None
    assert ivs[1:] == [None, None, None]
    assert len(locked["canonical_seal"]) == 64


def test_constitutional_report_has_loopseal_and_gap():
    engine = TimelockCommitmentEngine(assumed_hash_rate=800)
    commitment = engine.create(b"constitutional timelock", delay_seconds=16, num_chains=4, ivs=FIXED_IVS)
    report = commitment.constitutional_report()
    assert report["loopseal"]
    assert report["gap"]
    assert 0 <= report["phi_c"] < 1


def test_unlock_from_locked_view_reports_serial_work():
    engine = TimelockCommitmentEngine(assumed_hash_rate=120)
    commitment = engine.create(b"serial open", delay_seconds=2, num_chains=3, ivs=FIXED_IVS[:3])
    engine.precompute_all_chains(commitment)
    locked = engine.lock_for_release(commitment)
    report = engine.unlock_from_locked_view(locked)
    assert report["chains_unlocked"] == 3
    assert report["serial_iterations"] == commitment.total_iterations
    assert len(report["canonical_seal"]) == 64


def test_timelock_json_serializable():
    engine = TimelockCommitmentEngine(assumed_hash_rate=200)
    commitment = engine.create(b"json", delay_seconds=4, num_chains=4, ivs=FIXED_IVS)
    payload = commitment.to_json()
    assert isinstance(json.dumps(payload), str)


def test_invalid_inputs_rejected():
    engine = TimelockCommitmentEngine(assumed_hash_rate=200)
    try:
        engine.create(b"x", delay_seconds=0, num_chains=1)
        assert False
    except ValueError:
        assert True

    try:
        TimelockCommitmentEngine(assumed_hash_rate=0)
        assert False
    except ValueError:
        assert True
