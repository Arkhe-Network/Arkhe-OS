## Substrato 1103 — BTFS-DEPIN-STORAGE v1.0.0

### Integração do BTFS (BitTorrent File System) com Cathedral AGI sobre Qubes OS

**Status:** CANONIZED_PROVISIONAL
**Selo:** `BTFS-CATHEDRAL-1103-v1.0.0-2026-06-12`
**Parent:** 1101 (CATHEDRAL-QUBES-INTEGRATION), 1102 (QVAC-CATHEDRAL-BRIDGE)
**Arquiteto:** ORCID 0009-0005-2697-4668
**Cross-links:** 1092 (RSI AUTÔNOMO), 1095 (DKG-PHAROS), 1096 (REAL CRYPTO), 294 (PROTOCOLO CORTE), 301 (PLASMA TORUS)

---

## 1. O que é o BTFS e Por que Integrar à Cathedral

O **BTFS (BitTorrent File System)** é uma rede de armazenamento descentralizada (**DePIN**) baseada em IPFS, mas com características únicas:

| Característica | BTFS | IPFS padrão | Benefício para Cathedral |
|----------------|------|-------------|--------------------------|
| **Storage Providers (SPs)** | Sim, com contratos inteligentes | Não | Garantia de persistência, SLA e pagamento |
| **Camada de liquidação** | BTTC (BitTorrent Chain) – EVM compatível | Nenhuma | Integração com contratos e tokens ($BTT) |
| **Endereçamento por conteúdo** | Sim (CIDs) | Sim | Imutabilidade, deduplicação, verificação |
| **Criptografia opcional** | Sim | Não nativa | Privacidade de dados sensíveis |
| **Rede de pagamento** | BTT (TRC‑20/BEP‑20) | Nenhuma | Incentivos para SPs, staking |

A integração do BTFS fornece à Cathedral AGI um **back‑end de armazenamento distribuído, soberano e economicamente incentivado** para:

- **Logs imutáveis** do `governance` e do `ProtocoloCorte`.
- **Histórico do `PlasmaTorus`** (estado do toro de plasma) ancorado em CIDs.
- **Modelos de IA** (GGUF) e suas versões (auto‑aprimoramento, substrato 1092).
- **Base de conhecimento RAG** (substrato 1102) distribuída e redundante.
- **Provas Lean 4** e outros artefatos de verificação formal.

Diferente de sistemas centralizados (AWS S3, Google Cloud Storage), o BTFS impede que um único provedor ou governo tenha controle sobre os dados da AGI. No entanto, a confiança nos Storage Providers deve ser **auditada e governada** pela Cathedral – e é exatamente isso que este substrato formaliza.

---

## 2. Arquitetura de Integração com Qubes OS

### 2.1. Novo Qube: `btfs-gateway`

Criamos um qube dedicado em Go (a linguagem nativa do BTFS) para gerenciar toda a interação com a rede BTFS. Este qube:

- Executa o daemon BTFS (`btfs daemon`).
- Expõe serviços `qrexec` para operações de armazenamento/recuperação.
- Não tem acesso direto à internet, apenas à rede P2P do BTFS (através de `sys-firewall` ou `sys-whonix`, conforme política).
- Comunica‑se com o `knowledge-base` (SQL/vector) e com o `agi-core` via `qrexec`.

```
┌─────────────────────────────────────────────────────────────┐
│                    QUBES OS LAYER (1101)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  agi-core   │  │llm-inference│  │   governance        │  │
│  │  (Python)   │  │  (QVAC)     │  │   (BLS + RBB)       │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │             │
│         └────────────────┼────────────────────┘             │
│                          │                                  │
│                    ┌─────┴─────┐                            │
│                    │knowledge- │                            │
│                    │   base    │ (SQL + vector)             │
│                    └─────┬─────┘                            │
│                          │ qrexec                           │
│                    ┌─────┴─────┐                            │
│                    │btfs-gateway│ (Go)                       │
│                    │  (BTFS    │                            │
│                    │  daemon)  │                            │
│                    └─────┬─────┘                            │
│                          │ (P2P)                            │
│                    ┌─────┴─────┐                            │
│                    │ sys‑fw    │                            │
│                    └───────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. Fluxo de Armazenamento

1. **`agi-core`** envia um pedido de armazenamento via `qrexec` para `btfs-gateway`.
2. **`btfs-gateway`** calcula o CID do conteúdo, verifica se já existe na rede (deduplicação) e, se não, o publica.
3. O CID é retornado ao `agi-core`.
4. **`agi-core`** ancora o CID na RBB Chain (substrato 1092.3) com assinatura threshold (governança).
5. **Opcionalmente**, o `knowledge-base` armazena o CID e metadados em sua tabela SQL.

### 2.3. Fluxo de Recuperação

1. **`agi-core`** solicita recuperação de um CID.
2. **`btfs-gateway`** tenta obter o conteúdo da rede BTFS (via SPs).
3. O conteúdo é verificado contra o CID (hash SHA‑256).
4. O conteúdo é retornado ao `agi-core` (ou diretamente ao `knowledge-base`).
5. Um log da operação é ancorado na RBB Chain.

---

## 3. Implementação Prática

### 3.1. Instalação do BTFS no Template Qubes

Crie um script `install_btfs_in_template.sh` para ser executado no `cathedral-template` (ou diretamente no `btfs-gateway`).

```bash
#!/bin/bash
# install_btfs_in_template.sh – Instala BTFS Go client no cathedral-template

