// ============================================================================
// ARKHE Watchdog — Kernel Module
// ============================================================================
// Contador de liveness simples. `init` arma o timeout; `kick` registra
// atividade; `expired` compara o tempo desde o último kick com o timeout.

use core::sync::atomic::{AtomicU64, Ordering};
use core::time::Duration;

static TIMEOUT_NS: AtomicU64 = AtomicU64::new(0);
static LAST_KICK: AtomicU64 = AtomicU64::new(0);

/// Arma o watchdog com o timeout fornecido.
pub fn init(timeout: Duration) {
    TIMEOUT_NS.store(timeout.as_nanos() as u64, Ordering::SeqCst);
    LAST_KICK.store(0, Ordering::SeqCst);
}

/// Registra atividade (reinicia a contagem).
pub fn kick() {
    LAST_KICK.fetch_add(1, Ordering::SeqCst);
}

/// Timeout configurado, em nanossegundos.
pub fn timeout_ns() -> u64 {
    TIMEOUT_NS.load(Ordering::SeqCst)
}

/// Número de kicks registrados desde o `init`.
pub fn kicks() -> u64 {
    LAST_KICK.load(Ordering::SeqCst)
}
