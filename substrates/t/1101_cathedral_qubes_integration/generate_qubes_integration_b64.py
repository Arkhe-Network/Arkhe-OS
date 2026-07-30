import base64
import os

with open("cathedral_qubes_integration_1101.md", "rb") as f:
    md_content = f.read()

with open("substrate.toml", "rb") as f:
    toml_content = f.read()

md_b64 = base64.b64encode(md_content).decode("utf-8")
toml_b64 = base64.b64encode(toml_content).decode("utf-8")

with open("substrato_1101_cathedral_qubes_integration.py", "w") as f:
    f.write(f'''import json
import base64
from datetime import datetime, timezone

MD_B64 = "{md_b64}"
TOML_B64 = "{toml_b64}"

def canonize():
    report = {{
        "SubstrateID": "1101_cathedral_qubes",
        "Name": "CATHEDRAL-QUBES-INTEGRATION",
        "Status": "CANONIZED_PROVISIONAL",
        "Seal": "CATHEDRAL-QUBES-1101-v1.0.0-2026-06-12",
        "Files": {{
            "cathedral_qubes_integration_1101.md": base64.b64decode(MD_B64).decode("utf-8"),
            "substrate.toml": base64.b64decode(TOML_B64).decode("utf-8")
        }}
    }}

    return json.dumps(report, indent=2)

if __name__ == "__main__":
    print(canonize())
''')
