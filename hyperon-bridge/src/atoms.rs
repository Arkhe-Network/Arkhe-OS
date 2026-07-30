//! Atom definitions and registration.
use hyperon::*;

pub fn register_dla_atoms(space: &mut AtomSpace) {
    let dla_state = ExpressionAtom::new(Symb::new("DLAState"), vec![Value::from(0), Value::from(0.0)]);
    space.add(dla_state);
}

pub fn register_merkle_atoms(space: &mut AtomSpace) {
    let merkle_root = ExpressionAtom::new(Symb::new("MerkleRoot"), vec![Value::from("")]);
    space.add(merkle_root);
}

pub fn register_policy_atoms(space: &mut AtomSpace) {
    let policy_rule = ExpressionAtom::new(
        Symb::new("PolicyRule"),
        vec![Value::from(""), Value::from(""), Value::from(0)],
    );
    space.add(policy_rule);
}
