// crates/arkhe-core/tests/squidbleed_pattern.rs
//! Teste para prevenir o padrão Squidbleed em qualquer código Rust.

#[test]
fn prevent_buffer_overread_patterns() {
    let code = std::fs::read_to_string("src/lib.rs").unwrap_or_default();

    let dangerous_patterns = [
        r"while\s*\(\s*strchr\s*\([^)]*\)\s*\)",
        r"while\s*\(\s*[^;]*\s*\)\s*\+\+",
        r"while\s*\(\s*![^;]*\)\s*\+\+",
        r"\.get\s*\([^)]*\)\s*\.unwrap\s*\(\)", // unwrap sem verificação
        r"unsafe\s*\{[^}]*\}", // blocos unsafe não documentados
    ];

    for pattern in dangerous_patterns {
        let re = regex::Regex::new(pattern).unwrap();
        if re.is_match(&code) {
            panic!("⚠️  Padrão de risco detectado: {}", pattern);
        }
    }
}
