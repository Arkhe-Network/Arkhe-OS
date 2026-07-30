import base64
import json
import os
from datetime import datetime

def read_and_encode(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        content = file.read()
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")

def canonize():
    base_dir = "substrates/t/4004_b20_base_bridge"

    files_to_encode = [
        "b20_mapper.rs",
        "policy_adapter.rs",
        "compliance_engine.rs",
        "settlement_engine.rs",
        "memo_tracer.rs",
        "cross_chain_bridge.rs",
        "b20_integration_tests.rs",
        "dashboard-b20.yml",
        "substrate.toml"
    ]

    payloads = {}
    for filename in files_to_encode:
        filepath = os.path.join(base_dir, filename)
        payloads[filename] = read_and_encode(filepath)

    report = {
        "substrate_id": "4004",
        "seal": "CATHEDRAL-ARKHE-SUBSTRATO-4004-v1.0.0-2026-06-18",
        "timestamp": datetime.now().isoformat(),
        "payloads": payloads
    }

    output_path = os.path.join(base_dir, "b64_output.json")
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(report, out, indent=4)

    print("Canonization complete. Output saved to {0}".format(output_path))

if __name__ == "__main__":
    canonize()
