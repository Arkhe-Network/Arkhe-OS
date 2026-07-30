import json
import base64
import os
from datetime import datetime, timezone

def to_base64(filepath):
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    files = {}

    for root, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename == "canonizer_8000.py":
                continue
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, base_dir)
            files[rel_path] = to_base64(filepath)

    report = {
        "SubstrateID": "8000",
        "Name": "HEADROOM_BRIDGE",
        "Type": "Context Compression Layer",
        "Version": "1.0.0",
        "Era": "8",
        "Status": "CANONIZED_FULL",
        "Timestamp": datetime.now(timezone.utc).isoformat(),
        "Seal": "CATHEDRAL-ARKHE-8000-HEADROOM-v1.0.0-2026-06-18",
        "Files": files
    }

    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