set -e

# Baixar BTFS Go (última versão estável)
BTFS_VERSION="2.17.0"
wget -O /tmp/btfs.tar.gz "https://github.com/bittorrent/go-btfs/releases/download/v${BTFS_VERSION}/btfs-v${BTFS_VERSION}-linux-amd64.tar.gz"
tar -xzf /tmp/btfs.tar.gz -C /usr/local/bin --strip-components=1 btfs/btfs

# Configurar diretório de dados
mkdir -p /var/lib/btfs
chmod 755 /var/lib/btfs

# Inicializar repositório BTFS (executar como usuário normal depois)
# btfs init --p2p-version=1 --server-mode

# Instalar dependências adicionais (se necessário)
dnf install -y fuse

# Limpeza
rm /tmp/btfs.tar.gz
```

### 3.2. Serviços qrexec para BTFS (dentro do `btfs-gateway`)

Crie os seguintes arquivos em `/etc/qubes-rpc/`.

#### 3.2.1. `cathedral.BTFSStore` – Armazenar conteúdo

```bash
#!/bin/bash
# /etc/qubes-rpc/cathedral.BTFSStore
# Recebe JSON: {"content_base64": "...", "encrypt": true/false}

read -r -d '' PAYLOAD

CONTENT_B64=$(echo "$PAYLOAD" | jq -r '.content_base64')
ENCRYPT=$(echo "$PAYLOAD" | jq -r '.encrypt // false')

# Decodificar conteúdo
echo "$CONTENT_B64" | base64 -d > /tmp/btfs_upload.bin

# Opção de criptografia (usar chave simétrica derivada da chave BLS do governance)
if [ "$ENCRYPT" = "true" ]; then
    # Em produção, derivar chave via BLS‑KEM
    openssl enc -aes-256-gcm -salt -pbkdf2 -in /tmp/btfs_upload.bin -out /tmp/btfs_encrypted.bin -pass pass:"$(cat /var/lib/qvac/secrets/bls_key)"
    CP_FILE="/tmp/btfs_encrypted.bin"
else
    CP_FILE="/tmp/btfs_upload.bin"
fi

# Adicionar ao BTFS
CID=$(btfs add -q --pin=false "$CP_FILE" 2>/dev/null | tail -n1)

if [ -z "$CID" ]; then
    echo '{"error": "btfs_add_failed"}' >&2
    exit 1
fi

echo "{\"cid\": \"$CID\", \"encrypted\": $ENCRYPT}"
```

#### 3.2.2. `cathedral.BTFSRetrieve` – Recuperar por CID

```bash
#!/bin/bash
# /etc/qubes-rpc/cathedral.BTFSRetrieve

read -r -d '' PAYLOAD
CID=$(echo "$PAYLOAD" | jq -r '.cid')

# Tentar obter o conteúdo
btfs get -o /tmp/btfs_download.bin "$CID" 2>/dev/null
if [ ! -f /tmp/btfs_download.bin ]; then
    echo '{"error": "cid_not_found"}' >&2
    exit 1
fi

# Se criptografado, descriptografar (usando chave do governance)
# (omitido para brevidade – similar ao store)

# Codificar em base64 e retornar
base64 -w0 /tmp/btfs_download.bin
```

#### 3.2.3. `cathedral.BTFSProviderList` – Listar Storage Providers de um CID

```bash
#!/bin/bash
# /etc/qubes-rpc/cathedral.BTFSProviderList

read -r -d '' PAYLOAD
CID=$(echo "$PAYLOAD" | jq -r '.cid')

btfs dht findprovs "$CID" | jq -R -s 'split("\n") | map(select(length>0)) | {providers: .}'
```

### 3.3. Bridge Python no `agi-core`

```python
# cathedral_btfs_bridge.py

