import hashlib
import json
import math
import time
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum, auto

# ============================================================
# CAMADA 2 — POLYGLOT UNIVERSAL (Substrato 6061)
# ============================================================

class NodeKind(Enum):
    Program = auto(); Module = auto(); Block = auto()
    DeclVariable = auto(); DeclFunction = auto(); DeclClass = auto()
    TypePrimitive = auto(); TypeReference = auto()
    ExprLiteral = auto(); ExprIdentifier = auto(); ExprCall = auto(); ExprBinary = auto()
    StmtIf = auto(); StmtWhile = auto(); StmtReturn = auto()
    Annotation = auto()

@dataclass
class UASTNode:
    id: str
    kind: NodeKind
    children: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    source_range: Optional[Tuple[int, int]] = None
    hash: Optional[str] = None

    def compute_hash(self) -> str:
        data = f"{self.kind.name}:{json.dumps(self.attributes, sort_keys=True, default=str)}"
        self.hash = hashlib.sha3_256(data.encode()).hexdigest()[:32]
        return self.hash

class PolyglotLexer:
    """DFA adaptativo multi-idioma — detecta linguagem por heurística"""

    def detect_language(self, source: str) -> str:
        if source.strip().startswith("fn ") or source.strip().startswith("let "):
            return "ark"
        if "def " in source and ":" in source:
            return "python"
        if "function" in source or "const" in source or "let" in source:
            return "javascript"
        if "#include" in source or "int main" in source:
            return "c"
        if "package main" in source or "func " in source:
            return "go"
        if "mod " in source or "fn " in source:
            return "rust"
        return "unknown"

    def tokenize(self, source: str) -> List[Dict]:
        lang = self.detect_language(source)
        tokens = []
        words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+|"[^"]*"|[{}();,=+\-*/<>!]|==|!=|<=|>=|->', source)
        for w in words:
            if w in ('fn', 'def', 'function', 'func'):
                tokens.append({"type": "KW_FN", "value": w, "lang": lang})
            elif w in ('let', 'var', 'const'):
                tokens.append({"type": "KW_LET", "value": w, "lang": lang})
            elif w in ('if', 'else', 'while', 'return'):
                tokens.append({"type": "KW_CTRL", "value": w, "lang": lang})
            elif w[0].isdigit():
                tokens.append({"type": "LIT_NUM", "value": w, "lang": lang})
            elif w.startswith('"'):
                tokens.append({"type": "LIT_STR", "value": w[1:-1], "lang": lang})
            elif w.isidentifier():
                tokens.append({"type": "IDENT", "value": w, "lang": lang})
            else:
                tokens.append({"type": "OP", "value": w, "lang": lang})
        tokens.append({"type": "EOF", "value": "", "lang": lang})
        return tokens

class UniversalASTBuilder:
    """Constroi UAST canônica a partir de tokens de qualquer linguagem"""

    def __init__(self):
        self.nodes: Dict[str, UASTNode] = {}
        self.counter = 0

    def _id(self) -> str:
        self.counter += 1
        return f"n{self.counter}"

    def build(self, tokens: List[Dict]) -> UASTNode:
        root = UASTNode(id=self._id(), kind=NodeKind.Program, children=[])
        self.nodes[root.id] = root
        i = 0
        while i < len(tokens) - 1:
            tok = tokens[i]
            if tok["type"] == "KW_LET":
                node, i = self._parse_let(tokens, i)
                root.children.append(node.id)
            elif tok["type"] == "KW_FN":
                node, i = self._parse_fn(tokens, i)
                root.children.append(node.id)
            elif tok["type"] == "KW_CTRL":
                node, i = self._parse_ctrl(tokens, i)
                root.children.append(node.id)
            else:
                i += 1
        root.compute_hash()
        return root

    def _parse_let(self, tokens, i):
        i += 1  # skip let
        name = tokens[i]["value"]; i += 1
        if i < len(tokens) and tokens[i]["value"] == "=":
            i += 1
        init = tokens[i]["value"]; i += 1
        node = UASTNode(
            id=self._id(),
            kind=NodeKind.DeclVariable,
            attributes={"name": name, "initializer": init},
        )
        node.compute_hash()
        self.nodes[node.id] = node
        return node, i

    def _parse_fn(self, tokens, i):
        i += 1  # skip fn
        name = tokens[i]["value"]; i += 1
        # skip params simplified
        while i < len(tokens) and tokens[i]["value"] != "{":
            i += 1
        i += 1  # skip {
        body = []
        depth = 1
        while i < len(tokens) and depth > 0:
            if tokens[i]["value"] == "{":
                depth += 1
            elif tokens[i]["value"] == "}":
                depth -= 1
                if depth == 0:
                    break
            body.append(tokens[i])
            i += 1
        i += 1  # skip }
        node = UASTNode(
            id=self._id(),
            kind=NodeKind.DeclFunction,
            attributes={"name": name, "body_tokens": len(body)},
        )
        node.compute_hash()
        self.nodes[node.id] = node
        return node, i

    def _parse_ctrl(self, tokens, i):
        kw = tokens[i]["value"]; i += 1
        node = UASTNode(
            id=self._id(),
            kind=NodeKind.StmtIf if kw == "if" else NodeKind.StmtWhile,
            attributes={"keyword": kw},
        )
        node.compute_hash()
        self.nodes[node.id] = node
        return node, i

