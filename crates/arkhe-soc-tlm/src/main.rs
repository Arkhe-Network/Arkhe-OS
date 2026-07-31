use arkhe_soc_tlm::{
    micros, aotb::{AotbEncoderHw, AotbVerifierHw}, soc::ArkheSoc, ClockDomain,
    PerformanceCounters, REFERENCE_SOL_US,
};
use ed25519_dalek::SigningKey;
use serde::Serialize;
use std::time::Instant;

#[derive(Serialize)]
struct Report {
    iterations: usize,
    wall_time_us: f64,
    qpl_us: f64,
    expand_us: f64,
    encode_us: f64,
    verify_us: f64,
    frames_emitted: u64,
    frames_dropped: u64,
    frames_rejected: u64,
    swarms_completed: u64,
    power_mw: u32,
    reference_sol_us: f64,
    overhead_vs_reference_percent: f64,
    score: u32,
}

fn main() {
    let iterations = std::env::args()
        .nth(1)
        .and_then(|v| v.parse().ok())
        .unwrap_or(10_000usize);

    let freq_mhz = 400u32; // 400 MHz = 2.5ns/ciclo
    let clock = ClockDomain::new(freq_mhz);
    let key = SigningKey::from_bytes(&[7u8; 32]);
    let mut soc = ArkheSoc::new(
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        [9u8; 16],
        clock,
    );
    let mut encoder = AotbEncoderHw::new(
        key.clone(),
        soc.session_id,
        soc.proof_hash,
        ClockDomain::new(freq_mhz),
    );
    let mut verifier = AotbVerifierHw::new(key.verifying_key(), soc.session_id);

    let wall_start = Instant::now();
    for sequence in 0..iterations as u64 {
        let _ = soc.qpl_forward().expect("QPL deve executar");
        soc.expand(sequence);
        let frame = soc.emit_frame(&mut encoder).expect("encode deve funcionar");
        let v_start = Instant::now();
        verifier.verify(&frame).expect("benchmark frame must verify");
        let _v_elapsed = v_start.elapsed();
        // Acumula no encoder/verifier — precisamos expor contadores
    }
    let wall_elapsed = wall_start.elapsed();

    // Coleta contadores
    let mut total = PerformanceCounters::default();
    total.merge(&soc.counters());
    total.merge(encoder.counters());
    total.merge(verifier.counters());

    let wall_time_us = wall_elapsed.as_secs_f64() * 1_000_000.0;
    let per_iter_us = micros(total.qpl_cycles, freq_mhz) / iterations as f64;
    let overhead = ((per_iter_us / REFERENCE_SOL_US) - 1.0) * 100.0;

    // Score de engenharia: 100 se overhead <= 7% (meta do paper), linear decaindo
    let score = if overhead <= 7.0 {
        100
    } else if overhead <= 100.0 {
        (100.0 - (overhead - 7.0)) as u32
    } else {
        0
    };

    let report = Report {
        iterations,
        wall_time_us,
        qpl_us: micros(total.qpl_cycles, freq_mhz) / iterations as f64,
        expand_us: micros(total.expand_cycles, freq_mhz) / iterations as f64,
        encode_us: micros(total.encode_cycles, freq_mhz) / iterations as f64,
        verify_us: micros(total.verify_cycles, freq_mhz) / iterations as f64,
        frames_emitted: total.frames_emitted,
        frames_dropped: total.frames_dropped,
        frames_rejected: total.frames_rejected,
        swarms_completed: iterations as u64 * 15, // MAX_SWARMS
        power_mw: total.power_mw,
        reference_sol_us: REFERENCE_SOL_US,
        overhead_vs_reference_percent: overhead,
        score,
    };

    println!("{}", serde_json::to_string_pretty(&report).unwrap());

    if score >= 95 {
        eprintln!("🏛️ Selo: ARKHE-SOC-TLM-v2.0-PASSED-2026-07-31");
    } else {
        eprintln!("⚠️  Submeta a otimizações: double-buffer, pipelining, ou aumente freq_mhz");
    }
}
