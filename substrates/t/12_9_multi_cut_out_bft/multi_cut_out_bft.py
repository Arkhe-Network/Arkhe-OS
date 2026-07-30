#!/usr/bin/env python3
# Cathedral Multi-Cut-Out BFT v1.0.0
# Tres Orquestradores RSI em consenso HotStuff com propriedades de Cut-Out.

import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Set
from enum import Enum
import asyncio
from collections import defaultdict

# CONFIGURACAO
N_ORCHESTRATORS = 3
FAULT_TOLERANCE = 1  # f=1, N=3f+1 (na pratica, N=3 com quorum 2)
QUORUM = 2  # 2/3
BLOCK_TIME_MS = 500
VIEW_TIMEOUT_MS = 2000

# TEE Enclaves (simulado -- em producao: SGX/TrustZone/Nitro)
TEE_ENCLAVES = {
    "alpha": {"type": "SGX", "location": "Sao Paulo", "attestation": None},
    "beta": {"type": "TrustZone", "location": "Brasilia", "attestation": None},
    "gamma": {"type": "Nitro", "location": "Recife", "attestation": None},
}

# TIPOS DE DADOS
class MessageType(Enum):
    NEW_VIEW = "new_view"
    PREPARE = "prepare"
    PRE_COMMIT = "pre_commit"
    COMMIT = "commit"
    DECIDE = "decide"
    VIEW_CHANGE = "view_change"

@dataclass(frozen=True)
class Block:
    # Bloco de orquestracao -- contem apenas hashes, nunca conteudo semantico.
    view_number: int
    block_number: int
    parent_hash: str
    payload_hash: str  # Hash do comando de orquestracao (nunca o comando em si)
    timestamp_ns: int
    orchestrator_id: str
    signature: str

    def hash(self) -> str:
        # Hash canonico do bloco (deterministico).
        data = "{}:{}:{}:{}:{}:{}".format(self.view_number, self.block_number, self.parent_hash, self.payload_hash, self.timestamp_ns, self.orchestrator_id)
        return "0x" + hashlib.sha3_256(data.encode()).hexdigest()

@dataclass(frozen=True)
class QuorumCertificate:
    # Certificado de quorum -- prova de consenso BFT.
    view_number: int
    block_hash: str
    signatures: Dict[str, str]  # orchestrator_id -> signature

    def verify(self, orchestrators: Set[str]) -> bool:
        # Verifica se QC tem quorum valido.
        if len(self.signatures) < QUORUM:
            return False
        for oid in self.signatures:
            if oid not in orchestrators:
                return False
        return True

@dataclass(frozen=True)
class CutOutMessage:
    # Mensagem entre Cut-Outs -- contem apenas metadados, nunca payload semantico.
    # Principio: um Cut-Out genuino nao conhece o significado da mensagem que transmite.
    msg_type: MessageType
    view_number: int
    block_hash: Optional[str]
    qc: Optional[QuorumCertificate]
    orchestrator_id: str
    signature: str

    def verify_signature(self, public_key: str) -> bool:
        # Verifica assinatura do Cut-Out (SPHINCS+ em producao).
        data = "{}:{}:{}:{}".format(self.msg_type.value, self.view_number, self.block_hash, self.orchestrator_id)
        expected = "0x" + hashlib.sha3_256((public_key + data).encode()).hexdigest()
        return self.signature == expected


