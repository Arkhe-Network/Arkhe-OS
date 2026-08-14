use criterion::{criterion_group, criterion_main, Criterion};

fn bench_hash(c: &mut Criterion) {
    let data = vec![0u8; 1024];
    c.bench_function("blake3 1KB", |b| b.iter(|| blake3::hash(&data)));
}

criterion_group!(benches, bench_hash);
criterion_main!(benches);
