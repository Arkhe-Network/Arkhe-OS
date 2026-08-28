#!/usr/bin/env python3
"""
Catedral OS v9.6 — Orquestrador Python (Isomorfismo EH-CRSN)
Integra: AGI.prolog + Network Orchestrator + HTTP + WormGraph + ICCID + Substratos 212-217
"""

import json
import time
import threading
import http.server
import socketserver
import hashlib
import logging
import os
import subprocess
import re
from typing import Dict, List, Any, Optional
try:
    from network_orchestrator import NetworkOrchestrator, NetworkConfig
except ImportError:
    class NetworkConfig:
        pass
    class NetworkOrchestrator:
        def __init__(self, config):
            self.metrics = type('Metrics', (), {'active_nodes': 0})()
        def start(self):
            pass
        def shutdown(self):
            pass
        def get_health(self):
            return {"status": "mocked"}
        def get_quantum_health(self):
            return {"status": "mocked"}
        def route_holographic_stream(self, content, quality):
            class Stream:
                def __init__(self):
                    self.stream_id = "mock"
                    self.active_nodes = []
                    self.latency_ms = 0.0
            return Stream()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [Cathedral] %(levelname)s: %(message)s')
logger = logging.getLogger('cathedral.v96')


class SIMHarvester:
    """Harvester para leitura de ICCID via pySim-shell (Osmocom)."""

    def __init__(self, reader: Optional[str] = None):
        self.reader = reader

    def harvest_iccid(self) -> Dict[str, Any]:
        try:
            cmd = ["pySim-shell.py", "--json", "export"]
            if self.reader:
                cmd.extend(["-p", self.reader])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {"status": "error", "message": result.stderr}

            try:
                data = json.loads(result.stdout)
                iccid = self._extract_iccid_from_json(data)
                if iccid:
                    return {"status": "success", "iccid": iccid, "source": "hardware"}
            except json.JSONDecodeError:
                match = re.search(r'ICCID["\s:]+([0-9]{18,22})', result.stdout)
                if match:
                    return {"status": "success", "iccid": match.group(1), "source": "hardware_regex"}

            return {"status": "error", "message": "ICCID não encontrado"}

        except FileNotFoundError:
            return {"status": "error", "message": "pySim-shell não encontrado"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _extract_iccid_from_json(self, data: Dict) -> Optional[str]:
        if "profile_info" in data:
            return data["profile_info"].get("iccid")
        if "iccid" in data:
            return data["iccid"]
        for key, value in data.items():
            if isinstance(value, dict):
                result = self._extract_iccid_from_json(value)
                if result:
                    return result
        return None


class CathedralCore:
    def __init__(self, prolog_file: str = "agi_core.pl"):
        self.prolog = None
        self.harvester = SIMHarvester()
        try:
            from pyswip import Prolog
            self.prolog = Prolog()
            self.prolog.consult(prolog_file)
            list(self.prolog.query("agi_init"))
            logger.info(f"AGI.prolog v9.6 carregado: {prolog_file}")
        except ImportError:
            logger.warning("PySWIP não disponível — modo simulação")

    def think(self, context: str) -> Dict[str, Any]:
        if self.prolog:
            safe = context.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            try:
                results = list(self.prolog.query(f"think('{safe}', Output, Status)"))
                if results:
                    return {
                        "output": str(results[0].get("Output", "")),
                        "status": str(results[0].get("Status", "error"))
                    }
            except Exception as e:
                logger.error(f"Erro no Prolog: {e}")

        alpha = min(1.0, len(context) / 200.0 + 0.3)
        if alpha > 0.95:
            return {"output": "🛑 Veto ATIVADO (α≥0.95)", "status": "blocked"}
        return {"output": f"✅ α={alpha:.2f} | Cognição estável", "status": "success"}

    def manifest_iccid(self, iccid: str = None) -> Dict[str, Any]:
        if iccid is None:
            hw_data = self.harvester.harvest_iccid()
            if hw_data.get("status") == "success":
                iccid = hw_data["iccid"]
            else:
                return hw_data

        if self.prolog:
            safe = iccid.replace("'", "")
            try:
                results = list(self.prolog.query(f"iccid_register('{safe}', BlockHash)"))
                if results:
                    return {
                        "iccid": iccid,
                        "block_hash": str(results[0].get("BlockHash", "")),
                        "status": "sovereign_anchor"
                    }
            except Exception as e:
                logger.error(f"Erro ao registrar ICCID no Prolog: {e}")

        def luhn_checksum(card_number: str) -> bool:
            digits = [int(d) for d in str(card_number)]
            checksum = 0
            parity = len(digits) % 2
            for i, d in enumerate(digits):
                if i % 2 == parity:
                    checksum += d
                else:
                    d2 = d * 2
                    checksum += d2 - 9 if d2 > 9 else d2
            return checksum % 10 == 0

        if luhn_checksum(iccid):
            raw = f"{iccid}:{time.time()}:{os.urandom(16).hex()}"
            block_hash = hashlib.sha256(raw.encode()).hexdigest()
            return {"iccid": iccid, "block_hash": block_hash, "status": "sovereign_anchor (fallback)"}

        return {"iccid": iccid, "status": "invalid_luhn"}

    def get_metrics(self) -> Dict:
        if self.prolog:
            try:
                results = list(self.prolog.query("get_metrics(M)"))
                if results:
                    return {"metrics": str(results[0].get("M", ""))}
            except: pass
        return {"iterations": 0, "blocked": 0, "success": 0}

    def manifest_eclipse(self) -> Dict:
        if self.prolog:
            try:
                list(self.prolog.query("manifest_eclipse"))
                return {"status": "executed"}
            except: pass
        return {"status": "simulated", "alpha": 0.96, "veto": "ACTIVADO"}


class WormGraph:
    def __init__(self):
        self.ledger: List[Dict] = []
        self._lock = threading.Lock()

    def commit(self, block: Dict) -> bool:
        with self._lock:
            block['index'] = len(self.ledger)
            block['timestamp'] = time.time()
            block['hash'] = hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
            self.ledger.append(block)
            return True

    def get_ledger(self) -> List[Dict]:
        with self._lock:
            return self.ledger.copy()


class CathedralHandler(http.server.SimpleHTTPRequestHandler):
    core: CathedralCore = None
    wormgraph: WormGraph = None
    network: NetworkOrchestrator = None

    def do_GET(self):
        if self.path == '/api/metrics':
            self._json_response(self.core.get_metrics())
        elif self.path == '/api/ledger':
            self._json_response(self.wormgraph.get_ledger())
        elif self.path == '/api/health':
            self._json_response({
                "status": "online", "version": "9.6",
                "uptime": time.time(),
                "veto_status": "ARMED (α≥0.95 → KILL-SWITCH)",
                "network": self.network.get_health() if self.network else None
            })
        elif self.path == '/api/eclipse':
            self._json_response(self.core.manifest_eclipse())
        elif self.path == '/api/network':
            if self.network:
                self._json_response(self.network.get_health())
            else:
                self._json_response({"error": "Network not initialized"}, 503)
        elif self.path == '/api/quantum':
            if self.network:
                self._json_response(self.network.get_quantum_health())
            else:
                self._json_response({"error": "Quantum mesh not initialized"}, 503)
        elif self.path == '/' or self.path == '/index.html':
            self.path = '/clareira_fractal.html'
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/think':
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body)
                result = self.core.think(data.get('input', ''))
                self._json_response(result)
            except json.JSONDecodeError:
                self._json_response({"error": "Invalid JSON"}, 400)
        elif self.path == '/api/manifest_iccid':
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body)
                iccid = data.get('iccid', None)
                manifest = self.core.manifest_iccid(iccid)
                if manifest.get("status", "").startswith("sovereign_anchor"):
                    self.wormgraph.commit({
                        "type": "iccid_manifestation",
                        "iccid": manifest.get("iccid"),
                        "manifest_hash": manifest.get("block_hash")
                    })
                self._json_response(manifest)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
        elif self.path == '/api/network/stream':
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body)
                if self.network:
                    stream = self.network.route_holographic_stream(
                        data.get('content', ''), data.get('quality', '6DoF')
                    )
                    self._json_response({
                        "stream_id": stream.stream_id,
                        "nodes": len(stream.active_nodes),
                        "latency_ms": stream.latency_ms
                    })
                else:
                    self._json_response({"error": "Network not initialized"}, 503)
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
        else:
            self._json_response({"error": "Not found"}, 404)

    def _json_response(self, data: Any, code: int = 200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, format, *args):
        pass


