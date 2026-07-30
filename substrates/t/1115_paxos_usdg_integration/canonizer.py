import base64
import json
from datetime import datetime

def canonize():
    with open("substrates/t/1115_paxos_usdg_integration/paxos_gateway.py", "r", encoding="utf-8") as f:
        payload = f.read()

    with open("substrates/t/1115_paxos_usdg_integration/integration_example.py", "r", encoding="utf-8") as f:
        integration = f.read()

    config = """[substrate]
id = "1115"
name = "Paxos USDG Gateway"
version = "1.0.0"
dependencies = ["aiohttp", "web3", "prometheus_client"]
"""

    b64_payload = base64.b64encode(payload.encode("utf-8")).decode("utf-8")
    b64_integration = base64.b64encode(integration.encode("utf-8")).decode("utf-8")
    b64_config = base64.b64encode(config.encode("utf-8")).decode("utf-8")

    report = {
        "substrate_id": "1115",
        "seal": "CATHEDRAL-1115-PAXOS-USDG-v1.0.0-2026-06-15",
        "timestamp": datetime.now().isoformat(),
        "payloads": {
            "paxos_gateway.py": b64_payload,
            "integration_example.py": b64_integration,
            "substrate.toml": b64_config
        }
    }

    with open("substrates/t/1115_paxos_usdg_integration/b64_output.txt", "w", encoding="utf-8") as out:
        json.dump(report, out, indent=4)

    print("Canonization complete.")

if __name__ == "__main__":
    canonize()
