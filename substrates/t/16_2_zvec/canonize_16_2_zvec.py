#!/usr/bin/env python3
import json
import base64
import os
import hashlib
from datetime import datetime

# Substrate 16.2
SEAL = "CATHEDRAL-ARKHE-v16.2-ZVEC-2026-06-14"

def read_file(path):
    with open(path, "rb") as f:
        return f.read()

def canonize():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    script_path = os.path.join(base_dir, "cathedral_arkhe_v16_2_zvec.py")
    toml_path = os.path.join(base_dir, "substrate.toml")

    script_bytes = read_file(script_path)
    toml_bytes = read_file(toml_path)

    script_b64 = base64.b64encode(script_bytes).decode("utf-8")
    toml_b64 = base64.b64encode(toml_bytes).decode("utf-8")

    report = {
        "substrate_id": "16.2",
        "seal": SEAL,
        "canonization_timestamp": datetime.utcnow().isoformat(),
        "artifacts": {
            "cathedral_arkhe_v16_2_zvec.py": {
                "base64": script_b64,
                "sha256": hashlib.sha256(script_bytes).hexdigest()
            },
            "substrate.toml": {
                "base64": toml_b64,
                "sha256": hashlib.sha256(toml_bytes).hexdigest()
            }
        }
    }

    report_path = os.path.join(base_dir, "canonized_report_16_2.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)

    print("Canonization complete. Report saved to: {0}".format(report_path))

if __name__ == "__main__":
    canonize()
