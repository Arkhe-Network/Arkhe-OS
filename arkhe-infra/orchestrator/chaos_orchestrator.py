#!/usr/bin/env python3
# orchestrator/chaos_orchestrator.py
import time
import json
import subprocess
import requests
from datetime import datetime
from typing import Dict, List
import boto3
from prometheus_api_client import PrometheusConnect

class ChaosOrchestrator:
    def __init__(self):
        self.prometheus = PrometheusConnect(url="http://prometheus.monitoring:9090", disable_ssl=True)
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        self.experiments = self._load_experiments()
        self.results = []

    def _load_experiments(self) -> List[Dict]:
        return [
            {"name": "gpu-pod-kill", "file": "chaos/gpu-pod-failure.yaml"},
            {"name": "gpu-node-reset", "file": "chaos/gpu-node-failure.yaml"},
            {"name": "gpu-stress-oom", "file": "chaos/gpu-stress-oom.yaml"},
            {"name": "network-partition", "file": "chaos/network-partition.yaml"},
            {"name": "io-failure", "file": "chaos/io-failure.yaml"},
        ]

    def run_experiment(self, experiment: Dict) -> Dict:
        print(f"🧪 Executando experimento: {experiment['name']}")
        start_time = time.time()
        subprocess.run(["kubectl", "apply", "-f", experiment["file"]], capture_output=True, check=True)
        time.sleep(30)
        recovery_metrics = self._collect_metrics(start_time)
        subprocess.run(["kubectl", "delete", "-f", experiment["file"]], capture_output=True, check=True)
        result = {
            "experiment": experiment["name"],
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": time.time() - start_time,
            "recovery_metrics": recovery_metrics
        }
        self.results.append(result)
        return result

    def _collect_metrics(self, start_time: float) -> Dict:
        mttr_query = 'histogram_quantile(0.95, sum(rate(arkhe_mttr_seconds_bucket[5m])) by (le))'
        gpu_failures_query = 'sum(arkhe_gpu_failures_total)'
        coherence_query = 'arkhe_coherence{project_id="global"}'
        mttr = self.prometheus.custom_query(mttr_query)
        gpu_failures = self.prometheus.custom_query(gpu_failures_query)
        coherence = self.prometheus.custom_query(coherence_query)
        return {
            "mttr_seconds": float(mttr[0]['value'][1]) if mttr else None,
            "gpu_failures_detected": float(gpu_failures[0]['value'][1]) if gpu_failures else 0,
            "coherence_post_recovery": float(coherence[0]['value'][1]) if coherence else None,
            "recovery_success": coherence and float(coherence[0]['value'][1]) > 0.90
        }

    def run_suite(self):
        print("🧬 ARKHE(N) — CHAOS ENGINEERING SUITE")
        print("=" * 70)
        for exp in self.experiments:
            result = self.run_experiment(exp)
            print(f"  ✅ {exp['name']}: MTTR={result['recovery_metrics'].get('mttr_seconds', 'N/A')}s")
            self.cloudwatch.put_metric_data(
                Namespace='Arkhe/Chaos',
                MetricData=[{
                    'MetricName': 'MTTR',
                    'Value': result['recovery_metrics'].get('mttr_seconds', 0),
                    'Unit': 'Seconds',
                    'Dimensions': [{'Name': 'Experiment', 'Value': exp['name']}]
                }]
            )
        report = {
            "suite": "Arkhe Chaos Engineering",
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "summary": {
                "total_experiments": len(self.results),
                "successful_recoveries": sum(1 for r in self.results if r['recovery_metrics'].get('recovery_success', False)),
                "average_mttr": sum(r['recovery_metrics'].get('mttr_seconds', 0) for r in self.results) / len(self.results) if self.results else 0
            }
        }
        with open('chaos_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📊 Relatório salvo em chaos_report.json")
        return report

if __name__ == "__main__":
    ChaosOrchestrator().run_suite()