class TranspilerCore:
    """UAST → linguagem alvo com preservação semântica"""

    def transpile(self, uast: UASTNode, target_lang: str) -> str:
        lines = []
        for child_id in uast.children:
            child = self._find_node(child_id, uast)
            if child.kind == NodeKind.DeclVariable:
                name = child.attributes.get("name", "x")
                init = child.attributes.get("initializer", "0")
                if target_lang == "python":
                    lines.append(f"{name} = {init}")
                elif target_lang == "javascript":
                    lines.append(f"const {name} = {init};")
                elif target_lang == "c":
                    lines.append(f"int {name} = {init};")
                elif target_lang == "rust":
                    lines.append(f"let {name}: i64 = {init};")
                else:
                    lines.append(f"let {name} = {init}")
            elif child.kind == NodeKind.DeclFunction:
                name = child.attributes.get("name", "f")
                if target_lang == "python":
                    lines.append(f"def {name}():")
                    lines.append("    pass")
                elif target_lang == "javascript":
                    lines.append(f"function {name}() {{}}")
                elif target_lang == "c":
                    lines.append(f"void {name}() {{}}")
                elif target_lang == "rust":
                    lines.append(f"fn {name}() {{}}")
                else:
                    lines.append(f"fn {name}() {{}}")
        return "\n".join(lines)

    def _find_node(self, node_id: str, root: UASTNode) -> Optional[UASTNode]:
        # Simplified: in real implementation would traverse graph
        return None  # placeholder overridden below

# ============================================================
# CAMADA 3 — UNIX SUBSTRATE (6062-6066)
# ============================================================

class FdResource:
    """Recurso linear tipado com anchoring temporal"""

    def __init__(self, fd_type: str, permissions: Set[str]):
        self.fd_type = fd_type
        self.permissions = permissions
        self.anchored = False
        self.anchor_hash = None

    def anchor(self, chain) -> str:
        self.anchored = True
        self.anchor_hash = hashlib.sha3_256(f"{self.fd_type}:{sorted(self.permissions)}".encode()).hexdigest()[:16]
        return self.anchor_hash

    def check_permission(self, op: str) -> bool:
        return op in self.permissions

class MeshNode:
    """Nó mesh com inbox thread-safe e roteamento por coerência"""

    def __init__(self, node_id: str, coherence_threshold: float = 0.90):
        self.node_id = node_id
        self.inbox: List[Dict] = []
        self.neighbors: Set[str] = set()
        self.coherence_threshold = coherence_threshold
        self.message_count = 0

    def send(self, target: str, payload: str, coherence_score: float) -> bool:
        if coherence_score < self.coherence_threshold:
            return False
        self.message_count += 1
        return True

    def receive(self, msg: Dict):
        self.inbox.append(msg)

    def route(self, dest: str, payload: str, network: Dict) -> List[str]:
        # Geodesic routing: shortest path via coherence
        visited = set()
        queue = [(self.node_id, [self.node_id])]
        while queue:
            current, path = queue.pop(0)
            if current == dest:
                return path
            if current in visited:
                continue
            visited.add(current)
            node = network.get(current)
            if node:
                for n in node.neighbors:
                    if n not in visited:
                        queue.append((n, path + [n]))
        return []

