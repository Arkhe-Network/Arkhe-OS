#!/usr/bin/env python3
# Cathedral Substrate 12.9 Canonizer
# MULTI-CUT-OUT BFT + CLASSIFICACAO HIERARQUICA
# Note: F-strings are strictly forbidden in this script.

import os
import sys
import json
import base64
import hashlib
from datetime import datetime

# ==============================================================================
# BASE64 PAYLOADS
# ==============================================================================

# In a real environment these are generated programmatically, but to simulate the script embedding:
# We will read them directly if they exist to package them.

def _get_base64_of_file(filepath):
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return ""

def canonize():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    multi_cut_out_bft_path = os.path.join(base_dir, "multi_cut_out_bft.py")
    classification_enforcement_path = os.path.join(base_dir, "classification_enforcement.py")
    md_path = os.path.join(base_dir, "cathedral_v12_9_multi_cut_out.md")
    toml_path = os.path.join(base_dir, "substrate.toml")

    # Encode files
    multi_cut_out_bft_b64 = _get_base64_of_file(multi_cut_out_bft_path)
    classification_enforcement_b64 = _get_base64_of_file(classification_enforcement_path)
    md_b64 = _get_base64_of_file(md_path)
    toml_b64 = _get_base64_of_file(toml_path)

    # Compute a dynamic seal
    seal_material = "{}:{}:{}:{}".format(
        hashlib.sha3_256(multi_cut_out_bft_b64.encode()).hexdigest(),
        hashlib.sha3_256(classification_enforcement_b64.encode()).hexdigest(),
        hashlib.sha3_256(md_b64.encode()).hexdigest(),
        hashlib.sha3_256(toml_b64.encode()).hexdigest()
    )
    seal_hash = hashlib.sha3_256(seal_material.encode()).hexdigest()
    seal = "CATHEDRAL-v12.9-MULTI-CUT-OUT-BFT-2026-06-12-{}".format(seal_hash[:8])

    report = {
        "SubstrateID": "12_9_multi_cut_out_bft",
        "Name": "MULTI-CUT-OUT BFT + CLASSIFICACAO HIERARQUICA",
        "Status": "CANONIZED_FULL",
        "Timestamp": datetime.now().isoformat(),
        "Seal": seal,
        "Files": [
            "multi_cut_out_bft.py",
            "classification_enforcement.py",
            "cathedral_v12_9_multi_cut_out.md",
            "substrate.toml"
        ],
        "Payloads": {
            "multi_cut_out_bft.py": multi_cut_out_bft_b64,
            "classification_enforcement.py": classification_enforcement_b64,
            "cathedral_v12_9_multi_cut_out.md": md_b64,
            "substrate.toml": toml_b64
        }
    }

    return json.dumps(report, indent=4)

if __name__ == "__main__":
    print(canonize())
