//! ARKHE — Teste de Invariante ML-002
//! "Versionamento e Reprodutibilidade de Pipelines"
//!
//! Verifica se um pipeline de ML produz identical outputs
//! quando executado 3× com seeds diferentes em ambiente containerizado.

use arkhe_materials::ml::pipeline::{MlPipeline, Seed};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

const MAX_R2_VARIANCE: f64 = 0.01;
const SEEDS: [u64; 3] = [42, 123, 999];

#[test]
fn ml002_reproducibility_cross_seed() {
    let dataset = load_perovskite_dataset_full();
    let mut results: Vec<f64> = Vec::new();

    for seed in SEEDS {
        let pipeline = MlPipeline::new()
            .seed(Seed::fixed(seed))
            .split_strategy("stratified_kfold")
            .model(BaselineModel::random_forest().n_estimators(500))
            .train(&dataset);

        let metrics = pipeline.evaluate();
        results.push(metrics.r2);
    }

    let mean_r2 = results.iter().sum::<f64>() / results.len() as f64;
    let variance = results.iter()
        .map(|r| (r - mean_r2).powi(2))
        .sum::<f64>() / results.len() as f64;
    let std_dev = variance.sqrt();

    assert!(
        std_dev < MAX_R2_VARIANCE,
        "ML-002 VIOLADO: Desvio padrão de R² entre seeds ({:.4}) excede limiar ({:.4}).          Resultados: {:?}",
        std_dev, MAX_R2_VARIANCE, results
    );
}

#[test]
fn ml002_containerized_environment() {
    // Verificar se estamos rodando dentro de Docker
    let in_docker = std::path::Path::new("/.dockerenv").exists()
        || std::fs::read_to_string("/proc/1/cgroup")
            .unwrap_or_default()
            .contains("docker");

    assert!(
        in_docker,
        "ML-002 VIOLADO: Pipeline não está executando em ambiente containerizado.          Execute via Docker para garantir reprodutibilidade."
    );

    // Verificar se requirements/poetry.lock existe
    assert!(
        std::path::Path::new("poetry.lock").exists(),
        "ML-002 VIOLADO: poetry.lock não encontrado. Dependências não estão fixas."
    );
}

#[test]
fn ml002_dvc_versioning() {
    // Verificar se DVC está configurado
    let dvc_dir = std::path::Path::new(".dvc");
    assert!(
        dvc_dir.exists(),
        "ML-002 VIOLADO: Diretório .dvc não encontrado. DVC não está configurado."
    );

    // Verificar se dados estão versionados
    let dvc_file = std::path::Path::new("data/perovskites.csv.dvc");
    assert!(
        dvc_file.exists(),
        "ML-002 VIOLADO: Arquivo data/perovskites.csv.dvc não encontrado.          Dataset não está versionado via DVC."
    );
}