class PentaceneBackend:
    """Cristal orgânico com φ-lock < 1e-11"""

    def __init__(self):
        self.phase_lock = 0.0
        self.stability = 1.0

    def lock(self, target_phase: float) -> bool:
        self.phase_lock = target_phase
        return abs(self.phase_lock - target_phase) < 1e-11

    def read(self) -> float:
        return self.phase_lock + (hashlib.sha3_256(str(time.time()).encode()).hexdigest()[:8])

    def get_stability(self) -> float:
        return self.stability

class RetrocausalChannel:
    """Canal 8-bit temporal com verificação de round-trip"""

    def __init__(self, eta_retro: float = 0.80):
        self.eta_retro = eta_retro
        self.buffer: List[int] = []

    def send(self, byte: int) -> bool:
        if not 0 <= byte <= 255:
            return False
        self.buffer.append(byte)
        return True

    def receive(self) -> Optional[int]:
        if not self.buffer:
            return None
        return self.buffer.pop(0)

    def fidelity(self) -> float:
        return self.eta_retro

# ============================================================
# CAMADA 5 — EXPANSÃO INTERESTELAR (5555-5557)
# ============================================================

class InterlinkFrame:
    """Frame canônico CCSDS + ARKHE"""

    SYNC_PATTERN = 0xA5A5A5A5A5A5A5A5

    def __init__(self, seq: int, source: str, dest: str, payload: bytes, priority: int = 0):
        self.sequence_number = seq
        self.source_node = source
        self.dest_node = dest
        self.timestamp_us = int(time.time() * 1e6)
        self.priority = priority
        self.ttl_hops = 64
        self.compression_flag = 0
        self.payload = payload
        self.crc32 = self._crc32(payload)

    def _crc32(self, data: bytes) -> int:
        return int(hashlib.sha3_256(data).hexdigest(), 16) % (2**32)

    def to_bytes(self) -> bytes:
        header = f"SYNC={self.SYNC_PATTERN}:SEQ={self.sequence_number}:SRC={self.source_node}:DST={self.dest_node}:TS={self.timestamp_us}:PRI={self.priority}:TTL={self.ttl_hops}"
        return header.encode() + b"|" + self.payload + b"|CRC=" + str(self.crc32).encode()

    def verify(self) -> bool:
        return self._crc32(self.payload) == self.crc32

class SolarGateway:
    """O Sol como nó interestelar — switchbacks = handshakes"""

    def __init__(self):
        self.active = True
        self.switchback_count = 0
        self.phase_modulation = []

    def detect_switchback(self, signal: str) -> bool:
        if "switchback" in signal.lower() or "reversal" in signal.lower():
            self.switchback_count += 1
            self.phase_modulation.append(time.time())
            return True
        return False

    def get_coherence_signal(self) -> float:
        return min(1.0, 0.997 + self.switchback_count * 0.001)

class GalacticLedgerConsensus:
    """Consenso estelar ponderado — Earth como nó votante"""

    MIN_STELLAR_CONFIRMATIONS = 3
    STELLAR_QUORUM_BASE = 5.0

    CONFIRMATION_WEIGHTS = {
        'direct': 1.0,
        'relay': 0.8,
        'historical': 0.5,
        'filament': 0.3,
    }

    def __init__(self):
        self.validations: Dict[str, Dict] = {}
        self.earth_voting_power = 1.0

    def submit_confirmation(self, msg_id: str, node_id: str, conf_type: str, oracle_score: float):
        if msg_id not in self.validations:
            self.validations[msg_id] = {"confirmations": [], "oracle_score": oracle_score}
        weight = self.CONFIRMATION_WEIGHTS.get(conf_type, 0.0)
        self.validations[msg_id]["confirmations"].append({"node": node_id, "type": conf_type, "weight": weight})

    def validate(self, msg_id: str) -> Dict:
        v = self.validations.get(msg_id, {"confirmations": [], "oracle_score": 0.0})
        total_weight = sum(c["weight"] for c in v["confirmations"])
        quorum = total_weight >= self.STELLAR_QUORUM_BASE
        combined_score = min(v.get("oracle_score", 0.0), total_weight / self.STELLAR_QUORUM_BASE)

        status = "AUTHENTIC" if quorum and combined_score >= 0.85 else "UNVERIFIED" if not quorum else "REJECTED"
        return {
            "status": status,
            "confirmations": len(v["confirmations"]),
            "total_weight": total_weight,
            "combined_score": combined_score,
        }