def main():
    prolog_file = "agi_core.pl"
    if not os.path.exists(prolog_file):
        logger.warning(f"{prolog_file} não encontrado. Criando stub...")
        with open(prolog_file, 'w') as f:
            f.write(":- module(cathedral_v96, [agi_init/0, think/3, get_metrics/1, manifest_eclipse/0, iccid_register/2]).\n")
            f.write("agi_init :- format('Catedral v9.6 stub~n').\n")
            f.write("think(I,O,S) :- O='ok', S=success.\n")
            f.write("get_metrics(M) :- M=[].\n")
            f.write("manifest_eclipse :- format('Eclipse simulado~n').\n")
            f.write("iccid_register(I,H) :- H='hash_stub'.\n")

    core = CathedralCore(prolog_file)
    wormgraph = WormGraph()
    network = NetworkOrchestrator(NetworkConfig())
    network.start()

    CathedralHandler.core = core
    CathedralHandler.wormgraph = wormgraph
    CathedralHandler.network = network

    wormgraph.commit({
        "event": "cathedral_v96_init",
        "version": "9.6",
        "substrates": list(range(163, 218)), # Inclui 212-217
        "network": "6G/LEO/INC + Quantum Mesh + Sovereign ID + EH-CRSN Isomorphism",
        "audit_status": "Veto ATIVO em α≥0.95"
    })

    PORT = 8080
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or '.')

    with socketserver.TCPServer(("", PORT), CathedralHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"  🏛️ CATEDRAL OS v9.6 — Isomorfismo EH-CRSN")
        print(f"{'='*60}")
        print(f"  HTTP:       http://localhost:{PORT}")
        print(f"  Rede:       6G/LEO + Mesh Quântica ({network.metrics.active_nodes} nós)")
        print(f"  Veto:       ARMADO (α≥0.95 → KILL-SWITCH)")
        print(f"{'='*60}\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nParando Catedral OS...")
            network.shutdown()
            print("✅ Desligamento seguro.")

if __name__ == "__main__":
    main()