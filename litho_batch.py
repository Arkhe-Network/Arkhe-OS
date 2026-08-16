#!/usr/bin/env python3
"""
litho_batch.py — Processamento em lote de especificações

Uso:
  python litho_batch.py --input-dir ./specs --output-dir ./reports
  python litho_batch.py --input-dir ./specs --watch          # modo daemon
  python litho_batch.py --input-dir ./specs --format json    # apenas JSON
  python litho_batch.py --input-dir ./specs --notify slack   # notificações

Integração CI/CD:
  python litho_batch.py --input-dir ./specs --fail-on-error  # exit code 1 se ERROR
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed

# Importar do litho_verifier
from litho_verifier_v310 import run, to_markdown, DEFAULT_EQUIPMENT_DB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    file: str
    status: str  # ok | warning | error
    n_claims: int
    n_validations: int
    confirmed: int
    warning: int
    error: int
    unverifiable: int
    report_path: Optional[str] = None
    error_msg: Optional[str] = None


def process_file(file_path: Path, output_dir: Path, output_formats: List[str]) -> BatchResult:
    """Processa um único arquivo de especificação."""
    try:
        report = run(file_path)
        md = to_markdown(report)

        base_name = file_path.stem
        report_paths = []

        if "json" in output_formats:
            json_path = output_dir / f"{base_name}.json"
            json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            report_paths.append(str(json_path))

        if "markdown" in output_formats:
            md_path = output_dir / f"{base_name}.md"
            md_path.write_text(md, encoding="utf-8")
            report_paths.append(str(md_path))

        counts = report["status_counts"]
        status = "error" if counts["ERROR"] > 0 else "warning" if counts["WARNING"] > 0 else "ok"

        return BatchResult(
            file=str(file_path),
            status=status,
            n_claims=report["n_claims"],
            n_validations=report["n_validations"],
            confirmed=counts["CONFIRMED"],
            warning=counts["WARNING"],
            error=counts["ERROR"],
            unverifiable=counts["UNVERIFIABLE"],
            report_path=report_paths[0] if report_paths else None
        )

    except Exception as e:
        logger.error(f"Erro ao processar {file_path}: {e}")
        return BatchResult(
            file=str(file_path),
            status="error",
            n_claims=0,
            n_validations=0,
            confirmed=0,
            warning=0,
            error=1,
            unverifiable=0,
            error_msg=str(e)
        )


def process_batch(
    input_dir: Path,
    output_dir: Path,
    output_formats: List[str],
    max_workers: int = 4,
    equipment_file: Optional[Path] = None
) -> List[BatchResult]:
    """Processa todos os arquivos em um diretório."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Encontrar arquivos
    extensions = {".md", ".txt", ".spec"}
    files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() in extensions]

    if not files:
        logger.warning(f"Nenhum arquivo encontrado em {input_dir}")
        return []

    logger.info(f"Processando {len(files)} arquivo(s) com {max_workers} worker(s)...")

    results: List[BatchResult] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, f, output_dir, output_formats): f for f in files}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            emoji = "✅" if result.status == "ok" else "⚠️" if result.status == "warning" else "❌"
            logger.info(f"{emoji} {result.file} — C:{result.confirmed} W:{result.warning} E:{result.error}")

    return results


def generate_summary(results: List[BatchResult], output_dir: Path) -> None:
    """Gera relatório consolidado do batch."""
    total_confirmed = sum(r.confirmed for r in results)
    total_warning = sum(r.warning for r in results)
    total_error = sum(r.error for r in results)
    total_unverifiable = sum(r.unverifiable for r in results)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(results),
        "total_ok": sum(1 for r in results if r.status == "ok"),
        "total_warning": sum(1 for r in results if r.status == "warning"),
        "total_error": sum(1 for r in results if r.status == "error"),
        "total_confirmed": total_confirmed,
        "total_warnings": total_warning,
        "total_errors": total_error,
        "total_unverifiable": total_unverifiable,
        "results": [asdict(r) for r in results]
    }

    summary_path = output_dir / "_batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown summary
    md_lines = [
        "# Relatório de Processamento em Lote",
        "",
        f"**Gerado em:** {summary['generated_at']}",
        f"**Arquivos processados:** {summary['total_files']}",
        "",
        "## Resumo",
        f"- ✅ OK: {summary['total_ok']}",
        f"- ⚠️ Com avisos: {summary['total_warning']}",
        f"- ❌ Com erros: {summary['total_error']}",
        "",
        "## Estatísticas de Validação",
        f"- ✅ CONFIRMED: {total_confirmed}",
        f"- ⚠️ WARNING: {total_warning}",
        f"- ❌ ERROR: {total_error}",
        f"- 🔍 UNVERIFIABLE: {total_unverifiable}",
        "",
        "## Detalhamento por Arquivo",
        "",
        "| Arquivo | Status | C | W | E | U |",
        "|---------|--------|---|---|---|---|",
    ]

    for r in results:
        status_emoji = "✅" if r.status == "ok" else "⚠️" if r.status == "warning" else "❌"
        md_lines.append(f"| {Path(r.file).name} | {status_emoji} | {r.confirmed} | {r.warning} | {r.error} | {r.unverifiable} |")

    md_lines.append("")
    md_lines.append("---")
    md_lines.append("*Relatório gerado automaticamente pelo Litho Verifier Batch Processor v3.1.0*")

    md_path = output_dir / "_batch_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    logger.info(f"Resumo salvo em: {summary_path} e {md_path}")