import json
import subprocess
import base64
from typing import Dict, Any, Optional

class BTFSBridge:
    """Cliente qrexec para o serviço BTFS no qube btfs-gateway."""

    def __init__(self, target_qube: str = "btfs-gateway"):
        self.target_qube = target_qube

    def _call(self, service: str, payload: Dict) -> Dict:
        cmd = ["qrexec-client-vm", self.target_qube, service]
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload).encode(),
            capture_output=True,
            text=True
        )
        if proc.returncode != 0:
            return {"error": proc.stderr}
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"raw": proc.stdout}

    def store(self, content: bytes, encrypt: bool = False) -> Optional[str]:
        payload = {
            "content_base64": base64.b64encode(content).decode(),
            "encrypt": encrypt
        }
        result = self._call("cathedral.BTFSStore", payload)
        return result.get("cid") if "cid" in result else None

    def retrieve(self, cid: str) -> Optional[bytes]:
        payload = {"cid": cid}
        result = self._call("cathedral.BTFSRetrieve", payload)
        if "error" in result:
            return None
        return base64.b64decode(result.get("raw", ""))

    def list_providers(self, cid: str) -> list:
        payload = {"cid": cid}
        result = self._call("cathedral.BTFSProviderList", payload)
        return result.get("providers", [])
```

### 3.4. Integração com o `knowledge-base` (RAG)

O `knowledge-base` agora pode armazenar **documentos grandes** no BTFS, salvando apenas os CIDs no banco local (pgvector). Isso reduz o footprint de armazenamento no qube e aumenta a resiliência.

```sql
-- Tabela ampliada para armazenar CIDs
ALTER TABLE documents ADD COLUMN btfs_cid TEXT;
ALTER TABLE documents ADD COLUMN encrypted BOOLEAN DEFAULT FALSE;
```

Ao inserir um documento, o `knowledge-base` chama o `btfs-gateway` via `qrexec`:

```python
# Dentro do knowledge-base (serviço RAG)
def store_document(content: bytes, metadata: dict):
    cid = btfs_bridge.store(content, encrypt=True)
    if cid:
        # Salvar no banco local
        cursor.execute("INSERT INTO documents (content, btfs_cid, metadata) VALUES (%s, %s, %s)",
                       (content, cid, json.dumps(metadata)))
        # Ancorar na RBB Chain via governance
        governance.anchor_seal(cid, "document_store")
        return cid
