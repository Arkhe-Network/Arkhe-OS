import base64
import json
import datetime

def canonize():
    payload_b64 = "IyBNVUxUSS1DVVQtT1VUIEJGVCArIENMQVNTSUZJQ0FDQU8gSElFUkFSUVVJQ0EKIyMgSW50cm9kdWN0aW9uClRoaXMgZG9jdW1lbnQgZGVzY3JpYmVzIHRoZSBSU0kgT3JjaGVzdHJhdG9ycyBpbiBCeXphbnRpbmUgRmF1bHQgVG9sZXJhbnQgY29uc2Vuc3VzIGFuZCBoaWVyYXJjaGljYWwgY2xhc3NpZmljYXRpb24gZW5mb3JjZW1lbnQgKExlYW40LCBURUUsIFpLKS4K"
    toml_b64 = "W3N1YnN0cmF0ZV0KaWQgPSAiMTIuOSIKbmFtZSA9ICJNVUxUSS1DVVQtT1VUIEJGVCArIENMQVNTSUZJQ0FDQU8gSElFUkFSUVVJQ0EiCnZlcnNpb24gPSAiMS4wLjAiCnR5cGUgPSAiZG9jdW1lbnRhdGlvbiIKYXV0aG9yID0gIkFya2hlIE9TIgoKW2Nhbm9uaXphdGlvbl0KcGF5bG9hZF9maWxlID0gIm11bHRpX2N1dF9vdXRfYmZ0Lm1kIgpzZWFsX2RhdGUgPSAiMjAyNi0wNi0xMiIKc3RhdGljX3NlYWwgPSAiTVVMVEktQ1VULU9VVC1CRlQtdjEuMC0yMDI2LTA2LTEyIgo="

    payload = base64.b64decode(payload_b64).decode('utf-8')
    toml = base64.b64decode(toml_b64).decode('utf-8')

    seal = "MULTI-CUT-OUT-BFT-v1.0-2026-06-12"

    report = {
        "substrate_id": "12.9",
        "name": "MULTI-CUT-OUT BFT + CLASSIFICACAO HIERARQUICA",
        "version": "1.0.0",
        "type": "documentation",
        "seal": seal,
        "timestamp": datetime.datetime.now().isoformat(),
        "payload": payload,
        "config": toml
    }

    return json.dumps(report, indent=2)

if __name__ == "__main__":
    print(canonize())
