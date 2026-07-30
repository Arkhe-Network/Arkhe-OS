import json
import base64
import os
from datetime import datetime, timezone

def to_base64(filepath):
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    wp_path = os.path.join(base_dir, "FSI_Whitepaper_v1.0.0.md")
    router_path = os.path.join(base_dir, "federated_router.rs")
    sol_path = os.path.join(base_dir, "ArkheFederation.sol")
    risk_path = os.path.join(base_dir, "FSI_Risk_Matrix_v1.0.0.md")
    manifest_path = os.path.join(base_dir, "manifest_1200.json")
    creek_path = os.path.join(base_dir, "creek_guard_stub.rs")
    rbb_path = os.path.join(base_dir, "rbb_client_stub.rs")
    toml_path = os.path.join(base_dir, "substrate.toml")

    report = {
        "SubstrateID": "1200",
        "Name": "FEDERACAO_SOBERANA_INFERENCIA",
        "Type": "Architecture",
        "Version": "1.0.0",
        "Era": "12",
        "Status": "CANONIZED_FULL",
        "Timestamp": datetime.now(timezone.utc).isoformat(),
        "Seal": "CATHEDRAL-1200-FSI-v1.0.0-2026-06-13",
        "Files": {
            "FSI_Whitepaper_v1.0.0.md": to_base64(wp_path),
            "federated_router.rs": to_base64(router_path),
            "ArkheFederation.sol": to_base64(sol_path),
            "FSI_Risk_Matrix_v1.0.0.md": to_base64(risk_path),
            "manifest_1200.json": to_base64(manifest_path),
            "creek_guard_stub.rs": to_base64(creek_path),
            "rbb_client_stub.rs": to_base64(rbb_path),
            "substrate.toml": to_base64(toml_path)
        }
    }

    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()