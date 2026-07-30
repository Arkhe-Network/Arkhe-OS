import base64
import json
import os

def generate_canonizer():
    # Read files
    with open('caster_software_319_1.rs', 'rb') as f:
        rs_content = base64.b64encode(f.read()).decode('utf-8')

    with open('linux_metrics.rs', 'rb') as f:
        metrics_content = base64.b64encode(f.read()).decode('utf-8')

    with open('linux_wg_tunnel.rs', 'rb') as f:
        tunnel_content = base64.b64encode(f.read()).decode('utf-8')

    with open('substrate.toml', 'rb') as f:
        toml_content = base64.b64encode(f.read()).decode('utf-8')

    # Generate Python script
    py_code = """import base64
import json

payloads = {
    "caster_software_319_1.rs": \"\"\"""" + rs_content + """\"\"\",
    "linux_metrics.rs": \"\"\"""" + metrics_content + """\"\"\",
    "linux_wg_tunnel.rs": \"\"\"""" + tunnel_content + """\"\"\",
    "substrate.toml": \"\"\"""" + toml_content + """\"\"\"
}

def canonize():
    report = {
        "substrate_id": "319.1",
        "name": "Caster Software v1.0.0",
        "status": "CANONIZED_FULL",
        "seal": "CATHEDRAL-319.1-CASTER-SOFTWARE-v1.0.0-2026-06-13",
        "Files": {}
    }
    for file_path, content in payloads.items():
        report["Files"][file_path] = base64.b64decode(content).decode("utf-8")
    return json.dumps(report, indent=2)

if __name__ == '__main__':
    print(canonize())
"""

    with open('substrato_319_1.py', 'w') as f:
        f.write(py_code)

if __name__ == '__main__':
    generate_canonizer()
