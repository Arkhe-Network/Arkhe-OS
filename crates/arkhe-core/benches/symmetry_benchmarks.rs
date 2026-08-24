use criterion::{criterion_group, criterion_main, Criterion};
use arkhe_core::safety::symmetry_generator::{SymmetryGenerator, SystemState, SystemConfig};
use arkhe_core::safety::invariants::all_invariants;

fn bench_compute_spectral_gap(c: &mut Criterion) {
    let gen = SymmetryGenerator::new(all_invariants(), SystemConfig::default());
    let state = SystemState::safe(SystemConfig::default());

    c.bench_function("compute_spectral_gap", |b| {
        b.iter(|| gen.compute_spectral_gap(&state))
    });
}

fn bench_preserves_manifold(c: &mut Criterion) {
    let gen = SymmetryGenerator::new(all_invariants(), SystemConfig::default());
    let from = SystemState::safe(SystemConfig::default());
    let mut to = SystemState::safe(SystemConfig::default());
    to.token_budget -= 100;

    c.bench_function("preserves_manifold", |b| {
        b.iter(|| gen.preserves_manifold(&from, &to))
    });
}

criterion_group!(benches, bench_compute_spectral_gap, bench_preserves_manifold);
criterion_main!(benches);
