# package_orchestrator.py
"""
Orquestrador de pacotes para a Catedral OS v8.10
Gerencia clonagem, compilação e integração dos repositórios mapeados.
"""

import subprocess
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

PACKAGE_MAP = {
    "prolog": {
        "swipl": "https://github.com/SWI-Prolog/swipl-devel.git",
        "prolog-mcp": "https://github.com/umuro/prolog-mcp.git",
        "prolog-ai": "https://github.com/ai-university-aiu/PrologAI.git"
    },
    "robotics": {
        "knowrob": "https://github.com/knowrob/knowrob.git",
        "rosprolog": "https://github.com/knowrob/rosprolog.git"
    },
    "nanophotonics": {
        "cgan": "https://github.com/metaphotonics/Inverse-metasurface-design-CGAN.git",
        "autophotonic": "https://github.com/flexcompute/autophotonicdesign.git"
    },
    "6g": {
        "deterministic": "https://github.com/ustutt-ipvs-vs/6GDetCom_MKFirm.git"
    },
    "qkd": {
        "qosst": "https://github.com/QOSST/qosst.git"
    },
    "formal": {
        "symbiyosys": "https://github.com/YosysHQ/SymbiYosys.git",
        "lean4": "https://github.com/leanprover/lean4.git"
    }
}

class PackageOrchestrator:
    def __init__(self, base_dir: str = "./catedral_deps"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def clone_all(self, priority: str = "high"):
        """Clona todos os repositórios do mapa."""
        for category, repos in PACKAGE_MAP.items():
            for name, url in repos.items():
                target = self.base_dir / name
                if not target.exists():
                    print(f"📦 Clonando {name}...")
                    subprocess.run(["git", "clone", url, str(target)], check=True)
                else:
                    print(f"✅ {name} já existe.")

    def generate_manifest(self) -> Dict:
        """Gera um manifesto com os hashes e versões dos repositórios."""
        manifest = {}
        for category, repos in PACKAGE_MAP.items():
            manifest[category] = {}
            for name, url in repos.items():
                target = self.base_dir / name
                if target.exists():
                    result = subprocess.run(
                        ["git", "-C", str(target), "rev-parse", "HEAD"],
                        capture_output=True, text=True
                    )
                    manifest[category][name] = {
                        "url": url,
                        "hash": result.stdout.strip(),
                        "path": str(target)
                    }
        return manifest

if __name__ == "__main__":
    orchestrator = PackageOrchestrator()
    orchestrator.clone_all()
    manifest = orchestrator.generate_manifest()
    with open("manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("📋 Manifesto gerado em manifest.json")