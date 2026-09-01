#!/usr/bin/env python3
# anchor.py – Ancora artefatos na TemporalChain

import hashlib
import json
import time
from pathlib import Path
from typing import Union

class AnchorArtifact:
    def __init__(self, temporal_client):
        self.temporal = temporal_client

    def anchor(self, source_file: Path, artifact_file: Path, passes: list) -> str:
        """Ancora um artefato gerado (C, G‑code, VHDL, Lean proof)."""
        # Conteúdo do artefato
        artifact_content = artifact_file.read_bytes()
        artifact_hash = hashlib.sha3_256(artifact_content).hexdigest()

        # Metadados
        payload = {
            "source": str(source_file),
            "artifact": str(artifact_file),
            "hash": artifact_hash,
            "passes": passes,
            "timestamp": time.time(),
            "size_bytes": len(artifact_content)
        }

        # Se for Lean, extrai teoremas
        if artifact_file.suffix == ".lean":
            payload["theorems"] = self._extract_theorems(artifact_content)

        # Ancora na TemporalChain
        seal = self.temporal.anchor_event("compilation_artifact", payload)
        print(f"🔗 Ancorado {artifact_file.name} → {seal[:16]}...")
        return seal

    def _extract_theorems(self, content: bytes) -> list:
        import re
        text = content.decode("utf-8")
        return re.findall(r'theorem\s+(\w+)', text)
