#!/usr/bin/env python3
"""
ARKHE — Validation Script for ML Invariants (ML-001, ML-002, ML-003)

Uso:
    python validate_ml_invariants.py --model-path ./models/ --data-path ./data/

Valida:
    ML-001: Baseline estatístico (comparação com regressão linear)
    ML-002: Reprodutibilidade (seed fixa, DVC, Docker)
    ML-003: Precisão numérica (float64 em simulações quânticas)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import click
import numpy as np
import pandas as pd
import yaml
from sklearn.datasets import make_regression
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_squared_error, r2_score


# ─── ML-001: Baseline Validation ──────────────────────────────────────────

def validate_ml001(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    threshold: float = 0.10,
    cv: int = 5,
) -> Dict[str, Any]:
    """
    ML-001: Modelo deve superar baseline (regressão linear) em >=10%.
    Retorna dict com scores, baseline, e status.
    """
    baseline = LinearRegression()
    baseline_scores = cross_val_score(baseline, X, y, cv=cv, scoring="r2")
    baseline_mean = np.mean(baseline_scores)

    model_scores = cross_val_score(model, X, y, cv=cv, scoring="r2")
    model_mean = np.mean(model_scores)

    improvement = (model_mean - baseline_mean) / baseline_mean
    passed = improvement >= threshold

    return {
        "invariant": "ML-001",
        "baseline_r2_mean": float(baseline_mean),
        "model_r2_mean": float(model_mean),
        "improvement": float(improvement),
        "threshold": threshold,
        "passed": passed,
    }


# ─── ML-002: Reproducibility Validation ──────────────────────────────────

def validate_ml002(project_root: Path) -> Dict[str, Any]:
    """
    ML-002: Verifica seed fixa, DVC, Docker.
    """
    checks = {
        "dvc_installed": False,
        "dvc_initialized": False,
        "dockerfile_exists": False,
        "docker_compose_exists": False,
        "seed_fixed": False,
    }
    messages = []

    # DVC
    try:
        subprocess.run(["dvc", "--version"], capture_output=True, check=True)
        checks["dvc_installed"] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        messages.append("DVC não instalado ou não encontrado.")

    dvc_dir = project_root / ".dvc"
    if dvc_dir.exists() and dvc_dir.is_dir():
        checks["dvc_initialized"] = True
    else:
        messages.append("DVC não inicializado (diretório .dvc não encontrado).")

    # Docker
    if (project_root / "Dockerfile").exists():
        checks["dockerfile_exists"] = True
    else:
        messages.append("Dockerfile não encontrado na raiz.")

    if (project_root / "docker-compose.yml").exists():
        checks["docker_compose_exists"] = True
    else:
        messages.append("docker-compose.yml não encontrado.")

    # Seed fixa - procurar em arquivos Python
    seed_found = False
    for py_file in project_root.rglob("*.py"):
        try:
            content = py_file.read_text()
            if "random.seed(42)" in content or "np.random.seed(42)" in content or "torch.manual_seed(42)" in content:
                seed_found = True
                break
        except Exception:
            continue
    checks["seed_fixed"] = seed_found
    if not seed_found:
        messages.append("Seed fixa (42) não encontrada em nenhum arquivo Python.")

    passed = all(checks.values())
    return {
        "invariant": "ML-002",
        "checks": checks,
        "messages": messages,
        "passed": passed,
    }


# ─── ML-003: Numerical Precision Validation ─────────────────────────────

def validate_ml003(project_root: Path) -> Dict[str, Any]:
    """
    ML-003: Verifica se há configuração de float64 em simulações quânticas.
    """
    checks = {
        "tensorflow_float64": False,
        "pytorch_float64": False,
        "jax_float64": False,
    }
    messages = []

    # Procurar em arquivos Python por configurações de precisão
    for py_file in project_root.rglob("*.py"):
        try:
            content = py_file.read_text()
            if "tf.float64" in content or "tf.keras.mixed_precision.set_global_policy('float64')" in content:
                checks["tensorflow_float64"] = True
            if "torch.float64" in content or "torch.set_default_dtype(torch.float64)" in content:
                checks["pytorch_float64"] = True
            if "jax.config.update('jax_enable_x64', True)" in content:
                checks["jax_float64"] = True
        except Exception:
            continue

    # Se nenhuma configuração encontrada, emitir aviso
    if not any(checks.values()):
        messages.append("Nenhuma configuração de float64 encontrada para TensorFlow, PyTorch ou JAX.")

    # Pelo menos um framework deve ter float64 configurado
    passed = any(checks.values())
    return {
        "invariant": "ML-003",
        "checks": checks,
        "messages": messages,
        "passed": passed,
    }


# ─── Main CLI ────────────────────────────────────────────────────────────

@click.command()
@click.option("--model-path", type=click.Path(exists=True), help="Caminho para modelo (pickle, joblib, etc.)")
@click.option("--data-path", type=click.Path(exists=True), help="Caminho para dados (CSV, Parquet, etc.)")
@click.option("--project-root", type=click.Path(exists=True), default=".", help="Raiz do projeto para ML-002 e ML-003")
@click.option("--threshold", default=0.10, help="Melhoria mínima para ML-001 (default: 0.10)")
@click.option("--cv", default=5, help="Número de folds para validação cruzada")
@click.option("--output", type=click.Path(), help="Arquivo JSON para salvar o relatório")
def main(model_path, data_path, project_root, threshold, cv, output):
    """
    Valida ML-001, ML-002, ML-003 e gera relatório.
    """
    results = {}
    project_root = Path(project_root).resolve()

    # ML-001: Baseline validation
    if model_path and data_path:
        try:
            # Carregar modelo e dados (exemplo simples)
            # Na prática, adaptar ao formato do projeto
            import joblib
            model = joblib.load(model_path)
            df = pd.read_csv(data_path)
            # Supõe que a última coluna é alvo e as demais são features
            X = df.iloc[:, :-1].values
            y = df.iloc[:, -1].values
            results["ML-001"] = validate_ml001(model, X, y, threshold, cv)
        except Exception as e:
            results["ML-001"] = {
                "invariant": "ML-001",
                "error": str(e),
                "passed": False,
            }
    else:
        results["ML-001"] = {
            "invariant": "ML-001",
            "error": "model-path ou data-path não fornecidos; pulando validação",
            "passed": None,
        }

    # ML-002: Reproducibility
    results["ML-002"] = validate_ml002(project_root)

    # ML-003: Numerical precision
    results["ML-003"] = validate_ml003(project_root)

    # Resumo
    all_passed = all(
        r.get("passed", False) for r in results.values() if r.get("passed") is not None
    )

    summary = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "all_passed": all_passed,
        "details": results,
    }

    # Output
    if output:
        with open(output, "w") as f:
            json.dump(summary, f, indent=2)

    # Print para console
    click.echo("\n" + "=" * 70)
    click.echo("ARKHE — ML Invariants Validation Report")
    click.echo("=" * 70)
    for key, result in results.items():
        status = "✅ PASS" if result.get("passed") else "❌ FAIL" if result.get("passed") is False else "⏭️ SKIP"
        click.echo(f"{key}: {status}")
        if "error" in result:
            click.echo(f"  Error: {result['error']}")
        if "checks" in result:
            for ck, val in result["checks"].items():
                click.echo(f"  {ck}: {'✅' if val else '❌'}")
        if "messages" in result:
            for msg in result["messages"]:
                click.echo(f"  ℹ️ {msg}")
        if "baseline_r2_mean" in result:
            click.echo(f"  Baseline R²: {result['baseline_r2_mean']:.3f}")
            click.echo(f"  Model R²:     {result['model_r2_mean']:.3f}")
            click.echo(f"  Improvement:  {result['improvement']*100:.1f}% (threshold: {result['threshold']*100:.0f}%)")
    click.echo("-" * 70)
    click.echo(f"Overall: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILURES'}")
    click.echo("=" * 70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()