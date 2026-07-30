
pub struct Gradient {}
pub struct GradientProof {}
pub fn prove_gradient(_g: &Gradient) -> Result<GradientProof, ()> { Ok(GradientProof {}) }
pub fn verify_gradient(_p: &GradientProof) -> Result<bool, ()> { Ok(true) }
