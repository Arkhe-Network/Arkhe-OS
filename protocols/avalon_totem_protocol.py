#!/usr/bin/env python3
"""
AVALON TOTEM PROTOCOL — HumbleTurn Integration
Selo: AVALON-TOTEM-v1.0-2026-08-17

O HumbleTurn Totem é um protocolo de comunicação que codifica
a ordem termodinâmica correta para diálogos produtivos:
    P (Present) → C (Clarify) → E (Empathize) → F (Feedback)

Integração com o ecossistema Avalon:
- ARKHE Hypergraph: cada modo é um nó com evidência atestada
- Comunicação Avalon: protocolo padronizado para interações humano-IA
- Sessões colaborativas: modo T (Teach) para contextos educacionais
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Literal, Union
from datetime import datetime

# =============================================================================
# 1. TOTEM MODES
# =============================================================================

class TotemMode(Enum):
    """Os quatro modos fundamentais do HumbleTurn Totem."""
    REST = "REST"          # Estado neutro, à escuta
    PRESENT = "P"          # Compartilhar perspectiva
    CLARIFY = "C"          # Fazer perguntas para esclarecer
    EMPATHIZE = "E"        # Refletir compreensão
    FEEDBACK = "F"         # Responder construtivamente
    TEACH = "T"            # Ensinar / compartilhar conhecimento (extensão v1.0)

    @property
    def is_active(self) -> bool:
        """Retorna True se o modo não for REST."""
        return self != TotemMode.REST

    @property
    def priority(self) -> int:
        """Prioridade do modo (quanto menor, maior prioridade)."""
        priorities = {
            TotemMode.REST: 99,
            TotemMode.PRESENT: 10,
            TotemMode.CLARIFY: 1,      # Máxima prioridade
            TotemMode.EMPATHIZE: 5,
            TotemMode.FEEDBACK: 8,
            TotemMode.TEACH: 3,
        }
        return priorities.get(self, 50)

    def next_state(self, event: str) -> "TotemMode":
        """Transição de estado baseada no evento."""
        transitions = {
            ("REST", "request_floor"): TotemMode.PRESENT,
            ("REST", "teach"): TotemMode.TEACH,
            ("P", "request_clarity"): TotemMode.CLARIFY,
            ("P", "request_reflection"): TotemMode.EMPATHIZE,
            ("P", "request_response"): TotemMode.FEEDBACK,
            ("P", "teach"): TotemMode.TEACH,
            ("C", "understood"): TotemMode.PRESENT,
            ("C", "reflecting"): TotemMode.EMPATHIZE,
            ("E", "confirmed"): TotemMode.FEEDBACK,
            ("E", "still_confused"): TotemMode.CLARIFY,
            ("F", "done"): TotemMode.REST,
            ("F", "new_perspective"): TotemMode.PRESENT,
            ("T", "done"): TotemMode.REST,
            ("T", "need_clarity"): TotemMode.CLARIFY,
        }
        return transitions.get((self.value, event), self)

    @classmethod
    def from_letter(cls, letter: str) -> "TotemMode":
        """Converte uma letra (P, C, E, F, T) para o modo correspondente."""
        mapping = {
            "P": cls.PRESENT,
            "C": cls.CLARIFY,
            "E": cls.EMPATHIZE,
            "F": cls.FEEDBACK,
            "T": cls.TEACH,
            "REST": cls.REST,
        }
        return mapping.get(letter.upper(), cls.REST)

    def to_letter(self) -> str:
        """Retorna a letra correspondente ao modo."""
        return self.value


# =============================================================================
# 2. TOTEM NODE — Evidência no ARKHE Hypergraph
# =============================================================================

@dataclass
class TotemNode:
    """Nó do ARKHE Hypergraph representando um passo do protocolo totem."""
    mode: TotemMode
    speaker_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _content_hash: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        if self._content_hash is None:
            self._content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """SHA3-256 do conteúdo canónico para integridade."""
        payload = json.dumps({
            'mode': self.mode.value,
            'speaker_id': self.speaker_id,
            'content': self.content,
            'timestamp': self.timestamp,
            'parent_id': self.parent_id,
        }, sort_keys=True)
        return hashlib.sha3_256(payload.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para serialização."""
        return {
            'mode': self.mode.value,
            'speaker_id': self.speaker_id,
            'content': self.content,
            'timestamp': self.timestamp,
            'parent_id': self.parent_id,
            'content_hash': self._content_hash,
            'metadata': self.metadata,
        }

    def to_arkhe_node(self) -> Dict[str, Any]:
        """Converte para o formato de nó do ARKHE Hypergraph."""
        return {
            '@type': 'TotemStep',
            'id': f"totem-{self._content_hash[:16]}",
            'mode': self.mode.value,
            'speaker': self.speaker_id,
            'content': self.content,
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
            'parent': self.parent_id,
            'evidence_hash': self._content_hash,
            'provenance': {
                'protocol': 'HumbleTurnTotem',
                'version': '1.0',
                'context': self.metadata.get('context', 'conversation'),
            }
        }