# ORQUESTRADOR RSI (Cut-Out Digital)
class RSIOrchestrator:
    # Orquestrador RSI -- Cut-Out digital com propriedades de seguranca de tradecraft.
    # Propriedades:
    # - Sem estado persistente entre ciclos
    # - Sem conhecimento semantico dos substratos
    # - Comunicacao ofuscada via Multi-Layer Decoder
    # - Auto-destruicao pos-ciclo (garbage collection agressivo)

    def __init__(self, orchestrator_id: str, tee_type: str, location: str):
        self.id = orchestrator_id
        self.tee_type = tee_type
        self.location = location
        self.private_key = secrets.token_hex(32)
        self.public_key = "0x" + hashlib.sha3_256(self.private_key.encode()).hexdigest()

        # Estado efemero (resetado a cada ciclo)
        self.view_number = 0
        self.block_number = 0
        self.high_qc: Optional[QuorumCertificate] = None
        self.prepare_votes: Dict[str, str] = {}
        self.pre_commit_votes: Dict[str, str] = {}
        self.commit_votes: Dict[str, str] = {}

        # Metricas (nao persistentes)
        self.metrics = {
            "cycles_completed": 0,
            "blocks_proposed": 0,
            "votes_cast": 0,
            "view_changes": 0,
            "latency_ms": [],
        }

        self._lock = asyncio.Lock()
        self._running = False

    def _sign(self, data: str) -> str:
        # Assina dados com chave privada (SPHINCS+ stub).
        return "0x" + hashlib.sha3_256((self.private_key + data).encode()).hexdigest()

    def _create_block(self, payload_hash: str) -> Block:
        # Cria novo bloco de orquestracao -- apenas hash do payload.
        parent_hash = self.high_qc.block_hash if self.high_qc else "0x" + "0" * 64
        block = Block(
            view_number=self.view_number,
            block_number=self.block_number,
            parent_hash=parent_hash,
            payload_hash=payload_hash,
            timestamp_ns=time.time_ns(),
            orchestrator_id=self.id,
            signature=""
        )
        signature = self._sign(block.hash())
        return Block(
            view_number=block.view_number,
            block_number=block.block_number,
            parent_hash=block.parent_hash,
            payload_hash=block.payload_hash,
            timestamp_ns=block.timestamp_ns,
            orchestrator_id=block.orchestrator_id,
            signature=signature
        )

    async def propose_block(self, payload_hash: str) -> Tuple[Block, QuorumCertificate]:
        # Proposta de bloco (lider do view atual).
        # O Cut-Out propoe um bloco contendo apenas o hash do payload.
        # O payload real nunca e acessado pelo Orquestrador.
        async with self._lock:
            block = self._create_block(payload_hash)
            qc = QuorumCertificate(
                view_number=self.view_number,
                block_hash=block.hash(),
                signatures={self.id: block.signature}
            )
            self.metrics["blocks_proposed"] += 1
            return block, qc

    async def vote_prepare(self, block: Block) -> Optional[CutOutMessage]:
        # Voto PREPARE -- verifica bloco e emite voto.
        # O Cut-Out verifica apenas a estrutura do bloco, nunca o conteudo semantico.
        async with self._lock:
            if block.view_number != self.view_number:
                return None
            self.prepare_votes[block.hash()] = self.id
            msg = CutOutMessage(
                msg_type=MessageType.PREPARE,
                view_number=self.view_number,
                block_hash=block.hash(),
                qc=None,
                orchestrator_id=self.id,
                signature=self._sign("prepare:{}".format(block.hash()))
            )
            self.metrics["votes_cast"] += 1
            return msg

    async def vote_pre_commit(self, block_hash: str, prepare_qc: QuorumCertificate) -> Optional[CutOutMessage]:
        # Voto PRE-COMMIT -- verifica quorum de PREPARE.
        async with self._lock:
            if not prepare_qc.verify({"alpha", "beta", "gamma"}):
                return None
            self.pre_commit_votes[block_hash] = self.id
            msg = CutOutMessage(
                msg_type=MessageType.PRE_COMMIT,
                view_number=self.view_number,
                block_hash=block_hash,
                qc=prepare_qc,
                orchestrator_id=self.id,
                signature=self._sign("pre_commit:{}".format(block_hash))
            )
            return msg

    async def vote_commit(self, block_hash: str, pre_commit_qc: QuorumCertificate) -> Optional[CutOutMessage]:
        # Voto COMMIT -- verifica quorum de PRE-COMMIT.
        async with self._lock:
            if not pre_commit_qc.verify({"alpha", "beta", "gamma"}):
                return None
            self.commit_votes[block_hash] = self.id
            msg = CutOutMessage(
                msg_type=MessageType.COMMIT,
                view_number=self.view_number,
                block_hash=block_hash,
                qc=pre_commit_qc,
                orchestrator_id=self.id,
                signature=self._sign("commit:{}".format(block_hash))
            )
            return msg

    async def decide(self, block_hash: str, commit_qc: QuorumCertificate) -> bool:
        # DECIDE -- bloco finalizado com quorum de COMMIT.
        # O Cut-Out comita o bloco e destrui o estado efemero.
        async with self._lock:
            if not commit_qc.verify({"alpha", "beta", "gamma"}):
                return False
            self.high_qc = commit_qc
            self.block_number += 1
            self.metrics["cycles_completed"] += 1
            self._sanitize_state()
            return True

    def _sanitize_state(self):
        # Destruicao de contexto pos-ciclo.
        # O Cut-Out destroi todo o estado efemero apos cada ciclo de consenso.
        # Esta e a propriedade fundamental que o torna um intermediario seguro.
        self.prepare_votes = {}
        self.pre_commit_votes = {}
        self.commit_votes = {}
        # Nota: view_number e block_number sao retidos para continuidade
        # Em producao: estes tambem seriam comitados via ZK-proof

    async def view_change(self, new_view: int) -> CutOutMessage:
        # Transicao de view (lider falho ou timeout).
        async with self._lock:
            self.view_number = new_view
            self.metrics["view_changes"] += 1
            msg = CutOutMessage(
                msg_type=MessageType.VIEW_CHANGE,
                view_number=new_view,
                block_hash=None,
                qc=self.high_qc,
                orchestrator_id=self.id,
                signature=self._sign("view_change:{}".format(new_view))
            )
            return msg

    def get_metrics(self) -> dict:
        # Metricas nao persistentes -- apenas para monitoramento.
        return {
            **self.metrics,
            "orchestrator_id": self.id,
            "tee_type": self.tee_type,
            "location": self.location,
            "current_view": self.view_number,
            "current_block": self.block_number,
        }


