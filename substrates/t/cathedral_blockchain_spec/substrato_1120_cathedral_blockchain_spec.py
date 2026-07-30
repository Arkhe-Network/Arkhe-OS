import os
import json
import base64

def canonize():
    """
    Canonizer for Cathedral Blockchain Spec.
    Generates canonical JSON report directly.
    """
    # Use relative paths or absolute. Since we test from root, let's use relative from root.
    spec_path = "substrates/t/cathedral_blockchain_spec/cathedral_blockchain_spec.md"
    config_path = "substrates/t/cathedral_blockchain_spec/substrate.toml"

    with open(spec_path, "r", encoding="utf-8") as spec_file:
        spec_content = spec_file.read()

    with open(config_path, "r", encoding="utf-8") as config_file:
        config_content = config_file.read()

    spec_b64 = base64.b64encode(spec_content.encode("utf-8")).decode("utf-8")
    config_b64 = base64.b64encode(config_content.encode("utf-8")).decode("utf-8")

    report = {
        "SubstrateID": "1120_cathedral_blockchain_spec",
        "Name": "CATHEDRAL BLOCKCHAIN SPECIFICATION",
        "Seal": "CATHEDRAL-BLOCKCHAIN-SPEC-v1.0.0-2026-06-13",
        "Status": "CANONIZED_FULL",
        "Files": [
            "cathedral_blockchain_spec.md",
            "substrate.toml"
        ],
        "Payloads": {
            "cathedral_blockchain_spec.md": spec_b64,
            "substrate.toml": config_b64
        }
    }

    return json.dumps(report, indent=4)

if __name__ == "__main__":
    print(canonize())