# =============================================================================
# 3. TOTEM SESSION — Gerenciamento de Sessões Colaborativas
# =============================================================================

@dataclass
class TotemSession:
    """Sessão colaborativa usando o protocolo totem."""
    session_id: str
    participants: List[str]
    current_mode: TotemMode = TotemMode.REST
    current_speaker: Optional[str] = None
    history: List[TotemNode] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def request_floor(self, speaker: str, content: str) -> TotemNode:
        """Pede a palavra (transição para PRESENT)."""
        if speaker not in self.participants:
            raise ValueError(f"Speaker {speaker} not in session")

        node = TotemNode(
            mode=TotemMode.PRESENT,
            speaker_id=speaker,
            content=content,
            parent_id=self.history[-1]._content_hash if self.history else None,
            metadata={'session_id': self.session_id},
        )
        self.current_mode = TotemMode.PRESENT
        self.current_speaker = speaker
        self.history.append(node)
        return node

    def clarify(self, speaker: str, question: str) -> TotemNode:
        """Faz uma pergunta para clarificar (transição para CLARIFY)."""
        if speaker not in self.participants:
            raise ValueError(f"Speaker {speaker} not in session")

        node = TotemNode(
            mode=TotemMode.CLARIFY,
            speaker_id=speaker,
            content=question,
            parent_id=self.history[-1]._content_hash if self.history else None,
            metadata={'session_id': self.session_id},
        )
        self.current_mode = TotemMode.CLARIFY
        self.current_speaker = speaker
        self.history.append(node)
        return node

    def empathize(self, speaker: str, reflection: str) -> TotemNode:
        """Reflete a compreensão (transição para EMPATHIZE)."""
        if speaker not in self.participants:
            raise ValueError(f"Speaker {speaker} not in session")

        node = TotemNode(
            mode=TotemMode.EMPATHIZE,
            speaker_id=speaker,
            content=reflection,
            parent_id=self.history[-1]._content_hash if self.history else None,
            metadata={'session_id': self.session_id},
        )
        self.current_mode = TotemMode.EMPATHIZE
        self.current_speaker = speaker
        self.history.append(node)
        return node

    def feedback(self, speaker: str, response: str) -> TotemNode:
        """Oferece feedback construtivo (transição para FEEDBACK)."""
        if speaker not in self.participants:
            raise ValueError(f"Speaker {speaker} not in session")

        node = TotemNode(
            mode=TotemMode.FEEDBACK,
            speaker_id=speaker,
            content=response,
            parent_id=self.history[-1]._content_hash if self.history else None,
            metadata={'session_id': self.session_id},
        )
        self.current_mode = TotemMode.FEEDBACK
        self.current_speaker = speaker
        self.history.append(node)
        return node

    def teach(self, speaker: str, lesson: str) -> TotemNode:
        """Compartilha conhecimento (modo TEACH)."""
        if speaker not in self.participants:
            raise ValueError(f"Speaker {speaker} not in session")

        node = TotemNode(
            mode=TotemMode.TEACH,
            speaker_id=speaker,
            content=lesson,
            parent_id=self.history[-1]._content_hash if self.history else None,
            metadata={'session_id': self.session_id},
        )
        self.current_mode = TotemMode.TEACH
        self.current_speaker = speaker
        self.history.append(node)
        return node

    def rest(self) -> None:
        """Retorna ao estado de escuta (REST)."""
        self.current_mode = TotemMode.REST
        self.current_speaker = None

    def get_current_state(self) -> Dict[str, Any]:
        """Retorna o estado atual da sessão."""
        return {
            'session_id': self.session_id,
            'mode': self.current_mode.value,
            'speaker': self.current_speaker,
            'history_length': len(self.history),
            'participants': self.participants,
            'created_at': self.created_at,
        }

    def get_history_as_arkhe(self) -> List[Dict[str, Any]]:
        """Retorna todo o histórico como nós ARKHE."""
        return [node.to_arkhe_node() for node in self.history]

    def get_summary(self) -> Dict[str, Any]:
        """Gera um resumo da sessão."""
        modes = [h.mode.value for h in self.history]
        counts = {m: modes.count(m) for m in set(modes)}
        return {
            'session_id': self.session_id,
            'total_turns': len(self.history),
            'mode_counts': counts,
            'participants': self.participants,
            'duration_seconds': time.time() - self.created_at,
            'current_mode': self.current_mode.value,
            'current_speaker': self.current_speaker,
        }