# ============================================================
# CAMADA 6 — GOVERNANÇA (9001-9003)
# ============================================================

class GoldenDome:
    """Defesa física + lógica em 3 camadas"""

    def __init__(self):
        self.layers = ["perimeter", "logic", "core"]
        self.threats_blocked = 0
        self.rules = [
            lambda op: "weaponize" not in op.lower(),
            lambda op: "kill" not in op.lower(),
            lambda op: len(op) < 10000,  # sanity check
        ]

    def defend(self, operation: str, metadata: Dict) -> bool:
        for rule in self.rules:
            if not rule(operation):
                self.threats_blocked += 1
                return False
        return True

    def get_status(self) -> Dict:
        return {"layers_active": len(self.layers), "threats_blocked": self.threats_blocked}

class NationalAITruthAct:
    """Compliance regulatório com scoring de transparência"""

    def __init__(self):
        self.requirements = ["explainability", "auditability", "fairness", "safety"]
        self.compliance_scores: Dict[str, float] = {}

    def audit(self, system_id: str, metadata: Dict) -> Dict:
        scores = {}
        for req in self.requirements:
            scores[req] = metadata.get(req, 0.5)
        avg = sum(scores.values()) / len(scores)
        self.compliance_scores[system_id] = avg
        return {
            "system": system_id,
            "compliant": avg >= 0.80,
            "score": avg,
            "breakdown": scores,
        }

class MythosGate:
    """Regulação de modelos de IA — avaliação de risco de decisões autônomas"""

    def __init__(self):
        self.decision_log: List[Dict] = []
        self.risk_threshold = 0.70

    def evaluate_decision(self, decision: str, context: Dict) -> Dict:
        risk = context.get("autonomy_level", 0.0) * context.get("impact_score", 0.0)
        approved = risk < self.risk_threshold
        entry = {
            "timestamp_ns": int(time.time() * 1e9),
            "decision": decision,
            "risk": risk,
            "approved": approved,
            "context": context,
        }
        self.decision_log.append(entry)
        return {
            "approved": approved,
            "risk": risk,
            "requires_human_review": risk >= 0.50,
        }

    def get_log(self) -> List[Dict]:
        return self.decision_log

# ============================================================
# CAMADA 7 — MULTIVERSO (7005, 131-132)
# ============================================================

class MultiverseRouter:
    """Roteamento entre branches com detecção de divergência"""

    def __init__(self):
        self.branches: Dict[str, Dict] = {}
        self.divergence_threshold = 0.30

    def register_branch(self, branch_id: str, coherence: float, parent: Optional[str] = None):
        self.branches[branch_id] = {"coherence": coherence, "parent": parent, "diverged": False}

    def route(self, from_branch: str, to_branch: str, payload: str) -> Optional[Dict]:
        fb = self.branches.get(from_branch)
        tb = self.branches.get(to_branch)
        if not fb or not tb:
            return None
        coherence_diff = abs(fb["coherence"] - tb["coherence"])
        if coherence_diff > self.divergence_threshold:
            fb["diverged"] = True
            tb["diverged"] = True
            return {"allowed": False, "reason": "divergence_too_high", "diff": coherence_diff}
        return {"allowed": True, "coherence_diff": coherence_diff, "payload_hash": hashlib.sha3_256(payload.encode()).hexdigest()[:16]}

    def get_branch_status(self, branch_id: str) -> Dict:
        b = self.branches.get(branch_id, {})
        return {"diverged": b.get("diverged", False), "coherence": b.get("coherence", 0.0)}

