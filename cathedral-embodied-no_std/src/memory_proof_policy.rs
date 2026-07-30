pub struct MemoryProofPolicy {
    interval: usize,
}
impl Default for MemoryProofPolicy {
    fn default() -> Self {
        Self { interval: 10 }
    }
}
impl MemoryProofPolicy {
    pub fn add_rule(&mut self, _rule: ()) {}
    pub fn set_commitment_interval(&mut self, interval: usize) {
        self.interval = interval;
    }
}