# =============================================================================
# 4. TOTEM ORCHESTRATOR — Integração com ARKHE Hypergraph
# =============================================================================

class TotemOrchestrator:
    """
    Orquestrador do protocolo totem, integrado ao ARKHE Hypergraph.
    """

    def __init__(self, arkhe_api_url: Optional[str] = None):
        self.arkhe_api_url = arkhe_api_url
        self.sessions: Dict[str, TotemSession] = {}
        self._submitted_nodes: List[Dict[str, Any]] = []

    def create_session(self, participants: List[str]) -> TotemSession:
        """Cria uma nova sessão colaborativa."""
        session_id = f"totem-{hashlib.sha3_256(str(participants).encode()).hexdigest()[:8]}"
        session = TotemSession(
            session_id=session_id,
            participants=participants,
        )
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[TotemSession]:
        """Obtém uma sessão pelo ID."""
        return self.sessions.get(session_id)

    def submit_to_arkhe(self, node: TotemNode) -> Dict[str, Any]:
        """Submete um nó totem ao ARKHE Hypergraph."""
        arkhe_node = node.to_arkhe_node()
        self._submitted_nodes.append(arkhe_node)
        return {
            'submitted': True,
            'node_id': arkhe_node['id'],
            'evidence_hash': arkhe_node['evidence_hash'],
            'arkhe_node': arkhe_node,
        }

    def submit_session(self, session: TotemSession) -> List[Dict[str, Any]]:
        """Submete toda uma sessão ao ARKHE Hypergraph."""
        results = []
        for node in session.history:
            results.append(self.submit_to_arkhe(node))
        return results

    def get_arkhe_history(self, session: TotemSession) -> List[Dict[str, Any]]:
        """Obtém o histórico da sessão no formato ARKHE."""
        return session.get_history_as_arkhe()

    def analyze_session(self, session: TotemSession) -> Dict[str, Any]:
        """Analisa a dinâmica da sessão."""
        summary = session.get_summary()
        modes = [h.mode.value for h in session.history]
        transitions = []
        for i in range(1, len(modes)):
            transitions.append(f"{modes[i-1]} → {modes[i]}")

        return {
            **summary,
            'transitions': transitions,
            'transition_count': len(transitions),
            'most_common_transition': max(set(transitions), key=transitions.count) if transitions else None,
        }


# =============================================================================
# 5. TOTEM PROMPT TEMPLATES — Para uso em sessões humano-IA
# =============================================================================

TOTEM_PROMPT_TEMPLATES = {
    "P": """
[PRESENT] I'd like to share a perspective:
{content}

What I'm seeing is...
What I'm thinking is...
What I'm wondering about is...
""",
    "C": """
[CLARIFY] I need to understand better:
{content}

Could you elaborate on...
What do you mean by...
How does that relate to...
""",
    "E": """
[EMPATHIZE] Let me reflect what I'm hearing:
{content}

It sounds like you're saying...
What I'm understanding is...
The key point I'm picking up on is...
""",
    "F": """
[FEEDBACK] Here's my constructive response:
{content}

Building on what you've shared...
A perspective to consider is...
I'd like to suggest...
""",
    "T": """
[TEACH] Let me share what I know:
{content}

A useful framework for this is...
The key concepts here are...
What's important to understand is...
""",
}

