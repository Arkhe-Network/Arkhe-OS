#!/usr/bin/env python3
"""
ARKHE — ML-001 Baseline Validator
Integração com score-crates.py para validação de modelos ML

Uso:
    python ml001_baseline_validator.py --model-path model.pt \\
        --dataset data/perovskites.csv --task regression

Invariante: ML-001 — "Validação Contra Baseline Estatístico"
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, f1_score
from scipy import stats


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASELINE_IMPROVEMENT_THRESHOLD = 1.10  # 10% de melhoria mínima
P_VALUE_THRESHOLD = 0.05
CV_FOLDS = 5
RANDOM_STATE = 42


@dataclass
class ValidationResult:
    """Resultado da validação ML-001."""
    invariant_id: str = "ML-001"
    passed: bool = False
    baseline_model: str = ""
    proposed_model: str = ""
    metric_name: str = ""
    baseline_score: float = 0.0
    proposed_score: float = 0.0
    improvement_ratio: float = 0.0
    p_value: float = 1.0
    std_baseline: float = 0.0
    std_proposed: float = 0.0
    details: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ML001BaselineValidator:
    """
    Validador do Invariante ML-001.

    Verifica se um modelo proposto supera um baseline estatístico
    (Random Forest / XGBoost) em pelo menos 10% com significância
    estatística (p < 0.05).
    """

    def __init__(self, task: str = "regression", metric: str = "r2"):
        self.task = task
        self.metric = metric
        self.results: List[ValidationResult] = []

    def _get_baseline_model(self):
        """Retorna o modelo baseline apropriado para a tarefa."""
        if self.task == "regression":
            return RandomForestRegressor(
                n_estimators=500,
                max_depth=None,
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
        elif self.task == "classification":
            return RandomForestClassifier(
                n_estimators=500,
                max_depth=None,
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Tarefa '{self.task}' não suportada. Use 'regression' ou 'classification'.")

    def _score_model(self, model, X: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
        """Calcula score médio e desvio padrão via cross-validation."""
        if self.task == "regression":
            cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
            scoring = self.metric  # 'r2', 'neg_mean_squared_error', 'neg_mean_absolute_error'
        else:
            cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
            scoring = self.metric  # 'f1', 'accuracy', 'roc_auc'

        scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)
        return scores.mean(), scores.std()

    def _paired_t_test(self, baseline_scores: np.ndarray, proposed_scores: np.ndarray) -> float:
        """Teste t pareado para comparar dois conjuntos de scores."""
        _, p_value = stats.ttest_rel(proposed_scores, baseline_scores)
        return p_value

    def validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        proposed_model,
        proposed_name: str = "proposed_model",
        baseline_model=None,
        baseline_name: str = "RandomForest"
    ) -> ValidationResult:
        """
        Valida o modelo proposto contra baseline.

        Args:
            X: Features (n_samples, n_features)
            y: Targets (n_samples,)
            proposed_model: Modelo proposto (sklearn-compatible ou callable)
            proposed_name: Nome do modelo proposto
            baseline_model: Modelo baseline (default: RandomForest)
            baseline_name: Nome do baseline

        Returns:
            ValidationResult com resultado da validação
        """
        print(f"\n{'='*60}")
        print(f"ARKHE ML-001 — Validação de Baseline")
        print(f"{'='*60}")
        print(f"Tarefa: {self.task}")
        print(f"Métrica: {self.metric}")
        print(f"Baseline: {baseline_name}")
        print(f"Proposto: {proposed_name}")
        print(f"Amostras: {X.shape[0]} | Features: {X.shape[1]}")
        print(f"{'='*60}")

        # Baseline
        if baseline_model is None:
            baseline_model = self._get_baseline_model()

        print(f"\n[1/4] Treinando baseline ({baseline_name})...")
        baseline_mean, baseline_std = self._score_model(baseline_model, X, y)
        print(f"      Score: {baseline_mean:.4f} ± {baseline_std:.4f}")

        # Proposto
        print(f"\n[2/4] Avaliando modelo proposto ({proposed_name})...")
        proposed_mean, proposed_std = self._score_model(proposed_model, X, y)
        print(f"      Score: {proposed_mean:.4f} ± {proposed_std:.4f}")

        # Melhoria
        print(f"\n[3/4] Calculando melhoria...")
        if self.metric in ["neg_mean_squared_error", "neg_mean_absolute_error"]:
            # Métricas negativas: menor (mais negativo) é pior, então invertemos
            improvement = baseline_mean / proposed_mean if proposed_mean != 0 else float('inf')
        else:
            # Métricas positivas: maior é melhor
            improvement = proposed_mean / baseline_mean if baseline_mean != 0 else float('inf')

        print(f"      Melhoria: {improvement:.2%}")
        print(f"      Threshold: {BASELINE_IMPROVEMENT_THRESHOLD:.2%}")

        # Teste t pareado (usando predições em holdout para p-value)
        print(f"\n[4/4] Teste de significância estatística...")
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y if self.task == "classification" else None
        )

        baseline_model.fit(X_train, y_train)
        proposed_model.fit(X_train, y_train)

        y_pred_baseline = baseline_model.predict(X_test)
        y_pred_proposed = proposed_model.predict(X_test)

        if self.task == "regression":
            baseline_scores = np.array([r2_score(y_test, y_pred_baseline)])
            proposed_scores = np.array([r2_score(y_test, y_pred_proposed)])
        else:
            baseline_scores = np.array([f1_score(y_test, y_pred_baseline, average='weighted')])
            proposed_scores = np.array([f1_score(y_test, y_pred_proposed, average='weighted')])

        # Para teste t pareado precisamos de múltiplas amostras — usamos bootstrap
        n_bootstrap = 100
        baseline_boot = []
        proposed_boot = []
        rng = np.random.RandomState(RANDOM_STATE)
        for _ in range(n_bootstrap):
            idx = rng.randint(0, len(y_test), len(y_test))
            if self.task == "regression":
                baseline_boot.append(r2_score(y_test[idx], y_pred_baseline[idx]))
                proposed_boot.append(r2_score(y_test[idx], y_pred_proposed[idx]))
            else:
                baseline_boot.append(f1_score(y_test[idx], y_pred_baseline[idx], average='weighted'))
                proposed_boot.append(f1_score(y_test[idx], y_pred_proposed[idx], average='weighted'))

        p_value = self._paired_t_test(np.array(baseline_boot), np.array(proposed_boot))
        print(f"      p-value: {p_value:.4f} (threshold: {P_VALUE_THRESHOLD})")

        # Verificação final
        passed = (improvement >= BASELINE_IMPROVEMENT_THRESHOLD) and (p_value < P_VALUE_THRESHOLD)

        result = ValidationResult(
            invariant_id="ML-001",
            passed=passed,
            baseline_model=baseline_name,
            proposed_model=proposed_name,
            metric_name=self.metric,
            baseline_score=baseline_mean,
            proposed_score=proposed_mean,
            improvement_ratio=improvement,
            p_value=p_value,
            std_baseline=baseline_std,
            std_proposed=proposed_std,
            details="APROVADO" if passed else "REJEITADO",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S")
        )

        self.results.append(result)

        print(f"\n{'='*60}")
        print(f"RESULTADO: {result.details}")
        print(f"{'='*60}")
        if passed:
            print(f"✅ Modelo proposto SUPERA baseline em {improvement:.2%}")
            print(f"✅ Significância estatística confirmada (p={p_value:.4f})")
        else:
            if improvement < BASELINE_IMPROVEMENT_THRESHOLD:
                print(f"❌ Melhoria ({improvement:.2%}) abaixo do threshold ({BASELINE_IMPROVEMENT_THRESHOLD:.2%})")
            if p_value >= P_VALUE_THRESHOLD:
                print(f"❌ Diferença não é estatisticamente significativa (p={p_value:.4f})")
        print(f"{'='*60}")

        return result

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Gera relatório JSON da validação."""
        report = {
            "invariant": "ML-001",
            "validator": "ARKHE Baseline Validator v1.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "thresholds": {
                "improvement_ratio": BASELINE_IMPROVEMENT_THRESHOLD,
                "p_value": P_VALUE_THRESHOLD,
                "cv_folds": CV_FOLDS
            },
            "results": [r.to_dict() for r in self.results]
        }

        json_str = json.dumps(report, indent=2)

        if output_path:
            Path(output_path).write_text(json_str)
            print(f"\n📄 Relatório salvo: {output_path}")

        return json_str


