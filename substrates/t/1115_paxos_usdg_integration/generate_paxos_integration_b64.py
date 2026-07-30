import base64
import os

with open("paxos_gateway.py", "rb") as f:
    gateway_content = f.read()

with open("integration_example.py", "rb") as f:
    integration_content = f.read()

with open("test_paxos_gateway.py", "rb") as f:
    test_content = f.read()

with open("substrate.toml", "rb") as f:
    toml_content = f.read()

gateway_b64 = base64.b64encode(gateway_content).decode("utf-8")
integration_b64 = base64.b64encode(integration_content).decode("utf-8")
test_b64 = base64.b64encode(test_content).decode("utf-8")
toml_b64 = base64.b64encode(toml_content).decode("utf-8")

with open("substrato_1115_paxos_usdg_integration.py", "w") as f:
    f.write('import json\n')
    f.write('import base64\n')
    f.write('from datetime import datetime, timezone\n\n')
    f.write('GATEWAY_B64 = "' + gateway_b64 + '"\n')
    f.write('INTEGRATION_B64 = "' + integration_b64 + '"\n')
    f.write('TEST_B64 = "' + test_b64 + '"\n')
    f.write('TOML_B64 = "' + toml_b64 + '"\n\n')
    f.write('def canonize():\n')
    f.write('    report = {\n')
    f.write('        "SubstrateID": "1115_paxos_usdg",\n')
    f.write('        "Name": "CATHEDRAL-PAXOS-USDG-INTEGRATION",\n')
    f.write('        "Status": "CANONIZED_PROVISIONAL",\n')
    f.write('        "Seal": "CATHEDRAL-PAXOS-USDG-1115-v1.0.0-2026-06-15",\n')
    f.write('        "Files": {\n')
    f.write('            "paxos_gateway.py": base64.b64decode(GATEWAY_B64).decode("utf-8"),\n')
    f.write('            "integration_example.py": base64.b64decode(INTEGRATION_B64).decode("utf-8"),\n')
    f.write('            "test_paxos_gateway.py": base64.b64decode(TEST_B64).decode("utf-8"),\n')
    f.write('            "substrate.toml": base64.b64decode(TOML_B64).decode("utf-8")\n')
    f.write('        }\n')
    f.write('    }\n')
    f.write('    return json.dumps(report, indent=2)\n\n')
    f.write('if __name__ == "__main__":\n')
    f.write('    print(canonize())\n')
