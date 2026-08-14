use std::env;

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-env-changed=ARKHE_QUANTUM_AUTH_FORCE_NO_STD");

    let target_arch = env::var("CARGO_CFG_TARGET_ARCH").unwrap_or_default();
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();

    if target_arch == "x86_64" || target_arch == "x86" {
        println!("cargo:rustc-cfg=target_has_aesni");
    }
    if target_arch == "aarch64" {
        println!("cargo:rustc-cfg=target_has_neon_aes");
    }

    let features: Vec<String> = env::vars()
        .filter(|(k, _)| k.starts_with("CARGO_FEATURE_"))
        .map(|(k, _)| k.strip_prefix("CARGO_FEATURE_").unwrap().to_lowercase())
        .collect();

    if features.iter().any(|s| s == "std") && features.iter().any(|s| s == "no_std") {
        panic!("arkhe-quantum-auth: cannot enable both `std` and `no_std` features");
    }

    if features.iter().any(|s| s == "no_std") && !features.iter().any(|s| s == "alloc") {
        panic!("arkhe-quantum-auth: `no_std` feature requires `alloc`");
    }

    if features.iter().any(|s| s == "no_std") && target_os != "none" && target_os != "linux" {
        println!("cargo:warning=Building no_std for target_os={}. Ensure custom getrandom impl is provided.", target_os);
    }

    if features.iter().any(|s| s == "arkhe_pea") && !features.iter().any(|s| s == "arkhe_core") {
        println!("cargo:warning=arkhe-pea integration recommended with arkhe-core DID types");
    }
}
