"""Synthetic 10,000-parse concurrency smoke test.

This intentionally uses a deterministic parser stub so CI can measure scheduler
and orchestration overhead without requiring every production grammar to exist.
Real grammar stress tests can replace parse_one while preserving the contract.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import time


def parse_one(index: int) -> str:
    source = f"IDENTIFICATION DIVISION. PROGRAM-ID. ARKHE{index}. STOP RUN."
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def main() -> int:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        results = list(pool.map(parse_one, range(10_000)))
    elapsed = time.perf_counter() - started
    assert len(results) == 10_000
    assert len(set(results)) == 10_000
    print(f"10000 parses completed in {elapsed:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

