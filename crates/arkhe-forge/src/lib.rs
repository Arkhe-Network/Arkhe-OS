// arkhe-forge lib
pub fn verify_host_boundary() {}
pub fn verify_wasm_sandbox() {}

#[cfg(kani)]
mod verification {
    use super::*;

    #[kani::proof]
    fn verify_host_boundary() {
        super::verify_host_boundary();
    }

    #[kani::proof]
    fn verify_wasm_sandbox() {
        super::verify_wasm_sandbox();
    }
}