def format_totem_prompt(mode: TotemMode, content: str) -> str:
    """Formata o conteúdo no template do modo correspondente."""
    template = TOTEM_PROMPT_TEMPLATES.get(mode.value, "{content}")
    return template.format(content=content)


# =============================================================================
# 6. TOTEM DECORATOR — Para funções que participam do protocolo
# =============================================================================

def totem_aware(func):
    """
    Decorator que torna uma função consciente do protocolo totem.
    Adiciona os argumentos 'mode' e 'totem_session' à função.
    """
    def wrapper(*args, mode: TotemMode = TotemMode.PRESENT, session: Optional[TotemSession] = None, **kwargs):
        if session:
            # Registra a invocação como um passo totem
            node = TotemNode(
                mode=mode,
                speaker_id="AI_Agent",
                content=f"Function call: {func.__name__}",
                metadata={'args': args, 'kwargs': kwargs},
            )
            session.history.append(node)
        return func(*args, **kwargs)
    return wrapper


# =============================================================================
# 7. TESTES DE PROPRIEDADE
# =============================================================================

def test_totem_protocol():
    """Testa o protocolo totem com uma sessão de exemplo."""
    print("🔱 TOTEM PROTOCOL — SELF-TEST")
    print("=" * 50)

    # 1. Criar sessão
    session = TotemSession(
        session_id="test-001",
        participants=["Alice", "Bob", "AI_Agent"],
    )
    print("✅ 1. Sessão criada")

    # 2. Alice apresenta
    node1 = session.request_floor("Alice", "I believe we should focus on energy efficiency.")
    assert node1.mode == TotemMode.PRESENT
    print("✅ 2. Alice apresentou")

    # 3. Bob clarifica
    node2 = session.clarify("Bob", "What do you mean by 'energy efficiency' in this context?")
    assert node2.mode == TotemMode.CLARIFY
    print("✅ 3. Bob clarificou")

    # 4. Alice empatiza
    node3 = session.empathize("Alice", "I hear you asking about the definition. Let me clarify.")
    assert node3.mode == TotemMode.EMPATHIZE
    print("✅ 4. Alice empatizou")

    # 5. IA oferece feedback
    node4 = session.feedback("AI_Agent", "Based on your exchange, I recommend optimizing the power curve.")
    assert node4.mode == TotemMode.FEEDBACK
    print("✅ 5. IA ofereceu feedback")

    # 6. Retornar ao estado de escuta
    session.rest()
    assert session.current_mode == TotemMode.REST
    print("✅ 6. Retornou ao estado REST")

    # 7. Modo TEACH
    node5 = session.teach("AI_Agent", "Energy efficiency in this context means minimizing entropy production.")
    assert node5.mode == TotemMode.TEACH
    print("✅ 7. Modo TEACH ativado")

    # 8. Verificar histórico
    assert len(session.history) == 5
    print(f"✅ 8. Histórico: {len(session.history)} passos")

    # 9. Transições
    transitions = [f"{session.history[i].mode.value}→{session.history[i+1].mode.value}"
                   for i in range(len(session.history)-1)]
    print(f"✅ 9. Transições: {' → '.join(transitions)}")

    # 10. ARKHE export
    arkhe_nodes = session.get_history_as_arkhe()
    assert len(arkhe_nodes) == 5
    for node in arkhe_nodes:
        assert 'evidence_hash' in node
    print("✅ 10. Exportação ARKHE OK")

    print("\n✅ Todos os testes passaram.")


# =============================================================================
# 8. EXEMPLO DE USO — SESSÃO COLABORATIVA
# =============================================================================

