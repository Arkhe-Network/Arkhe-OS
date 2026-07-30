import base64
import json
from pathlib import Path
import os
import hashlib

def get_file_content(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def main():
    base_dir = "substrates/t/1104_2_rio35_open_397b_integration"

    arkhe_rs = get_file_content(f"{base_dir}/arkhe_1104_2_engine.rs")
    vllm_yaml = get_file_content(f"{base_dir}/vllm_rio35.yaml")
    run_chat = get_file_content(f"{base_dir}/run_chat_rio35.py")
    makefile = get_file_content(f"{base_dir}/Makefile_rio35")
    calibration = get_file_content(f"{base_dir}/calibration_report_template.json")
    artifacts = get_file_content(f"{base_dir}/artifacts.json")
    toml = get_file_content(f"{base_dir}/substrate.toml")

    # Avoid f-strings in canonizer output!
    canonizer_script = """import base64
import json
import hashlib

def decode_b64(b64_str):
    return base64.b64decode(b64_str).decode('utf-8')

def canonize():
    arkhe_rs_b64 = "{0}"
    vllm_yaml_b64 = "{1}"
    run_chat_b64 = "{2}"
    makefile_b64 = "{3}"
    calibration_b64 = "{4}"
    artifacts_b64 = "{5}"
    toml_b64 = "{6}"

    arkhe_rs = decode_b64(arkhe_rs_b64)
    vllm_yaml = decode_b64(vllm_yaml_b64)
    run_chat = decode_b64(run_chat_b64)
    makefile = decode_b64(makefile_b64)
    calibration = decode_b64(calibration_b64)
    artifacts = decode_b64(artifacts_b64)
    toml = decode_b64(toml_b64)

    return json.dumps({{
        "arkhe_1104_2_engine.rs": arkhe_rs,
        "vllm_rio35.yaml": vllm_yaml,
        "run_chat_rio35.py": run_chat,
        "Makefile_rio35": makefile,
        "calibration_report_template.json": calibration,
        "artifacts.json": artifacts,
        "substrate.toml": toml,
        "seal": "CATHEDRAL-1104.2-RIO35-ENGINE-2026-06-13"
    }}, indent=2)

if __name__ == '__main__':
    print(canonize())
""".format(
        base64.b64encode(arkhe_rs.encode()).decode(),
        base64.b64encode(vllm_yaml.encode()).decode(),
        base64.b64encode(run_chat.encode()).decode(),
        base64.b64encode(makefile.encode()).decode(),
        base64.b64encode(calibration.encode()).decode(),
        base64.b64encode(artifacts.encode()).decode(),
        base64.b64encode(toml.encode()).decode()
    )

    with open(f"{base_dir}/canonize.py", "w") as f:
        f.write(canonizer_script)

if __name__ == '__main__':
    main()
