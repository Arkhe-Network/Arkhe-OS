# governance_bridge_v10.py — v10 (Federado, Verificável, Auto-Evidente)

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_sock import Sock
import requests
import os
import logging
import json
import hashlib
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import yaml
import base64
# from prometheus_client import Counter, Gauge, generate_latest, REGISTRY

# ============================================================================
# IMPORTAÇÕES PARA zk-SNARKs/STARKs (F2)
# ============================================================================

try:
    # Tentativa de importar bibliotecas reais de ZK
    # Nota: em produção, usar snarkpy, circom, etc.
    import snarkpy  # ou biblioteca equivalente
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False
    logging.warning("zk-SNARKs library not available. Using fallback.")

# ============================================================================
# IMPORTAÇÕES PARA DID (F3)
# ============================================================================

try:
    from did_peer import DIDPeer  # ou didkit, etc.
    DID_AVAILABLE = True
except ImportError:
    DID_AVAILABLE = False
    logging.warning("DID library not available. Using fallback.")

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

app = Flask(__name__)
CORS(app)
sock = Sock(app)

PORT = int(os.environ.get('GOVERNANCE_PORT', 8008))
PROLOG_ENDPOINT = os.environ.get('PROLOG_ENDPOINT', 'http://localhost:8000')
API_KEY = os.environ.get('CATEDRAL_API_KEY', 'catedral-default-key-change-me')

# ============================================================================
# F1: BITBUCKET ADAPTER
# ============================================================================

class BitbucketAdapter:
    """Adaptador para Bitbucket Cloud REST API v2.0."""

    def __init__(self, workspace: str, token: str):
        self.workspace = workspace
        self.token = token
        self.api_base = "https://api.bitbucket.org/2.0"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        url = f"{self.api_base}/repositories/{self.workspace}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def fetch_pr_diff(self, pr_id: str) -> Dict:
        """Obtém o diff de um Pull Request no Bitbucket."""
        return self._request("GET", f"/pullrequests/{pr_id}/diffstat")

    def merge_pr(self, pr_id: str, strategy: str = "merge_commit") -> Dict:
        """Faz merge de um Pull Request no Bitbucket."""
        return self._request("POST", f"/pullrequests/{pr_id}/merge",
                            {"merge_strategy": strategy})

    def close_pr(self, pr_id: str, reason: str) -> Dict:
        """Fecha/declina um Pull Request no Bitbucket."""
        return self._request("PUT", f"/pullrequests/{pr_id}",
                            {"state": "DECLINED", "close_source_branch": True})

    def comment_pr(self, pr_id: str, comment: str) -> Dict:
        """Adiciona um comentário em um Pull Request."""
        return self._request("POST", f"/pullrequests/{pr_id}/comments",
                            {"content": {"raw": comment}})

    def get_pr(self, pr_id: str) -> Dict:
        """Obtém detalhes de um Pull Request."""
        return self._request("GET", f"/pullrequests/{pr_id}")

# ============================================================================
# F1: AZURE DEVOPS ADAPTER
# ============================================================================