# ============================================================
# INTEGRAÇÃO COM score-crates.py
# ============================================================

def score_ml_model(
    model_path: str,
    dataset_path: str,
    task: str = "regression",
    metric: str = "r2",
    output_report: Optional[str] = None
) -> float:
    """
    Função de integração com score-crates.py.

    Retorna um score de 0-100 baseado na conformidade com ML-001.
    Pode ser usada como métrica de qualidade no pipeline de scoring.

    Args:
        model_path: Caminho para o modelo proposto (pickle/joblib/torch)
        dataset_path: Caminho para o dataset de validação (CSV)
        task: 'regression' ou 'classification'
        metric: Métrica de avaliação
        output_report: Caminho para salvar relatório JSON

    Returns:
        Score de 0-100 (100 = ML-001 totalmente satisfeito)
    """
    import pandas as pd

    # Carregar dados
    df = pd.read_csv(dataset_path)
    # Assumir que a última coluna é o target
    X = df.iloc[:, :-1].values
    y = df.iloc[:, -1].values

    # Carregar modelo proposto (placeholder — adaptar para formato real)
    # Para sklearn:
    import joblib
    proposed_model = joblib.load(model_path)

    # Validar
    validator = ML001BaselineValidator(task=task, metric=metric)
    result = validator.validate(X, y, proposed_model, proposed_name=Path(model_path).stem)

    if output_report:
        validator.generate_report(output_report)

    # Calcular score (0-100)
    if result.passed:
        score = 100.0
    else:
        # Score proporcional à melhoria (máx 90 se não passar no p-value)
        improvement_score = min(result.improvement_ratio / BASELINE_IMPROVEMENT_THRESHOLD, 1.0) * 90
        p_value_penalty = 0 if result.p_value < P_VALUE_THRESHOLD else 10
        score = max(0, improvement_score - p_value_penalty)

    print(f"\n🏛️ ARKHE ML-001 Score: {score:.1f}/100")
    return score


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="ARKHE ML-001 Baseline Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Validação de regressão
  python ml001_baseline_validator.py --model-path model.pkl \\
      --dataset data/perovskites.csv --task regression --metric r2

  # Validação de classificação
  python ml001_baseline_validator.py --model-path classifier.pkl \\
      --dataset data/stability.csv --task classification --metric f1

  # Com relatório JSON
  python ml001_baseline_validator.py --model-path model.pkl \\
      --dataset data/perovskites.csv --report ml001_report.json
        """
    )
    parser.add_argument("--model-path", required=True, help="Caminho para o modelo proposto")
    parser.add_argument("--dataset-path", required=True, help="Caminho para o dataset (CSV)")
    parser.add_argument("--task", default="regression", choices=["regression", "classification"])
    parser.add_argument("--metric", default="r2", help="Métrica de avaliação (r2, f1, etc.)")
    parser.add_argument("--report", help="Caminho para salvar relatório JSON")
    parser.add_argument("--score-only", action="store_true", help="Retornar apenas score numérico")

    args = parser.parse_args()

    score = score_ml_model(
        model_path=args.model_path,
        dataset_path=args.dataset_path,
        task=args.task,
        metric=args.metric,
        output_report=args.report
    )

    if args.score_only:
        print(score)
        sys.exit(0 if score >= 90 else 1)


if __name__ == "__main__":
    main()