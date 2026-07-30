
pub struct BFVContext {}
impl BFVContext {
    pub fn new(_a: u32, _b: u32) -> Self { Self {} }
}
pub struct BFVEncoder {}
impl BFVEncoder {
    pub fn new(_ctx: &BFVContext) -> Self { Self {} }
}
pub struct BFVEvaluator {}
impl BFVEvaluator {
    pub fn new(_ctx: &BFVContext) -> Self { Self {} }
    pub fn add(&self, a: &[u8], _b: &[u8]) -> Vec<u8> { a.to_vec() }
}
pub struct BFVKeyGenerator {}
impl BFVKeyGenerator {
    pub fn new(_ctx: &BFVContext) -> Self { Self {} }
}