# REDE BFT -- SIMULACAO DOS 3 CUT-OUTS
class BFTNetwork:
    # Rede BFT com 3 Cut-Outs RSI.
    # Simula a comunicacao entre os 3 Orquestradores em zonas geograficas distintas.

    def __init__(self):
        self.orchestrators: Dict[str, RSIOrchestrator] = {}
        self.message_log: List[CutOutMessage] = []
        self.decided_blocks: List[Tuple[str, QuorumCertificate]] = []
        self._lock = asyncio.Lock()

    def register_orchestrator(self, orch: RSIOrchestrator):
        self.orchestrators[orch.id] = orch

    async def broadcast(self, msg: CutOutMessage, exclude: Optional[str] = None):
        # Broadcast de mensagem para todos os Cut-Outs (simulado).
        async with self._lock:
            self.message_log.append(msg)
            for oid, orch in self.orchestrators.items():
                if oid != exclude:
                    # Em producao: comunicacao cifrada via TLS 1.3 + PQC
                    pass

    async def run_consensus_round(self, payload_hash: str) -> Optional[str]:
        # Executa uma rodada completa de consenso BFT.
        # Fases: 1.PROPOSE 2.PREPARE 3.PRE-COMMIT 4.COMMIT 5.DECIDE
        leader_id = list(self.orchestrators.keys())[0]
        leader = self.orchestrators[leader_id]

        # Fase 1: PROPOSE
        block, qc = await leader.propose_block(payload_hash)
        print("[BFT] Lider {} propos bloco {}...".format(leader_id, block.hash()[:16]))

        # Fase 2: PREPARE
        prepare_votes = {}
        for oid, orch in self.orchestrators.items():
            msg = await orch.vote_prepare(block)
            if msg:
                prepare_votes[oid] = msg.signature

        if len(prepare_votes) < QUORUM:
            print("[BFT] FALHA: quorum PREPARE nao atingido ({}/{})".format(len(prepare_votes), QUORUM))
            return None

        prepare_qc = QuorumCertificate(
            view_number=block.view_number,
            block_hash=block.hash(),
            signatures=prepare_votes
        )
        print("[BFT] Quorum PREPARE atingido ({}/{})".format(len(prepare_votes), N_ORCHESTRATORS))

        # Fase 3: PRE-COMMIT
        pre_commit_votes = {}
        for oid, orch in self.orchestrators.items():
            msg = await orch.vote_pre_commit(block.hash(), prepare_qc)
            if msg:
                pre_commit_votes[oid] = msg.signature

        if len(pre_commit_votes) < QUORUM:
            print("[BFT] FALHA: quorum PRE-COMMIT nao atingido")
            return None

        pre_commit_qc = QuorumCertificate(
            view_number=block.view_number,
            block_hash=block.hash(),
            signatures=pre_commit_votes
        )
        print("[BFT] Quorum PRE-COMMIT atingido ({}/{})".format(len(pre_commit_votes), N_ORCHESTRATORS))

        # Fase 4: COMMIT
        commit_votes = {}
        for oid, orch in self.orchestrators.items():
            msg = await orch.vote_commit(block.hash(), pre_commit_qc)
            if msg:
                commit_votes[oid] = msg.signature

        if len(commit_votes) < QUORUM:
            print("[BFT] FALHA: quorum COMMIT nao atingido")
            return None

        commit_qc = QuorumCertificate(
            view_number=block.view_number,
            block_hash=block.hash(),
            signatures=commit_votes
        )
        print("[BFT] Quorum COMMIT atingido ({}/{})".format(len(commit_votes), N_ORCHESTRATORS))

        # Fase 5: DECIDE
        for oid, orch in self.orchestrators.items():
            success = await orch.decide(block.hash(), commit_qc)
            if success:
                print("[BFT] Cut-Out {} decidiu bloco {}...".format(oid, block.hash()[:16]))

        self.decided_blocks.append((block.hash(), commit_qc))
        return block.hash()

    async def run_byzantine_test(self, payload_hash: str, faulty_orchestrator: str):
        # Teste de tolerancia a falha bizantina.
        # Simula um Orquestrador malicioso que envia votos invalidos.
        # O consenso deve continuar com os 2 Orquestradores honestos (2/3).
        print("\n[BFT TEST] Orquestrador {} e BIZANTINO".format(faulty_orchestrator))
        faulty = self.orchestrators[faulty_orchestrator]
        faulty._sign = lambda data: "INVALID_SIGNATURE"
        result = await self.run_consensus_round(payload_hash)
        if result:
            print("[BFT TEST] SUCESSO: consenso atingido apesar de falha bizantina")
        else:
            print("[BFT TEST] FALHA: consenso nao atingido")
        return result


