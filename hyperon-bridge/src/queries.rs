//! MeTTa query helpers.
use hyperon::*;

/// Query DLA state by pattern matching.
pub fn query_dla_state(space: &AtomSpace) -> Option<(usize, f32)> {
    let pattern = ExpressionAtom::new(Symb::new("DLAState"), vec![Var::new("segments").into(), Var::new("util").into()]);
    for atom in space.query(&pattern) {
        if let Some(expr) = atom.as_expression() {
            let args = expr.args();
            if args.len() == 2 {
                let segments = args[0].as_number().map(|n| n as usize)?;
                let util = args[1].as_number().map(|n| n as f32)?;
                return Some((segments, util));
            }
        }
    }
    None
}

/// Query the latest Merkle root.
pub fn query_merkle_root(space: &AtomSpace) -> Option<String> {
    let pattern = ExpressionAtom::new(Symb::new("MerkleRoot"), vec![Var::new("root").into()]);
    for atom in space.query(&pattern) {
        if let Some(expr) = atom.as_expression() {
            let args = expr.args();
            if args.len() == 1 {
                return args[0].as_string().map(|s| s.to_string());
            }
        }
    }
    None
}
