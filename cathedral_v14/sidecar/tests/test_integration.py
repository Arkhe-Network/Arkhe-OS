import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from sidecar.client import CircuitBreaker, GgufSidecarClient

@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(max_failures=3, recovery_timeout=0.1, slow_threshold=1.0)

def test_circuit_breaker_initial_state(circuit_breaker):
    assert circuit_breaker.is_available() == True
    assert circuit_breaker.check() == True

def test_circuit_breaker_failure_trip(circuit_breaker):
    for _ in range(3):
        circuit_breaker.record_failure()
    assert circuit_breaker.is_available() == False
    assert circuit_breaker.check() == False

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(circuit_breaker):
    for _ in range(3):
        circuit_breaker.record_failure()

    assert circuit_breaker.check() == False
    await asyncio.sleep(0.15)

    assert circuit_breaker.check() == True
    assert circuit_breaker._state == "HALF_OPEN"

    circuit_breaker.record_success(0.5)
    assert circuit_breaker._state == "CLOSED"
    assert circuit_breaker.is_available() == True

@pytest.mark.asyncio
async def test_client_circuit_breaker():
    import aiohttp
    from aiohttp.test_utils import make_mocked_request
    pass