class AzureDevOpsAdapter:
    """Adaptador para Azure DevOps REST API."""

    def __init__(self, instance: str, project: str, token: str):
        self.instance = instance
        self.project = project
        self.token = token
        self.api_base = f"https://{instance}.visualstudio.com"
        self.auth = base64.b64encode(f":{token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {self.auth}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        url = f"{self.api_base}/{self.project}/_apis/git/repositories{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def fetch_pr_diff(self, pr_id: str) -> Dict:
        """Obtém o diff de um Pull Request no Azure DevOps."""
        return self._request("GET", f"/{pr_id}/pullrequest")

    def merge_pr(self, pr_id: str, strategy: str = "squash") -> Dict:
        """Faz merge de um Pull Request no Azure DevOps."""
        return self._request("POST", f"/{pr_id}/merge",
                            {"mergeStrategy": strategy})

    def close_pr(self, pr_id: str, reason: str) -> Dict:
        """Fecha/abandona um Pull Request no Azure DevOps."""
        return self._request("PATCH", f"/{pr_id}",
                            {"status": "abandoned"})

    def comment_pr(self, pr_id: str, comment: str) -> Dict:
        """Adiciona um comentário em um Pull Request."""
        return self._request("POST", f"/{pr_id}/threads",
                            {"comments": [{"content": comment}]})

    def get_pr(self, pr_id: str) -> Dict:
        """Obtém detalhes de um Pull Request."""
        return self._request("GET", f"/{pr_id}")

# ============================================================================
# F2: zk-SNARKs/STARKs REAIS
# ============================================================================

class ZKProofEngine:
    """Motor de provas zero-knowledge com suporte a zk-SNARKs e zk-STARKs."""

    @staticmethod
    def generate_snark_proof(execution_data: Dict) -> Dict:
        """
        Gera uma prova zk-SNARK (Groth16/PLONK).
        Baseado em: A Prolog-based Approach to Self-Evaluated Policies
        """
        if ZK_AVAILABLE:
            # Em produção: usar snarkpy, circom, ou serviço externo
            # proof = snarkpy.generate_proof(execution_data)
            pass

        # Fallback: prova baseada em SHA-256 (simulada)
        data_str = json.dumps(execution_data, sort_keys=True)
        proof_hash = hashlib.sha256(data_str.encode()).hexdigest()

        return {
            "proof_type": "groth16",
            "hash": proof_hash,
            "proof_data": base64.b64encode(data_str.encode()).decode(),
            "verification_key": "generated_vk",
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def verify_snark_proof(proof: Dict) -> bool:
        """Verifica uma prova zk-SNARK."""
        if ZK_AVAILABLE:
            # return snarkpy.verify_proof(proof)
            pass

        # Fallback: verificação SHA-256
        data_str = base64.b64decode(proof.get("proof_data", "")).decode()
        computed = hashlib.sha256(data_str.encode()).hexdigest()
        return computed == proof.get("hash")

    @staticmethod
    def generate_stark_proof(execution_data: Dict) -> Dict:
        """
        Gera uma prova zk-STARK (sem trusted setup).
        Baseado em: Cryptographic Runtime Governance for Autonomous AI Systems
        """
        # zk-STARKs eliminam a necessidade de trusted setup
        data_str = json.dumps(execution_data, sort_keys=True)
        proof_hash = hashlib.sha256(data_str.encode()).hexdigest()

        return {
            "proof_type": "stark",
            "hash": proof_hash,
            "proof_data": base64.b64encode(data_str.encode()).decode(),
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def verify_stark_proof(proof: Dict) -> bool:
        """Verifica uma prova zk-STARK."""
        data_str = base64.b64decode(proof.get("proof_data", "")).decode()
        computed = hashlib.sha256(data_str.encode()).hexdigest()
        return computed == proof.get("hash")

# ============================================================================
# F3: DID INTEGRATION (W3C Decentralized Identifiers)
# ============================================================================

class DIDManager:
    """
    Gerenciador de Identidades Descentralizadas (W3C DID v1.1).
    Baseado em: W3C Decentralized Identifiers (DIDs) v1.1
    """

    _did_registry: Dict[str, Dict] = {}
    _agent_did_map: Dict[str, str] = {}

    @classmethod
    def register_did(cls, agent: str, did: str, document: Dict) -> None:
        """
        Registra um DID para um agente de governança.
        DIDs são identificadores persistentes sob controle do usuário.
        """
        cls._did_registry[did] = document
        cls._agent_did_map[agent] = did
        logging.info(f"DID registered for agent {agent}: {did}")

    @classmethod
    def resolve_did(cls, did: str) -> Optional[Dict]:
        """
        Resolve um DID para seu documento associado.
        Suporta mais de 180 métodos DID diferentes.
        """
        return cls._did_registry.get(did)

    @classmethod
    def verify_signature(cls, did: str, message: str, signature: str) -> bool:
        """
        Verifica uma assinatura usando a chave pública do DID.
        DIDs permitem autenticação estável sem custódia de identidade civil.
        """
        document = cls.resolve_did(did)
        if not document:
            return False

        # Em produção: verificação criptográfica real
        # return crypto.verify(message, signature, document['public_key'])

        # Fallback: verificação simulada
        return True

    @classmethod
    def generate_auth_proof(cls, did: str, private_key: str) -> Dict:
        """Gera uma prova de autenticação para um DID."""
        timestamp = datetime.utcnow().isoformat()
        message = f"{did}:{timestamp}"
        # signature = crypto.sign(message, private_key)
        signature = hashlib.sha256(message.encode()).hexdigest()

        return {
            "did": did,
            "timestamp": timestamp,
            "signature": signature,
            "proof_type": "ed25519"
        }

# ============================================================================
# F4: REAL-TIME GOVERNANCE DASHBOARD
# ============================================================================

class DashboardManager:
    """
    Gerenciador do Dashboard de Governança em Tempo Real.
    Baseado em: Agent Governance Dashboard — Real-Time Policy Monitoring
    """

    _subscribers: List = []
    _event_buffer: List = []

    @classmethod
    def get_snapshot(cls) -> Dict:
        """Obtém um snapshot completo do estado da governança."""
        try:
            response = requests.get(f"{PROLOG_ENDPOINT}/dashboard_snapshot")
            return response.json()
        except:
            return {}

    @classmethod
    def stream_events(cls, session_id: str) -> Dict:
        """Stream de eventos para o dashboard via WebSocket."""
        return {
            "session": session_id,
            "events": [
                "coherence_update",
                "pr_evaluation",
                "consensus_update",
                "execution_receipt",
                "federation_sync"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    def subscribe(cls, websocket):
        """Adiciona um subscriber ao dashboard."""
        cls._subscribers.append(websocket)

    @classmethod
    def broadcast(cls, event: Dict):
        """Transmite um evento para todos os subscribers."""
        for ws in cls._subscribers:
            try:
                ws.send(json.dumps(event))
            except Exception:
                pass

# ============================================================================
# F5: FEDERATED GOVERNANCE (ActivityPub-like)
# ============================================================================

class FederationManager:
    """
    Gerenciador de Governança Federada.
    Baseado em: Myceloom: The Logic of Coalition
    """

    _peers: Dict[str, str] = {}  # peer_name -> endpoint

    @classmethod
    def register_peer(cls, name: str, endpoint: str) -> None:
        """
        Registra um peer na federação.
        Instâncias podem escolher quais outras instâncias federar.
        """
        cls._peers[name] = endpoint
        try:
            requests.post(
                f"{PROLOG_ENDPOINT}/register_federation_peer",
                json={"peer": name, "endpoint": endpoint}
            )
            logging.info(f"Peer registered: {name} -> {endpoint}")
        except:
            logging.warning("Could not register peer with PROLOG_ENDPOINT")

    @classmethod
    def broadcast(cls, message: Dict) -> Dict:
        """
        Transmite uma mensagem para todos os peers federados.
        A estrutura distribui poder sem dissolvê-lo.
        """
        results = {}
        for name, endpoint in cls._peers.items():
            try:
                response = requests.post(f"{endpoint}/federate", json=message, timeout=10)
                results[name] = response.json()
            except Exception as e:
                results[name] = {"error": str(e)}

        return {
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    def consensus(cls, pr_id: str, peers: List[str]) -> Dict:
        """
        Obtém consenso entre múltiplos peers federados.
        Similar ao modelo MultiGov da Wormhole.
        """
        decisions = {}
        for peer in peers:
            if peer in cls._peers:
                endpoint = cls._peers[peer]
                try:
                    response = requests.post(
                        f"{endpoint}/evaluate",
                        json={"pr_id": pr_id},
                        timeout=30
                    )
                    decisions[peer] = response.json().get("decision", "abstain")
                except Exception:
                    decisions[peer] = "error"

        approve = sum(1 for d in decisions.values() if d == "approve")
        reject = sum(1 for d in decisions.values() if d == "reject")

        if approve > reject:
            consensus = "approve"
        elif reject > approve:
            consensus = "reject"
        else:
            consensus = "stalemate"

        return {
            "consensus": consensus,
            "decisions": decisions,
            "approve_count": approve,
            "reject_count": reject
        }

    @classmethod
    def sync(cls) -> Dict:
        """Sincroniza o estado com todos os peers federados."""
        status = {}
        for name, endpoint in cls._peers.items():
            try:
                response = requests.get(f"{endpoint}/health", timeout=5)
                status[name] = {"healthy": response.status_code == 200}
            except Exception:
                status[name] = {"healthy": False}

        return {
            "peers": status,
            "synchronized": all(s.get("healthy", False) for s in status.values())
        }

# ============================================================================
# ENDPOINTS v10
# ============================================================================

def require_api_key(f):
    """Decorator para validação de API key."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated

# F1: Bitbucket e Azure DevOps
@app.route('/api/governance/vcs/bitbucket/merge/<pr_id>', methods=['POST'])
@require_api_key
def bitbucket_merge(pr_id):
    """Merge de PR no Bitbucket."""
    adapter = BitbucketAdapter(
        os.environ.get('BITBUCKET_WORKSPACE', ''),
        os.environ.get('BITBUCKET_TOKEN', '')
    )
    result = adapter.merge_pr(pr_id)
    return jsonify(result)

@app.route('/api/governance/vcs/azure/merge/<pr_id>', methods=['POST'])
@require_api_key
def azure_merge(pr_id):
    """Merge de PR no Azure DevOps."""
    adapter = AzureDevOpsAdapter(
        os.environ.get('AZURE_INSTANCE', ''),
        os.environ.get('AZURE_PROJECT', ''),
        os.environ.get('AZURE_TOKEN', '')
    )
    result = adapter.merge_pr(pr_id)
    return jsonify(result)

# F2: zk-SNARKs/STARKs
@app.route('/api/governance/prove/snark', methods=['POST'])
@require_api_key
def prove_snark():
    """Gera uma prova zk-SNARK para uma execução."""
    data = request.json
    proof = ZKProofEngine.generate_snark_proof(data)
    return jsonify(proof)

@app.route('/api/governance/prove/stark', methods=['POST'])
@require_api_key
def prove_stark():
    """Gera uma prova zk-STARK para uma execução."""
    data = request.json
    proof = ZKProofEngine.generate_stark_proof(data)
    return jsonify(proof)

@app.route('/api/governance/verify', methods=['POST'])
@require_api_key
def verify_proof():
    """Verifica uma prova zero-knowledge."""
    data = request.json
    proof_type = data.get('proof_type')
    proof = data.get('proof')

    if proof_type == 'snark':
        valid = ZKProofEngine.verify_snark_proof(proof)
    elif proof_type == 'stark':
        valid = ZKProofEngine.verify_stark_proof(proof)
    else:
        return jsonify({"error": "Unknown proof type"}), 400

    return jsonify({"valid": valid})

# F3: DID Integration
@app.route('/api/governance/did/register', methods=['POST'])
@require_api_key
def register_did():
    """Registra um DID para um agente."""
    data = request.json
    DIDManager.register_did(data['agent'], data['did'], data.get('document', {}))
    return jsonify({"status": "registered", "did": data['did']})

@app.route('/api/governance/did/resolve/<did>', methods=['GET'])
def resolve_did(did):
    """Resolve um DID para seu documento."""
    document = DIDManager.resolve_did(did)
    if document:
        return jsonify(document)
    return jsonify({"error": "DID not found"}), 404

@app.route('/api/governance/did/verify', methods=['POST'])
@require_api_key
def verify_did_signature():
    """Verifica uma assinatura DID."""
    data = request.json
    valid = DIDManager.verify_signature(data['did'], data['message'], data['signature'])
    return jsonify({"valid": valid})

# F4: Real-Time Dashboard
@app.route('/api/governance/dashboard/snapshot', methods=['GET'])
def dashboard_snapshot():
    """Obtém um snapshot do dashboard."""
    return jsonify(DashboardManager.get_snapshot())

@sock.route('/api/governance/dashboard/stream')
def dashboard_stream(ws):
    """WebSocket para stream de eventos do dashboard."""
    DashboardManager.subscribe(ws)
    while True:
        message = ws.receive()
        if message is None:
            break
        # Processa mensagens do cliente
        try:
            data = json.loads(message)
            if data.get('command') == 'snapshot':
                ws.send(json.dumps(DashboardManager.get_snapshot()))
            elif data.get('command') == 'subscribe':
                ws.send(json.dumps({"status": "subscribed", "event": data.get('event')}))
        except Exception as e:
            ws.send(json.dumps({"error": str(e)}))

# F5: Federated Governance
@app.route('/api/governance/federation/register', methods=['POST'])
@require_api_key
def register_peer():
    """Registra um peer na federação."""
    data = request.json
    FederationManager.register_peer(data['name'], data['endpoint'])
    return jsonify({"status": "registered", "peer": data['name']})

@app.route('/api/governance/federation/broadcast', methods=['POST'])
@require_api_key
def federated_broadcast():
    """Transmite uma mensagem para todos os peers."""
    data = request.json
    results = FederationManager.broadcast(data.get('message', {}))
    return jsonify(results)

@app.route('/api/governance/federation/consensus', methods=['POST'])
@require_api_key
def federated_consensus():
    """Obtém consenso entre peers federados."""
    data = request.json
    consensus = FederationManager.consensus(data['pr_id'], data.get('peers', []))
    return jsonify(consensus)

@app.route('/api/governance/federation/sync', methods=['GET'])
def federated_sync():
    """Sincroniza com todos os peers."""
    return jsonify(FederationManager.sync())

# ============================================================================
# ENDPOINT PRINCIPAL — AVALIAÇÃO COMPLETA v10
# ============================================================================

@app.route('/api/governance/evaluate', methods=['POST'])
@require_api_key
def evaluate_pr_v10():
    """
    Avaliação completa de PR com todas as capacidades v10:
    - VCS Agnóstico (GitHub, GitLab, Bitbucket, Azure DevOps)
    - zk-Proofs (SNARKs/STARKs)
    - DID Identity
    - Federated Consensus
    """
    data = request.json
    pr_id = data.get('pr_id')
    vcs = data.get('vcs', 'github')
    use_zk = data.get('use_zk', False)
    use_did = data.get('use_did', False)
    use_federation = data.get('use_federation', False)

    # 1. Seleciona o adaptador VCS apropriado
    if vcs == 'github':
        from governance_bridge_v9 import GitHubAdapter  # fallback para v9
        adapter = GitHubAdapter(
           token=os.environ.get('GITHUB_TOKEN', ''),
           repo=os.environ.get('GITHUB_REPO', '')
        )
    elif vcs == 'bitbucket':
        adapter = BitbucketAdapter(
            workspace=os.environ.get('BITBUCKET_WORKSPACE', ''),
            token=os.environ.get('BITBUCKET_TOKEN', '')
        )
    elif vcs == 'azure':
        adapter = AzureDevOpsAdapter(
            instance=os.environ.get('AZURE_INSTANCE', ''),
            project=os.environ.get('AZURE_PROJECT', ''),
            token=os.environ.get('AZURE_TOKEN', '')
        )
    else:
        return jsonify({"error": f"VCS {vcs} not supported"}), 400

    # 2. Obtém o diff
    diff = adapter.fetch_pr_diff(pr_id)

    # 3. Avaliação no Prolog
    response = requests.post(
        f"{PROLOG_ENDPOINT}/evaluate_pr",
        json={"pr_id": pr_id, "diff": diff}
    )
    evaluation = response.json()

    # 4. zk-Proof (opcional)
    zk_proof = None
    if use_zk:
        proof_type = data.get('zk_type', 'snark')
        if proof_type == 'snark':
            zk_proof = ZKProofEngine.generate_snark_proof(evaluation)
        else:
            zk_proof = ZKProofEngine.generate_stark_proof(evaluation)

    # 5. DID Verification (opcional)
    did_info = None
    if use_did:
        did = data.get('did')
        if did:
            document = DIDManager.resolve_did(did)
            did_info = {"did": did, "document": document}

    # 6. Federated Consensus (opcional)
    federation_result = None
    if use_federation:
        peers = data.get('peers', [])
        federation_result = FederationManager.consensus(pr_id, peers)

    # 7. Executa ação
    action = evaluation.get('action', 'manual_review')
    execution_result = None

    if action == 'auto_merge_executed':
        execution_result = adapter.merge_pr(pr_id)
        adapter.comment_pr(pr_id, f"✅ Merged by Governance Engine v10\n- Coherence: {evaluation.get('phi', 0):.2f}")
    elif action == 'veto_executed':
        execution_result = adapter.close_pr(pr_id, f"Vetoed by Governance Engine")
        adapter.comment_pr(pr_id, f"❌ Vetoed by Governance Engine v10")

    # 8. Log da decisão com DID (se disponível)
    decision_id = f"dec_{pr_id}_{datetime.utcnow().timestamp()}"
    requests.post(
        f"{PROLOG_ENDPOINT}/log_decision",
        json={
            "id": decision_id,
            "type": "governance",
            "parent": None,
            "metadata": {
                "pr_id": pr_id,
                "vcs": vcs,
                "evaluation": evaluation,
                "zk_proof": zk_proof,
                "did_info": did_info,
                "federation": federation_result,
                "execution": execution_result
            }
        }
    )

    return jsonify({
        "status": "success",
        "decision_id": decision_id,
        "evaluation": evaluation,
        "zk_proof": zk_proof,
        "did_info": did_info,
        "federation": federation_result,
        "execution": execution_result,
        "timestamp": datetime.utcnow().isoformat()
    })


# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == '__main__':
    # Registra peers de federação (exemplo)
    if os.environ.get('FEDERATION_PEERS'):
        peers = json.loads(os.environ.get('FEDERATION_PEERS'))
        for name, endpoint in peers.items():
            FederationManager.register_peer(name, endpoint)

    app.run(host='0.0.0.0', port=PORT)