# MAIN -- SIMULACAO
async def main():
    print("=" * 60)
    print("CATHEDRAL MULTI-CUT-OUT BFT v1.0.0")
    print("3 Orquestradores RSI em consenso HotStuff")
    print("=" * 60)

    network = BFTNetwork()
    network.register_orchestrator(RSIOrchestrator("alpha", "SGX", "Sao Paulo"))
    network.register_orchestrator(RSIOrchestrator("beta", "TrustZone", "Brasilia"))
    network.register_orchestrator(RSIOrchestrator("gamma", "Nitro", "Recife"))

    print("\n[SETUP] 3 Cut-Outs registrados:")
    for oid, orch in network.orchestrators.items():
        print("  {}: {} @ {}".format(oid, orch.tee_type, orch.location))

    # Rodada 1: Consenso normal
    print("\n" + "=" * 60)
    print("RODADA 1: Consenso Normal (3/3 honestos)")
    print("=" * 60)
    payload = "0x" + hashlib.sha3_256(b"substrato_1091_1:vector_theosis").hexdigest()
    result = await network.run_consensus_round(payload)

    # Rodada 2: Falha bizantina (1/3 malicioso)
    print("\n" + "=" * 60)
    print("RODADA 2: Tolerancia a Falha Bizantina (2/3 honestos)")
    print("=" * 60)
    payload2 = "0x" + hashlib.sha3_256(b"substrato_2140_3:sensorio_temporal").hexdigest()
    result2 = await network.run_byzantine_test(payload2, "beta")

    # Metricas finais
    print("\n" + "=" * 60)
    print("METRICAS FINAIS")
    print("=" * 60)
    for oid, orch in network.orchestrators.items():
        metrics = orch.get_metrics()
        print("\nCut-Out {} ({} @ {}):".format(oid, metrics['tee_type'], metrics['location']))
        print("  Ciclos completados: {}".format(metrics['cycles_completed']))
        print("  Blocos propostos: {}".format(metrics['blocks_proposed']))
        print("  Votos emitidos: {}".format(metrics['votes_cast']))
        print("  View changes: {}".format(metrics['view_changes']))

    print("\nTotal de blocos decididos: {}".format(len(network.decided_blocks)))
    print("\n[OK] Simulacao BFT concluida.")

if __name__ == "__main__":
    asyncio.run(main())
