//! Lista de revogacao (CRL) compacta baseada em prova de inclusao Merkle.
//!
//! Este modulo implementa apenas a arvore de Merkle necessaria para provar
//! que um GDID especifico pertence ao conjunto de dispositivos revogados na
//! epoca corrente, sem depender de um crate externo de hashtree (nenhum
//! existe neste workspace). A prova comprova *inclusao*; a ausencia de uma
//! prova valida NAO e, por si so, uma prova criptografica de nao-revogacao
//! (isso exigiria uma sparse Merkle tree de profundidade fixa). Chamadores
//! que precisam de garantia forte de "nao revogado" devem tratar falha de
//! verificacao como "desconhecido" e aplicar a politica `fail_closed`.

use serde::{Deserialize, Serialize};

use super::cert::GdidError;
use super::Gdid;

/// Prova de inclusao Merkle (caminho de irmaos ate a raiz).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MerkleProof {
    /// Indice da folha na arvore (usado para saber o lado do irmao em cada nivel).
    pub leaf_index: u64,
    /// Hashes irmaos do caminho, da folha ate a raiz.
    pub siblings: Vec<[u8; 32]>,
}

impl MerkleProof {
    fn compute_root(&self, leaf_hash: &[u8; 32]) -> [u8; 32] {
        let mut current = *leaf_hash;
        let mut index = self.leaf_index;
        for sibling in &self.siblings {
            let mut hasher = blake3::Hasher::new();
            if index & 1 == 0 {
                hasher.update(&current);
                hasher.update(sibling);
            } else {
                hasher.update(sibling);
                hasher.update(&current);
            }
            current = *hasher.finalize().as_bytes();
            index >>= 1;
        }
        current
    }
}

/// Bundle de lista de revogacao (CRL) para um epoch especifico.
///
/// `sparse_proof` e a prova de inclusao para o GDID consultado nesta epoca
/// (o servidor emite um `CrlBundle` por consulta, contendo a prova relevante
/// para o GDID perguntado).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrlBundle {
    /// Numero da revisao (incrementa monotonicamente).
    pub epoch: u64,
    /// Quantidade de GDIDs revogados nesta revisao.
    pub revoked_count: u64,
    /// Raiz Merkle da CRL nesta epoca.
    pub root_hash: [u8; 32],
    /// Prova de inclusao para o GDID consultado.
    pub sparse_proof: MerkleProof,
}

impl CrlBundle {
    /// Verifica se a prova incluida comprova que `gdid` esta na lista de revogacao.
    ///
    /// Retorna `Ok(true)` apenas se a prova de inclusao for criptograficamente
    /// valida contra `root_hash`. Retorna `Err(GdidError::InvalidProof)` se a
    /// prova nao reconstituir a raiz esperada (o que tambem cobre o caso de
    /// o GDID nao estar revogado).
    pub fn is_revoked(&self, gdid: &Gdid) -> Result<bool, GdidError> {
        let leaf_hash = *blake3::hash(gdid.as_bytes()).as_bytes();
        let computed_root = self.sparse_proof.compute_root(&leaf_hash);

        if computed_root != self.root_hash {
            return Err(GdidError::InvalidProof);
        }

        Ok(true)
    }

    /// Verifica se o GDID NAO esta comprovadamente revogado por esta prova.
    ///
    /// Nota: isto reflete apenas o resultado desta prova especifica, nao uma
    /// garantia criptografica de nao-inclusao no conjunto completo.
    pub fn is_valid(&self, gdid: &Gdid) -> bool {
        !matches!(self.is_revoked(gdid), Ok(true))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn leaf_hash(gdid: &Gdid) -> [u8; 32] {
        *blake3::hash(gdid.as_bytes()).as_bytes()
    }

    fn hash_pair(left: &[u8; 32], right: &[u8; 32]) -> [u8; 32] {
        let mut hasher = blake3::Hasher::new();
        hasher.update(left);
        hasher.update(right);
        *hasher.finalize().as_bytes()
    }

    #[test]
    fn valid_inclusion_proof_verifies() {
        let revoked = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_ARKHE, &[1u8; 20], 1);
        let sibling_leaf = [0xABu8; 32];

        let leaf = leaf_hash(&revoked);
        let root = hash_pair(&leaf, &sibling_leaf);

        let bundle = CrlBundle {
            epoch: 1,
            revoked_count: 2,
            root_hash: root,
            sparse_proof: MerkleProof { leaf_index: 0, siblings: vec![sibling_leaf] },
        };

        assert_eq!(bundle.is_revoked(&revoked).unwrap(), true);
        assert!(!bundle.is_valid(&revoked));
    }

    #[test]
    fn tampered_root_fails_verification() {
        let revoked = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_ARKHE, &[1u8; 20], 1);
        let sibling_leaf = [0xABu8; 32];

        let bundle = CrlBundle {
            epoch: 1,
            revoked_count: 2,
            root_hash: [0u8; 32], // raiz incorreta
            sparse_proof: MerkleProof { leaf_index: 0, siblings: vec![sibling_leaf] },
        };

        assert!(bundle.is_revoked(&revoked).is_err());
        assert!(bundle.is_valid(&revoked));
    }
}
