#!/usr/bin/env python3
# bridge.py — Conecta análises do BLOCK 11 ao Obsidian via Local REST API

import requests
import json
import hashlib
from datetime import datetime
import yaml
import os

OBSIDIAN_API = "http://localhost:27123"  # Local REST API plugin
# Use a mock API for testing

def post_analysis(title, content, domain, version, selo, base_dir="."):
    """Envia uma análise para o Obsidian como nota."""
    hash_val = hashlib.sha256(content.encode()).hexdigest()
    frontmatter = {
        "title": title,
        "type": "analysis",
        "domain": domain,
        "version": version,
        "date": datetime.now().isoformat(),
        "status": "rascunho",
        "hash": hash_val,
        "selo": selo,
        "tags": ["analysis", domain]
    }
    # Note: yaml.dump from pyyaml is needed, let's just make it a string
    fm_str = yaml.dump(frontmatter, default_flow_style=False)

    note = f"---\n{fm_str}---\n{content}"

    # Criar arquivo via API
    path = f"01 - Analyses/{domain}/{title}.md"
    try:
        response = requests.put(
            f"{OBSIDIAN_API}/vault/{path}",
            json={"content": note}
        )
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"Warning: Could not connect to {OBSIDIAN_API}. Make sure Obsidian Local REST API is running.")

        # fallback to local file writing if API not available
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(note)
        print(f"Wrote locally to {full_path}")
        return True

if __name__ == '__main__':
    # Test the bridge with a mock analysis
    title = "v2.6 - CTC Detector"
    content = "O detector de CTC aprimorado incorpora capacidade retrocausal one-shot..."
    domain = "BLOCK-11"
    version = "v2.6"
    selo = "HANKEL-SEAL-CTC-ENHANCED-v2.6-2026-08-11"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    post_analysis(title, content, domain, version, selo, base_dir=script_dir)