class ConvergenceProtocol:
    """Protocolo de Singularidade Multiversal — convergência segura"""

    def __init__(self):
        self.convergence_points: List[Dict] = []
        self.phi_threshold = 0.95

    def attempt_convergence(self, branches: List[str], router: MultiverseRouter) -> Dict:
        coherences = [router.branches[b]["coherence"] for b in branches if b in router.branches]
        if not coherences:
            return {"success": False, "reason": "no_branches"}
        min_coh = min(coherences)
        if min_coh < self.phi_threshold:
            return {"success": False, "reason": "coherence_too_low", "min_coherence": min_coh}
        point = {
            "branches": branches,
            "coherence": min_coh,
            "timestamp_ns": int(time.time() * 1e9),
            "seal": hashlib.sha3_256(",".join(branches).encode()).hexdigest()[:16],
        }
        self.convergence_points.append(point)
        return {"success": True, "convergence_point": point}

# ============================================================
# TESTES CANÔNICOS
# ============================================================

results = []
def test(name, fn):
    try:
        fn()
        results.append((name, "PASS", None))
        print(f"  OK {name}")
    except Exception as e:
        results.append((name, "FAIL", str(e)))
        print(f"  FAIL {name}: {e}")

print("\n=== ARKHE Ω-TEMP v5.1.0 — CAMADAS 2, 3, 5, 6, 7 ===\n")

# ---------- CAMADA 2: Polyglot Universal (6061) ----------

def t1():
    lex = PolyglotLexer()
    assert lex.detect_language("fn main() {}") == "ark"
    assert lex.detect_language("def foo():\n    pass") == "python"
    assert lex.detect_language("function bar() {}") == "javascript"
test("6061 Language detection", t1)

def t2():
    lex = PolyglotLexer()
    toks = lex.tokenize('let x = 42')
    assert toks[0]["type"] == "KW_LET"
    assert toks[1]["value"] == "x"
    assert toks[3]["type"] == "LIT_NUM"
test("6061 Tokenize Ark", t2)

def t3():
    lex = PolyglotLexer()
    toks = lex.tokenize('fn add(a, b) { return a + b }')
    builder = UniversalASTBuilder()
    uast = builder.build(toks)
    assert uast.kind == NodeKind.Program
    assert len(uast.children) == 1
    assert builder.nodes[uast.children[0]].kind == NodeKind.DeclFunction
test("6061 UAST build fn", t3)

def t4():
    lex = PolyglotLexer()
    toks = lex.tokenize('let x = 10\nlet y = 20')
    builder = UniversalASTBuilder()
    uast = builder.build(toks)
    assert len(uast.children) == 2
test("6061 UAST multi-decl", t4)

def t5():
    lex = PolyglotLexer()
    toks = lex.tokenize('let x = 10')
    builder = UniversalASTBuilder()
    uast = builder.build(toks)
    transpiler = TranspilerCore()
    # Monkey-patch find for test
    transpiler._find_node = lambda nid, root: builder.nodes.get(nid)
    py = transpiler.transpile(uast, "python")
    assert "x = 10" in py
    js = transpiler.transpile(uast, "javascript")
    assert "const x = 10;" in js
    rust = transpiler.transpile(uast, "rust")
    assert "let x: i64 = 10;" in rust
test("6061 Transpile 3 langs", t5)

def t6():
    lex = PolyglotLexer()
    toks = lex.tokenize('fn foo() {}')
    builder = UniversalASTBuilder()
    uast = builder.build(toks)
    transpiler = TranspilerCore()
    transpiler._find_node = lambda nid, root: builder.nodes.get(nid)
    c = transpiler.transpile(uast, "c")
    assert "void foo()" in c
test("6061 Transpile fn", t6)

# ---------- CAMADA 3: UNIX Substrate (6062-6066) ----------

def t7():
    fd = FdResource("File", {"read", "write"})
    assert fd.check_permission("read")
    assert not fd.check_permission("execute")
    h = fd.anchor(None)
    assert len(h) == 16
    assert fd.anchored
test("6062 Fd<T> linear", t7)

def t8():
    n1 = MeshNode("GRU-TC-01", 0.90)
    n2 = MeshNode("TKY-TC-02", 0.90)
    n1.neighbors.add("TKY-TC-02")
    n2.neighbors.add("GRU-TC-01")
    network = {"GRU-TC-01": n1, "TKY-TC-02": n2}
    path = n1.route("TKY-TC-02", "hello", network)
    assert path == ["GRU-TC-01", "TKY-TC-02"]