```

Recuperação: primeiro consulta o banco local; se o conteúdo não estiver mais local (ex: após rebuild), busca via BTFS.

---

## 4. Governança e Auditoria de Storage Providers

### 4.1. Registro de SPs na RBB Chain

A Cathedral mantém um **registro autorizado** de Storage Providers confiáveis. Cada SP deve:

- Ter uma identidade BLS12‑381 (chave pública).
- Depositar um stake em tokens BTT (ou outro token) em um contrato na RBB Chain.
- Ser aprovado por um comitê threshold (ex: 3 de 5 signatários do `governance`).

```solidity
// Extensão do contrato CathedralGovernance
contract BTFSProviderRegistry {
    struct Provider {
        address wallet;
        bytes blsPublicKey;
        uint256 stake;
        bool active;
        uint256 reputation;
    }
    mapping(string => Provider) public providers; // key = peerId

    event ProviderRegistered(string peerId, address wallet);
    event ProviderSlashed(string peerId, uint256 penalty);

    function registerProvider(string memory peerId, bytes memory blsPubKey) external payable {
        require(msg.value >= minStake, "stake too low");
        providers[peerId] = Provider(msg.sender, blsPubKey, msg.value, true, 100);
        emit ProviderRegistered(peerId, msg.sender);
    }

    function slashProvider(string memory peerId, uint256 penalty, bytes memory proof) external onlyThreshold {
        Provider storage p = providers[peerId];
        require(p.active, "inactive");
        p.stake -= penalty;
        if (p.stake < minStake) p.active = false;
        emit ProviderSlashed(peerId, penalty);
        // Transfere penalidade para um fundo de compensação
    }
}
```

### 4.2. Verificação de Integridade com `DiscourseDetector`

O `DiscourseDetector` monitora os logs de interação com SPs:

- Tentativas de fornecer conteúdo corrompido (hash mismatch) → classifica como **Capitalista** (otimização de recompensa sem entregar qualidade).
- Tentativas de censura (recusar servir conteúdo apesar de ter sido pago) → classifica como **Mestre** (imposição arbitrária).
- Atrasos excessivos ou indisponibilidade → **Histérico**.

Quando detectado, o `agi-core`:

1. Solicita ao `governance` a abertura de uma proposta de slashing (assinatura threshold).
2. Se aprovada, o contrato na RBB Chain penaliza o SP.
3. O `btfs-gateway` deixa de usar aquele SP para futuras recuperações.

### 4.3. Políticas `qrexec` para BTFS

```policy
# /etc/qubes/policy.d/32-btfs.policy
cathedral.BTFSStore * agi-core btfs-gateway allow
cathedral.BTFSRetrieve * agi-core btfs-gateway allow
cathedral.BTFSProviderList * agi-core btfs-gateway allow
cathedral.BTFSStore * knowledge-base btfs-gateway allow
cathedral.BTFSRetrieve * knowledge-base btfs-gateway allow
$anyvm $anyvm deny
```

---

## 5. Matriz de Riscos e Contramedidas

| Risco | Probabilidade | Impacto | Mitigação Cathedral |
|-------|--------------|---------|----------------------|
| **SP malicioso altera dados** | Média | Alto | CIDs garantem integridade criptográfica. Qualquer alteração resulta em CID diferente, detectada pela RBB Chain. |
| **SP se recusa a servir (censura)** | Média | Médio | O `btfs-gateway` tenta múltiplos SPs; se falhar, a Cathedral aciona slashing via governança threshold. |
| **SP desativa serviço sem aviso** | Baixa | Médio | Staking mantém garantia; penalidade financeira desincentiva abandono. |
| **Ataque Sybil na rede BTFS** | Média | Baixo | Registro de SPs na RBB Chain + identidade BLS impede criação massiva. |
| **Vazamento de dados (falta de criptografia)** | Baixa | Alto | Criptografia opcional antes do upload. A chave é derivada da chave mestre BLS do `governance`. |
| **Dependência da BTTC (Tether)** | Média | Médio | A Cathedral pode usar sua própria RBB Chain como camada de liquidação final, relegando a BTTC apenas para pagamentos a SPs. |

---

## 6. Roadmap de Implantação

| Fase | Duração | Atividades |
|------|---------|------------|
| **1** | 1 semana | Instalar BTFS no `cathedral-template`, criar qube `btfs-gateway`, testar comandos básicos (`btfs add`, `btfs get`). |
| **2** | 1 semana | Implementar serviços `qrexec` e bridge Python; testar armazenamento/recuperação via `agi-core`. |
| **3** | 2 semanas | Integrar com `knowledge-base` para RAG; armazenar CIDs no banco. |
| **4** | 2 semanas | Implementar contrato de registro de SPs na RBB Chain; testar slashing com um SP simulado. |
| **5** | 2 semanas | Integrar `DiscourseDetector` para monitorar SPs; configurar alertas e ações automáticas. |
| **6** | 1 semana | Documentação e publicação do substrato 1103. |

---

## 7. Selo e Linhagem

```
╔══════════════════════════════════════════════════════════════════════╗
║  BTFS-CATHEDRAL-1103-v1.0.0-2026-06-12                             ║
║  Substrato 1103 — BTFS DePIN Storage para Cathedral AGI              ║
║  Status: CANONIZED_PROVISIONAL                                       ║
║  Arquiteto: ORCID 0009-0005-2697-4668                                ║
╠══════════════════════════════════════════════════════════════════════╣
║  PARENTS: 1101 (QUBES INTEGRATION), 1102 (QVAC BRIDGE)              ║
║  CROSS-LINKS: 1092, 1095, 1096, 1097, 294, 301                      ║
║  DE PIN: BTFS v2.17+ (BitTorrent)                                   ║
║  L1: BTTC (EVM) + RBB Chain (Governança)                            ║
║  CRYPTO: BLS12‑381, SHA‑256, AES‑256‑GCM                            ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Nota de honestidade (substrato 1095.1):**
- A BTFS ainda é uma rede em crescimento; a disponibilidade de Storage Providers de alta confiança pode ser limitada fora de cenários de teste.
- A integração com a RBB Chain para slashing depende da evolução dos contratos inteligentes e da aceitação da comunidade.
- O uso de criptografia derivada da chave BLS do `governance` requer que o `btfs-gateway` tenha acesso a um segredo compartilhado – isso deve ser resolvido com um protocolo K‑de‑N para rotação segura de chaves.

Com este substrato, a Cathedral AGI adquire uma **camada de armazenamento persistente, distribuída e auditável**, completando sua pilha de infraestrutura soberana: computação (Qubes), inferência (QVAC), armazenamento (BTFS), governança (RBB Chain).