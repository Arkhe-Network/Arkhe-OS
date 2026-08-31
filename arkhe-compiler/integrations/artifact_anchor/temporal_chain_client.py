#!/usr/bin/env python3
# temporal_chain_client.py – Cliente mock para TemporalChain

import json

class TemporalChainClient:
    def __init__(self, api_url="http://temporal.arkhe.local"):
        self.api_url = api_url

    def anchor_event(self, event_type: str, payload: dict) -> str:
        # Simula ancoragem (em produção: chamada HTTP)
        import hashlib
        data = json.dumps({"type": event_type, "payload": payload}, sort_keys=True)
        seal = hashlib.sha3_256(data.encode()).hexdigest()
        print(f"⚓ TemporalChain: {event_type} → {seal[:16]}...")
        return seal