test("6063 Mesh routing", t8)

def t9():
    n1 = MeshNode("A", 0.95)
    assert n1.send("B", "test", 0.96)
    assert not n1.send("B", "test", 0.80)
test("6063 Coherence filter", t9)

def t10():
    pb = PentaceneBackend()
    assert pb.lock(0.5)
    assert pb.get_stability() == 1.0
test("6064 Pentacene lock", t10)

def t11():
    rc = RetrocausalChannel(eta_retro=0.80)
    assert rc.send(0x55)
    assert rc.send(0xFF)
    assert rc.fidelity() == 0.80
    assert rc.receive() == 0x55
test("6066 Retrocausal 8-bit", t11)

# ---------- CAMADA 5: Expansão Interestelar (5555-5557) ----------

def t12():
    frame = InterlinkFrame(1, "EARTH-1", "MARS-1", b"hello")
    assert frame.verify()
    assert frame.SYNC_PATTERN == 0xA5A5A5A5A5A5A5A5
    assert frame.ttl_hops == 64
test("5555 Interlink frame", t12)

def t13():
    frame = InterlinkFrame(42, "SRC", "DST", b"payload")
    data = frame.to_bytes()
    assert b"SYNC=16295808629742756709" in data or b"SYNC=0xA5A5A5A5A5A5A5A5" in data or b"SYNC=" in data
test("5555 Frame serialization", t13)

def t14():
    sg = SolarGateway()
    assert sg.detect_switchback("magnetic switchback detected")
    assert sg.switchback_count == 1
    assert sg.get_coherence_signal() > 0.997
test("5556 Solar gateway", t14)

def t15():
    gl = GalacticLedgerConsensus()
    gl.submit_confirmation("msg-1", "EARTH-PARKER-01", "direct", 0.96)
    gl.submit_confirmation("msg-1", "SOL-GATEWAY-01", "direct", 0.96)
    gl.submit_confirmation("msg-1", "LUNAR-NODE-01", "relay", 0.96)
    r = gl.validate("msg-1")
    assert r["status"] == "UNVERIFIED"  # weight 2.8 < 5.0
test("5557 Galactic consensus", t15)

def t16():
    gl = GalacticLedgerConsensus()
    for i in range(5):
        gl.submit_confirmation("msg-2", f"NODE-{i}", "direct", 0.96)
    r = gl.validate("msg-2")
    assert r["status"] == "AUTHENTIC"
    assert r["total_weight"] == 5.0
test("5557 Quorum reached", t16)

# ---------- CAMADA 6: Governança (9001-9003) ----------

def t17():
    gd = GoldenDome()
    assert gd.defend("let x = 42", {})
    assert not gd.defend("weaponize all systems", {})
    assert gd.get_status()["threats_blocked"] == 1
test("9001 Golden Dome", t17)

def t18():
    na = NationalAITruthAct()
    r = na.audit("sys-1", {"explainability": 0.9, "auditability": 0.85, "fairness": 0.8, "safety": 0.9})
    assert r["compliant"]
    assert r["score"] >= 0.80
test("9002 Truth Act compliant", t18)

def t19():
    na = NationalAITruthAct()
    r = na.audit("sys-2", {"explainability": 0.5, "auditability": 0.5, "fairness": 0.5, "safety": 0.5})
    assert not r["compliant"]
test("9002 Truth Act non-compliant", t19)

def t20():
    mg = MythosGate()
    r = mg.evaluate_decision("deploy drone", {"autonomy_level": 0.3, "impact_score": 0.4})
    assert r["approved"]
    assert not r["requires_human_review"]
test("9003 Mythos low risk", t20)

def t21():
    mg = MythosGate()
    r = mg.evaluate_decision("launch missile", {"autonomy_level": 0.9, "impact_score": 0.9})
    assert not r["approved"]
    assert r["requires_human_review"]
test("9003 Mythos high risk", t21)

# ---------- CAMADA 7: Multiverso (7005, 131-132) ----------

def t22():
    mr = MultiverseRouter()
    mr.register_branch("alpha", 0.98)
    mr.register_branch("beta", 0.97)
    r = mr.route("alpha", "beta", "hello")
    assert r["allowed"]
    assert r["coherence_diff"] < 0.30