def demo_totem_session():
    """Demonstra uma sessão colaborativa completa."""
    print("\n🔱 TOTEM PROTOCOL — DEMONSTRAÇÃO")
    print("=" * 50)

    # 1. Criar sessão
    orchestrator = TotemOrchestrator()
    session = orchestrator.create_session(["Alice", "Bob", "AI_Agent"])
    print(f"📋 Sessão criada: {session.session_id}")
    print(f"   Participantes: {', '.join(session.participants)}")
    print()

    # 2. Ciclo completo
    steps = [
        ("Alice", TotemMode.PRESENT, "We need to optimize the DLCMD power curve."),
        ("Bob", TotemMode.CLARIFY, "What's the current power consumption baseline?"),
        ("Alice", TotemMode.EMPATHIZE, "I understand you're asking about baseline. It's 50W nominal."),
        ("Bob", TotemMode.FEEDBACK, "Based on that, we could reduce to 45W with PID tuning."),
        ("AI_Agent", TotemMode.TEACH, "The optimal PID parameters for this system are: Kp=1.2, Ki=0.8, Kd=0.3."),
        ("Alice", TotemMode.FEEDBACK, "Great suggestion! Let's implement that."),
    ]

    for speaker, mode, content in steps:
        if mode == TotemMode.PRESENT:
            node = session.request_floor(speaker, content)
        elif mode == TotemMode.CLARIFY:
            node = session.clarify(speaker, content)
        elif mode == TotemMode.EMPATHIZE:
            node = session.empathize(speaker, content)
        elif mode == TotemMode.FEEDBACK:
            node = session.feedback(speaker, content)
        elif mode == TotemMode.TEACH:
            node = session.teach(speaker, content)
        print(f"  {mode.value}: {speaker[:15]:15} → {content[:40]}...")

    # 3. Resumo
    print("\n📊 RESUMO DA SESSÃO:")
    summary = session.get_summary()
    print(f"   Total de passos: {summary['total_turns']}")
    print(f"   Modos usados: {summary['mode_counts']}")
    print(f"   Duração: {summary['duration_seconds']:.1f}s")

    # 4. Exportar para ARKHE
    print("\n📤 Exportação para ARKHE:")
    arkhe_nodes = orchestrator.get_arkhe_history(session)
    for node in arkhe_nodes:
        print(f"   {node['mode']:4} | {node['speaker']:12} | {node['content'][:30]}... | hash={node['evidence_hash'][:12]}...")


# =============================================================================
# 9. MODO T (TEACH) — EXTENSÃO EDUCACIONAL
# =============================================================================

class TeachModeExtensions:
    """
    Extensões para o modo TEACH, incluindo avaliação e estruturação.
    """

    @staticmethod
    def structure_lesson(topic: str, level: str = "beginner") -> Dict[str, Any]:
        """Estrutura uma lição no formato TEACH."""
        return {
            'topic': topic,
            'level': level,
            'key_concepts': [],
            'prerequisites': [],
            'learning_objectives': [],
            'assessment_questions': [],
        }

    @staticmethod
    def add_assessment(topic: str, questions: List[str]) -> Dict[str, Any]:
        """Adiciona perguntas de avaliação a uma lição."""
        return {
            'topic': topic,
            'assessment_questions': questions,
        }

    @staticmethod
    def totem_teach_prompt(lesson: Dict[str, Any]) -> str:
        """Gera um prompt TEACH estruturado."""
        template = """
[T] I'd like to teach about {topic} (level: {level})

Key Concepts:
{key_concepts}

Prerequisites:
{prerequisites}

Learning Objectives:
{objectives}

Assessment Questions:
{questions}
"""
        return template.format(
            topic=lesson.get('topic', ''),
            level=lesson.get('level', ''),
            key_concepts='\n'.join(f'  • {c}' for c in lesson.get('key_concepts', [])),
            prerequisites='\n'.join(f'  • {p}' for p in lesson.get('prerequisites', [])),
            objectives='\n'.join(f'  • {o}' for o in lesson.get('learning_objectives', [])),
            questions='\n'.join(f'  • {q}' for q in lesson.get('assessment_questions', [])),
        )


# =============================================================================
# 10. EXECUÇÃO PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    test_totem_protocol()
    demo_totem_session()

    print("\n🔱 AVALON TOTEM PROTOCOL — INTEGRADO COM SUCESSO")
    print("   Modos: P (Present) | C (Clarify) | E (Empathize) | F (Feedback) | T (Teach)")
    print("   Selo: AVALON-TOTEM-v1.0-2026-08-17")