def watch_mode(input_dir: Path, output_dir: Path, output_formats: List[str], interval: int = 30):
    """Modo daemon: observa diretório e processa novos arquivos."""
    logger.info(f"👁️ Modo watch ativado: {input_dir} (intervalo: {interval}s)")
    processed: set = set()

    while True:
        extensions = {".md", ".txt", ".spec"}
        current_files = {f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() in extensions}
        new_files = current_files - processed

        if new_files:
            logger.info(f"📥 {len(new_files)} novo(s) arquivo(s) detectado(s)")
            for f in new_files:
                result = process_file(f, output_dir, output_formats)
                processed.add(f)
                if result.status == "error":
                    logger.error(f"❌ Erro em {f.name}: {result.error_msg}")

            # Regenerar summary
            all_results = [process_file(f, output_dir, output_formats) for f in processed]
            generate_summary(all_results, output_dir)

        time.sleep(interval)


def notify_slack(webhook_url: str, results: List[BatchResult]) -> None:
    """Envia notificação para Slack."""
    try:
        import urllib.request
        total_error = sum(1 for r in results if r.status == "error")
        total_warning = sum(1 for r in results if r.status == "warning")

        color = "danger" if total_error > 0 else "warning" if total_warning > 0 else "good"
        payload = {
            "attachments": [{
                "color": color,
                "title": "Litho Verifier — Processamento em Lote",
                "text": f"{len(results)} arquivo(s) processado(s). ❌ {total_error} erro(s), ⚠️ {total_warning} aviso(s).",
                "footer": "Litho Verifier v3.1.0",
                "ts": int(datetime.now(timezone.utc).timestamp())
            }]
        }
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
        logger.info("Notificação Slack enviada.")
    except Exception as e:
        logger.warning(f"Erro ao notificar Slack: {e}")


def main():
    parser = argparse.ArgumentParser(description="Processamento em lote de especificações de litografia")
    parser.add_argument("--input-dir", type=Path, required=True, help="Diretório com arquivos de especificação")
    parser.add_argument("--output-dir", type=Path, default=Path("./reports"), help="Diretório de saída")
    parser.add_argument("--format", type=str, default="json,markdown", help="Formatos de saída (json,markdown)")
    parser.add_argument("--workers", type=int, default=4, help="Número de workers paralelos")
    parser.add_argument("--watch", action="store_true", help="Modo daemon (observa diretório)")
    parser.add_argument("--interval", type=int, default=30, help="Intervalo de polling no modo watch (segundos)")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit code 1 se houver erros")
    parser.add_argument("--notify-slack", type=str, help="Webhook URL do Slack para notificações")
    parser.add_argument("--equipment", type=Path, help="Arquivo JSON com equipamentos personalizados")
    args = parser.parse_args()

    if not args.input_dir.exists():
        logger.error(f"Diretório não encontrado: {args.input_dir}")
        sys.exit(1)

    output_formats = [f.strip() for f in args.format.split(",")]

    if args.watch:
        watch_mode(args.input_dir, args.output_dir, output_formats, args.interval)
    else:
        results = process_batch(args.input_dir, args.output_dir, output_formats, args.workers, args.equipment)
        generate_summary(results, args.output_dir)

        if args.notify_slack:
            notify_slack(args.notify_slack, results)

        total_errors = sum(1 for r in results if r.status == "error")
        if args.fail_on_error and total_errors > 0:
            logger.error(f"❌ {total_errors} arquivo(s) com erro. Falhando.")
            sys.exit(1)

        logger.info(f"✅ Processamento concluído. {len(results)} arquivo(s).")


if __name__ == "__main__":
    main()
