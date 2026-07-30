//! Hyperon Bridge – Exposes Cathedral ARKHE components as atoms.
pub mod atoms;
pub mod queries;

use hyperon::*;

/// Initialize an AtomSpace with Cathedral‑specific atoms and rules.
pub fn init_cathedral_atomspace() -> AtomSpace {
    let mut space = AtomSpace::new();
    atoms::register_dla_atoms(&mut space);
    atoms::register_merkle_atoms(&mut space);
    atoms::register_policy_atoms(&mut space);
    space
}

/// Expose DLA state (active_segments, utilization) as a ground atom.
pub fn expose_dla_state(space: &mut AtomSpace, active_segments: usize, utilization: f32) {
    let atom = ExpressionAtom::new(
        Symb::new("DLAState"),
        vec![
            Value::from(active_segments as i64),
            Value::from(utilization as f64),
        ],
    );
    space.add(atom);
}

/// Expose a Merkle root (as a symbolic constant).
pub fn expose_merkle_root(space: &mut AtomSpace, root_hex: &str) {
    let atom = ExpressionAtom::new(
        Symb::new("MerkleRoot"),
        vec![Value::from(root_hex)],
    );
    space.add(atom);
}
