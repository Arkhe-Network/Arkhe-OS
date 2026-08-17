#!/usr/bin/env python3
"""
litho_api.py — FastAPI backend para litho_verifier v3.1.0

Endpoints:
  POST /validate         → valida texto ou arquivo
  POST /validate/file    → upload de arquivo
  GET  /health           → healthcheck
  GET  /                 → interface HTML
"""

import json
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Importar do litho_verifier (deve estar no mesmo diretório)
from litho_verifier_v310 import (
    run, to_markdown, load_equipment_db, DEFAULT_EQUIPMENT_DB,
    EquipmentProfile, cross_validate_parameters, extract_all_parameters,
    identify_equipment, format_value_si
)

app = FastAPI(
    title="Litho Verifier API",
    description="Validação automática de especificações de litografia 3D",
    version="3.1.0"
)


class ValidateRequest(BaseModel):
    text: str
    equipment_db: Optional[dict] = None
    tolerances: Optional[dict] = None
    output_format: str = "json"  # json | markdown


class ValidateResponse(BaseModel):
    status: str
    report: dict
    markdown: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=HTML_INTERFACE, status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.1.0", "equipment_count": len(DEFAULT_EQUIPMENT_DB)}


@app.post("/validate")
async def validate(request: ValidateRequest):
    """Valida texto inline."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(request.text)
            tmp_path = Path(f.name)

        # Se equipment_db customizado fornecido, salvar temporariamente
        equip_file = None
        if request.equipment_db:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
                json.dump(request.equipment_db, f)
                equip_file = Path(f.name)

        tol_file = None
        if request.tolerances:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
                json.dump(request.tolerances, f)
                tol_file = Path(f.name)

        report = run(tmp_path, equip_file, tol_file)
        md = to_markdown(report)

        tmp_path.unlink(missing_ok=True)
        if equip_file:
            equip_file.unlink(missing_ok=True)
        if tol_file:
            tol_file.unlink(missing_ok=True)

        if request.output_format == "markdown":
            return PlainTextResponse(content=md, media_type="text/markdown")
        return JSONResponse(content={"status": "ok", "report": report, "markdown": md})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate/file")
async def validate_file(
    file: UploadFile = File(...),
    output_format: str = Form("json"),
    equipment_file: Optional[UploadFile] = File(None)
):
    """Valida arquivo uploadado."""
    try:
        suffix = Path(file.filename).suffix if file.filename else ".txt"
        with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as f:
            content = await file.read()
            f.write(content)
            tmp_path = Path(f.name)

        equip_path = None
        if equipment_file:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False) as f:
                f.write(await equipment_file.read())
                equip_path = Path(f.name)

        report = run(tmp_path, equip_path)
        md = to_markdown(report)

        tmp_path.unlink(missing_ok=True)
        if equip_path:
            equip_path.unlink(missing_ok=True)

        if output_format == "markdown":
            return PlainTextResponse(content=md, media_type="text/markdown")
        return JSONResponse(content={"status": "ok", "report": report, "markdown": md})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/equipment")
async def list_equipment():
    """Lista equipamentos disponíveis."""
    return {
        "equipment": [
            {
                "name": name,
                "manufacturer": data.get("manufacturer", ""),
                "technology": data.get("technology", ""),
                "parameters": list(data.get("parameters", {}).keys()),
                "metadata": data.get("metadata", {})
            }
            for name, data in DEFAULT_EQUIPMENT_DB.items()
        ]
    }


# ============================================================
# INTERFACE HTML EMBUTIDA
# ============================================================

HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Litho Verifier v3.1.0</title>
    <style>
        :root {
            --bg: #0d1117; --fg: #c9d1d9; --accent: #58a6ff;
            --card: #161b22; --border: #30363d; --ok: #238636;
            --warn: #9e6a03; --err: #da3633;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background: var(--bg); color: var(--fg); line-height: 1.6;
            min-height: 100vh; padding: 2rem;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; color: var(--accent); }
        .subtitle { color: #8b949e; margin-bottom: 2rem; }
        .card {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
        }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .tab {
            padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;
            background: var(--border); border: none; color: var(--fg);
            font-size: 0.9rem; transition: all 0.2s;
        }
        .tab.active { background: var(--accent); color: #fff; }
        .tab:hover:not(.active) { background: #30363d; }
        textarea, input[type="file"] {
            width: 100%; background: var(--bg); color: var(--fg);
            border: 1px solid var(--border); border-radius: 8px;
            padding: 0.75rem; font-family: "SF Mono", Monaco, monospace;
            font-size: 0.85rem; resize: vertical;
        }
        textarea { min-height: 200px; }
        button[type="submit"] {
            background: var(--ok); color: #fff; border: none;
            padding: 0.75rem 1.5rem; border-radius: 8px;
            font-size: 1rem; cursor: pointer; margin-top: 1rem;
            transition: opacity 0.2s;
        }
        button[type="submit"]:hover { opacity: 0.85; }
        .output {
            background: var(--bg); border: 1px solid var(--border);
            border-radius: 8px; padding: 1rem; margin-top: 1rem;
            font-family: "SF Mono", monospace; font-size: 0.8rem;
            white-space: pre-wrap; max-height: 600px; overflow-y: auto;
            display: none;
        }
        .output.show { display: block; }
        .badge {
            display: inline-block; padding: 0.25rem 0.5rem;
            border-radius: 4px; font-size: 0.75rem; font-weight: 600;
            margin-right: 0.5rem;
        }
        .badge.ok { background: rgba(35,134,54,0.2); color: #3fb950; }
        .badge.warn { background: rgba(158,106,3,0.2); color: #d29922; }
        .badge.err { background: rgba(218,54,51,0.2); color: #f85149; }
        .stats { display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .stat-box {
            background: var(--bg); border: 1px solid var(--border);
            border-radius: 8px; padding: 0.75rem 1rem; flex: 1; min-width: 120px;
        }
        .stat-box .number { font-size: 1.5rem; font-weight: 700; }
        .stat-box .label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; }
        .loading { display: none; color: var(--accent); margin-top: 1rem; }
        .loading.show { display: block; }
        .hidden { display: none; }
        #drop-zone {
            border: 2px dashed var(--border); border-radius: 12px;
            padding: 2rem; text-align: center; cursor: pointer;
            transition: all 0.2s; margin-bottom: 1rem;
        }
        #drop-zone.dragover { border-color: var(--accent); background: rgba(88,166,255,0.05); }
        #file-input { display: none; }
        .filename { color: var(--accent); margin-top: 0.5rem; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 Litho Verifier</h1>
        <p class="subtitle">Validação automática de especificações de litografia 3D — v3.1.0</p>

        <div class="card">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('text')">📄 Texto</button>
                <button class="tab" onclick="switchTab('file')">📁 Arquivo</button>
            </div>

            <form id="form-text" onsubmit="submitText(event)">
                <textarea id="input-text" placeholder="Cole aqui as especificações técnicas...

Exemplo:
Quantum X Shape: feature_size_xy = 100 nm
scan_speed: 6.25 m/s"></textarea>
                <button type="submit">Validar Especificações</button>
            </form>

            <form id="form-file" class="hidden" onsubmit="submitFile(event)">
                <div id="drop-zone" onclick="document.getElementById('file-input').click()">
                    <p>📂 Arraste um arquivo ou clique para selecionar</p>
                    <p style="color:#8b949e;font-size:0.8rem;margin-top:0.5rem;">.md, .txt, .spec</p>
                    <p class="filename" id="filename"></p>
                </div>
                <input type="file" id="file-input" accept=".md,.txt,.spec" onchange="fileSelected(event)">
                <button type="submit">Validar Arquivo</button>
            </form>

            <div class="loading" id="loading">⏳ Processando...</div>

            <div class="output" id="output"></div>
        </div>

        <div class="card">
            <h3 style="margin-bottom:1rem;">📊 Estatísticas do Banco</h3>
            <div class="stats" id="stats">
                <div class="stat-box"><div class="number" id="stat-equip">6</div><div class="label">Equipamentos</div></div>
                <div class="stat-box"><div class="number" id="stat-params">—</div><div class="label">Parâmetros</div></div>
                <div class="stat-box"><div class="number" id="stat-status">✅</div><div class="label">API Status</div></div>
            </div>
            <p style="font-size:0.8rem;color:#8b949e;">
                Banco atualizado em: 2026-08-15 | Fontes: Nanoscribe, UpNano, Heidelberg Instruments, Raith
            </p>
        </div>
    </div>

    <script>
        let currentFile = null;

        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('form-text').classList.toggle('hidden', tab !== 'text');
            document.getElementById('form-file').classList.toggle('hidden', tab !== 'file');
            document.getElementById('output').classList.remove('show');
        }

        function fileSelected(e) {
            currentFile = e.target.files[0];
            document.getElementById('filename').textContent = currentFile ? currentFile.name : '';
        }

        // Drag & drop
        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', e => {
            e.preventDefault(); dropZone.classList.remove('dragover');
            currentFile = e.dataTransfer.files[0];
            document.getElementById('filename').textContent = currentFile.name;
        });

        async function submitText(e) {
            e.preventDefault();
            const text = document.getElementById('input-text').value;
            if (!text.trim()) return alert('Cole o texto das especificações.');
            await doValidate('/validate', { text, output_format: 'json' });
        }

        async function submitFile(e) {
            e.preventDefault();
            if (!currentFile) return alert('Selecione um arquivo.');
            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('output_format', 'json');
            await doValidate('/validate/file', formData, true);
        }

        async function doValidate(url, body, isForm = false) {
            document.getElementById('loading').classList.add('show');
            document.getElementById('output').classList.remove('show');
            try {
                const opts = isForm ? { method: 'POST', body } : {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                };
                const res = await fetch(url, opts);
                const data = await res.json();
                renderOutput(data.report);
            } catch (err) {
                document.getElementById('output').textContent = 'Erro: ' + err.message;
                document.getElementById('output').classList.add('show');
            } finally {
                document.getElementById('loading').classList.remove('show');
            }
        }

        function renderOutput(report) {
            const out = document.getElementById('output');
            const counts = report.status_counts;
            let html = `<div style="margin-bottom:1rem;">`;
            html += `<span class="badge ok">✅ CONFIRMED: ${counts.CONFIRMED}</span>`;
            html += `<span class="badge warn">⚠️ WARNING: ${counts.WARNING}</span>`;
            html += `<span class="badge err">❌ ERROR: ${counts.ERROR}</span>`;
            html += `<span class="badge" style="background:rgba(139,148,158,0.2);color:#8b949e;">🔍 UNVERIFIABLE: ${counts.UNVERIFIABLE}</span>`;
            html += `</div>`;
            html += `<div style="color:#8b949e;font-size:0.75rem;margin-bottom:1rem;">`;
            html += `${report.n_claims} afirmações analisadas | ${report.n_validations} validações | ${report.generated_at_utc}</div>`;
            html += `<hr style="border-color:var(--border);margin:1rem 0;">`;

            for (const r of report.validation_results) {
                const emoji = r.status === 'CONFIRMED' ? '✅' : r.status === 'WARNING' ? '⚠️' : r.status === 'ERROR' ? '❌' : '🔍';
                const color = r.status === 'CONFIRMED' ? '#3fb950' : r.status === 'WARNING' ? '#d29922' : r.status === 'ERROR' ? '#f85149' : '#8b949e';
                html += `<div style="margin-bottom:1rem;padding:0.75rem;border-left:3px solid ${color};background:rgba(255,255,255,0.02);border-radius:0 6px 6px 0;">`;
                html += `<strong style="color:${color}">${emoji} ${r.equipment || 'N/I'} — ${r.param_name}</strong><br>`;
                html += `<span style="color:#8b949e;font-size:0.8rem;">${r.claim}</span><br>`;
                html += `<span style="font-size:0.8rem;">${r.detail}</span><br>`;
                html += `<span style="font-size:0.75rem;color:#58a6ff;">${r.rationale}</span>`;
                html += `</div>`;
            }
            out.innerHTML = html;
            out.classList.add('show');
        }

        // Carregar stats
        fetch('/health').then(r => r.json()).then(d => {
            document.getElementById('stat-equip').textContent = d.equipment_count;
            document.getElementById('stat-status').textContent = d.status === 'ok' ? '✅' : '❌';
        });
        fetch('/equipment').then(r => r.json()).then(d => {
            const total = d.equipment.reduce((s, e) => s + e.parameters.length, 0);
            document.getElementById('stat-params').textContent = total;
        });
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