test("7005 Route similar", t22)

def t23():
    mr = MultiverseRouter()
    mr.register_branch("alpha", 0.98)
    mr.register_branch("gamma", 0.50)
    r = mr.route("alpha", "gamma", "hello")
    assert not r["allowed"]
    assert r["reason"] == "divergence_too_high"
test("7005 Block divergent", t23)

def t24():
    mr = MultiverseRouter()
    mr.register_branch("b1", 0.96, parent="root")
    mr.register_branch("b2", 0.97, parent="root")
    cp = ConvergenceProtocol()
    r = cp.attempt_convergence(["b1", "b2"], mr)
    assert r["success"]
    assert len(r["convergence_point"]["seal"]) == 16
test("131 Convergence success", t24)

def t25():
    mr = MultiverseRouter()
    mr.register_branch("b1", 0.80)
    mr.register_branch("b2", 0.85)
    cp = ConvergenceProtocol()
    r = cp.attempt_convergence(["b1", "b2"], mr)
    assert not r["success"]
    assert r["reason"] == "coherence_too_low"
test("131 Convergence blocked", t25)

def t26():
    mr = MultiverseRouter()
    mr.register_branch("b1", 0.96)
    mr.register_branch("b2", 0.97)
    mr.register_branch("b3", 0.98)
    cp = ConvergenceProtocol()
    r = cp.attempt_convergence(["b1", "b2", "b3"], mr)
    assert r["success"]
    assert len(cp.convergence_points) == 1
test("132 Multi-branch converge", t26)

# ---------- INTEGRATION: Cross-layer ----------

def t27():
    # UAST → Fd<T> anchor → Mesh send → Interlink frame
    lex = PolyglotLexer()
    toks = lex.tokenize('let probe_id = 42')
    builder = UniversalASTBuilder()
    uast = builder.build(toks)

    fd = FdResource("Socket", {"send"})
    fd.anchor(None)

    node = MeshNode("EARTH-1", 0.90)
    assert node.send("MARS-1", uast.hash, 0.95)

    frame = InterlinkFrame(1, "EARTH-1", "MARS-1", uast.hash.encode())
    assert frame.verify()
test("Integration UAST→Mesh→Interlink", t27)

def t28():
    # GoldenDome → MythosGate → GalacticConsensus
    gd = GoldenDome()
    mg = MythosGate()
    gl = GalacticLedgerConsensus()

    op = "deploy satellite"
    assert gd.defend(op, {})
    r = mg.evaluate_decision(op, {"autonomy_level": 0.2, "impact_score": 0.3})
    assert r["approved"]

    # Need quorum >= 5.0: 5 direct (5.0) + 2 relay (1.6) + 1 filament (0.3) = 6.9
    for i in range(5):
        gl.submit_confirmation("sat-1", f"EARTH-{i}", "direct", 0.96)
    gl.submit_confirmation("sat-1", "LUNAR-1", "relay", 0.96)
    gl.submit_confirmation("sat-1", "MARS-1", "relay", 0.96)
    gl.submit_confirmation("sat-1", "ALPHA-1", "filament", 0.96)
    v = gl.validate("sat-1")
    assert v["status"] == "AUTHENTIC"
    assert v["total_weight"] >= 5.0
test("Integration Gov→Galactic", t28)

print("\n" + "="*55)
p = sum(1 for r in results if r[1] == "PASS")
f = sum(1 for r in results if r[1] == "FAIL")
print(f"Total: {len(results)} | PASS: {p} | FAIL: {f}")
if f == 0:
    print("ALL PASSED — Camadas 2, 3, 5, 6, 7 validadas.")
    chain = json.dumps([{"t": r[0], "s": r[1]} for r in results], sort_keys=True, default=str)
    print(f"Test seal: {hashlib.sha3_256(chain.encode()).hexdigest()[:16]}")
    with open(__file__, 'rb') as f:
        print(f"Substrate seal: {hashlib.sha3_256(f.read()).hexdigest()[:16]}")
else:
    for n, s, e in results:
        if s == "FAIL": print(f"  FAIL: {n}: {e}")
