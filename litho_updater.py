#!/usr/bin/env python3
"""
litho_updater.py — Atualização automática do banco de equipamentos

Busca especificações atualizadas em fontes conhecidas e gera
um equipment_db.json atualizado. Requer review humano antes do merge.

Uso:
  python litho_updater.py --check-all          # Verifica todas as fontes
  python litho_updater.py --diff               # Mostra diff vs banco atual
  python litho_updater.py --generate           # Gera equipment_db.json
  python litho_updater.py --check nanoscribe   # Verifica apenas Nanoscribe
"""

import json
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# FONTES CONHECIDAS (URLs oficiais e mirrors institucionais)
# ============================================================

SOURCES = {
    "nanoscribe": {
        "quantum_x_shape": "https://www.nanoscribe.com/quantum-x-shape",
        "quantum_x_align": "https://www.nanoscribe.com/quantum-x-align",
        "fallback": "https://web.archive.org/web/2025/https://www.nanoscribe.com/quantum-x-shape"
    },
    "upnano": {
        "nanoone_1000": "https://www.upnano.com/nanoone-1000",
        "nanoone_green": "https://www.upnano.com/nanoone-green",
    },
    "heidelberg": {
        "mla150": "https://heidelberg-instruments.com/mla150",
    },
    "raith": {
        "ebpg_5200": "https://raith.com/products/ebpg",
    },
    # Fontes institucionais (nanofabs universitários — dados de uso real)
    "institutional": {
        "stanford_snf_mla150": "https://snf.stanford.edu/equipment/heidelberg-mla150/",
        "ucsb_nanofab_mla150": "https://www.nanofab.ucsb.edu/equipment/heidelberg-mla150",
        "nist_raith": "https://www.nist.gov/laboratories/tools-instruments/raith-electron-beam-lithography-system",
        "upenn_singh_raith": "https://www.seas.upenn.edu/nanofab/equipment/raith-ebpg-5200-plus/",
        "cris_biu_nanoscribe": "https://cris.biu.ac.il/en/publications/quantum-x-shape",
        "umd_nanocenter_upnano": "https://nanocenter.umd.edu/equipment/upnano-nanoone-1000/",
        "cambridge_cavendish_nanoscribe": "https://www.nanofab.phy.cam.ac.uk/equipment/nanoscribe",
    }
}

# ============================================================
# SCHEMA DO BANCO DE DADOS
# ============================================================

@dataclass
class ParameterSpec:
    value: float
    unit: str
    tolerance_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "unit": self.unit, "tolerance_pct": self.tolerance_pct}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ParameterSpec":
        return cls(value=d["value"], unit=d["unit"], tolerance_pct=d["tolerance_pct"])


@dataclass
class EquipmentSpec:
    manufacturer: str
    technology: str
    parameters: Dict[str, ParameterSpec]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manufacturer": self.manufacturer,
            "technology": self.technology,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, name: str, d: Dict[str, Any]) -> "EquipmentSpec":
        return cls(
            manufacturer=d.get("manufacturer", ""),
            technology=d.get("technology", ""),
            parameters={k: ParameterSpec.from_dict(v) for k, v in d.get("parameters", {}).items()},
            metadata=d.get("metadata", {})
        )


# ============================================================
# EXTRATORES DE DADOS (heurísticos — fallback para dados manuais)
# ============================================================

class SpecExtractor:
    """Extrai parâmetros de HTML usando heurísticas."""

    # Padrões comuns em páginas de especificações técnicas
    PATTERNS = {
        "feature_size_xy": re.compile(r'feature\s*size.*xy[^0-9]*([0-9]+)\s*nm', re.I),
        "feature_size_z": re.compile(r'feature\s*size.*z[^0-9]*([0-9]+)\s*nm', re.I),
        "resolution": re.compile(r'resolution[^0-9]*([0-9]+)\s*nm', re.I),
        "spot_size": re.compile(r'spot\s*size[^0-9]*([0-9]+)\s*nm', re.I),
        "scan_speed": re.compile(r'scan\s*speed[^0-9]*([0-9]+\.?[0-9]*)\s*m/s', re.I),
        "writing_speed": re.compile(r'writing\s*speed[^0-9]*([0-9]+\.?[0-9]*)\s*m/s', re.I),
        "wavelength": re.compile(r'wavelength[^0-9]*([0-9]+)\s*nm', re.I),
        "laser_power": re.compile(r'(?:laser\s*)?power[^0-9]*([0-9]+\.?[0-9]*)\s*(?:mW|W)', re.I),
        "throughput": re.compile(r'throughput[^0-9]*([0-9]+)\s*mm³/h', re.I),
        "overlay_accuracy": re.compile(r'overlay[^0-9]*([0-9]+)\s*nm', re.I),
        "alignment_accuracy": re.compile(r'alignment[^0-9]*([0-9]+)\s*nm', re.I),
        "stage_repeatability": re.compile(r'repeatability[^0-9]*([0-9]+)\s*nm', re.I),
        "accelerating_voltage": re.compile(r'(?:accelerating\s*voltage|voltage)[^0-9]*([0-9]+)\s*kV', re.I),
        "beam_current": re.compile(r'beam\s*current[^0-9]*([0-9]+)\s*nA', re.I),
        "min_feature_size": re.compile(r'minimum\s*feature\s*size[^0-9]*([0-9]+\.?[0-9]*)\s*µm', re.I),
    }

    UNIT_MAP = {
        "nm": (1e-9, "m"),
        "µm": (1e-6, "m"),
        "um": (1e-6, "m"),
        "mW": (1e-3, "W"),
        "W": (1.0, "W"),
        "kV": (1e3, "V"),
        "nA": (1e-9, "A"),
        "m/s": (1.0, "m/s"),
        "mm³/h": (1e-9/3600, "m³/s"),
    }

    @classmethod
    def extract_from_html(cls, html: str, source_url: str) -> Dict[str, ParameterSpec]:
        """Tenta extrair parâmetros de HTML. Retorna dict vazio se não conseguir."""
        params: Dict[str, ParameterSpec] = {}
        for param_name, pattern in cls.PATTERNS.items():
            match = pattern.search(html)
            if match:
                raw_value = float(match.group(1))
                # Inferir unidade e converter para SI
                unit_str = match.group(0).split()[-1] if len(match.group(0).split()) > 1 else "nm"
                si_value, si_unit = cls._to_si(raw_value, unit_str)
                params[param_name] = ParameterSpec(
                    value=si_value,
                    unit=si_unit,
                    tolerance_pct=cls._infer_tolerance(param_name)
                )
        return params

    @classmethod
    def _to_si(cls, value: float, unit: str) -> Tuple[float, str]:
        if unit in cls.UNIT_MAP:
            factor, si_unit = cls.UNIT_MAP[unit]
            return value * factor, si_unit
        return value, unit

    @classmethod
    def _infer_tolerance(cls, param_name: str) -> float:
        tolerances = {
            "feature_size_xy": 10, "feature_size_z": 15, "resolution": 10,
            "scan_speed": 10, "writing_speed": 10, "wavelength": 1,
            "laser_power": 10, "throughput": 15, "overlay_accuracy": 10,
            "alignment_accuracy": 10, "stage_repeatability": 10,
            "accelerating_voltage": 5, "beam_current": 10,
            "min_feature_size": 10, "spot_size": 20,
        }
        return tolerances.get(param_name, 10)


def fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    """Busca conteúdo HTML de uma URL."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (LithoVerifier/3.1.0; Research Bot)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP {e.code} em {url}")
        return None
    except Exception as e:
        logger.warning(f"Erro ao buscar {url}: {e}")
        return None


# ============================================================
# BANCO DE DADOS BASE (v3.1.0 — dados verificados manualmente)
# ============================================================

BASE_EQUIPMENT_DB: Dict[str, EquipmentSpec] = {
    "Quantum X Shape": EquipmentSpec(
        manufacturer="Nanoscribe",
        technology="2PP",
        parameters={
            "feature_size_xy": ParameterSpec(100e-9, "m", 10),
            "feature_size_z": ParameterSpec(500e-9, "m", 15),
            "surface_roughness_ra": ParameterSpec(5e-9, "m", 20),
            "shape_accuracy_sa": ParameterSpec(200e-9, "m", 10),
            "scan_speed": ParameterSpec(6.25, "m/s", 10),
            "positioning_volume_xy": ParameterSpec(0.15, "m", 5),
            "positioning_volume_z": ParameterSpec(0.02, "m", 5),
            "stage_repeatability": ParameterSpec(150e-9, "m", 10),
            "wavelength": ParameterSpec(780e-9, "m", 1),
        },
        metadata={"url": "https://www.nanoscribe.com/quantum-x-shape", "last_verified": "2026-08-15", "source": "Nanoscribe official"}
    ),
    "Quantum X Align": EquipmentSpec(
        manufacturer="Nanoscribe",
        technology="2PP",
        parameters={
            "feature_size_xy": ParameterSpec(100e-9, "m", 10),
            "surface_roughness_ra": ParameterSpec(5e-9, "m", 20),
            "shape_accuracy_sa": ParameterSpec(200e-9, "m", 10),
            "scan_speed": ParameterSpec(6.25, "m/s", 10),
            "positioning_volume_xy": ParameterSpec(0.15, "m", 5),
            "positioning_volume_z": ParameterSpec(0.02, "m", 5),
            "stage_repeatability": ParameterSpec(150e-9, "m", 10),
            "wavelength": ParameterSpec(780e-9, "m", 1),
            "alignment_accuracy": ParameterSpec(100e-9, "m", 10),
        },
        metadata={"url": "https://www.nanoscribe.com/quantum-x-align", "last_verified": "2026-08-15", "source": "Nanoscribe official"}
    ),
    "NanoOne 1000": EquipmentSpec(
        manufacturer="UpNano",
        technology="2PP",
        parameters={
            "feature_size_xy": ParameterSpec(170e-9, "m", 10),
            "feature_size_z": ParameterSpec(550e-9, "m", 10),
            "surface_roughness_ra": ParameterSpec(10e-9, "m", 20),
            "throughput": ParameterSpec(450, "mm³/h", 15),
            "writing_speed": ParameterSpec(1.0, "m/s", 10),
            "travel_range_xy": ParameterSpec(0.12, "m", 5),
            "travel_range_z": ParameterSpec(0.049, "m", 5),
            "wavelength": ParameterSpec(780e-9, "m", 1),
            "laser_power": ParameterSpec(1.0, "W", 10),
        },
        metadata={"url": "https://www.upnano.com/nanoone-1000", "last_verified": "2026-08-15", "source": "UpNano official / UMD Nanocenter"}
    ),
    "NanoOne Green": EquipmentSpec(
        manufacturer="UpNano",
        technology="2PP",
        parameters={
            "feature_size_xy": ParameterSpec(200e-9, "m", 10),
            "feature_size_z": ParameterSpec(550e-9, "m", 10),
            "surface_roughness_ra": ParameterSpec(10e-9, "m", 20),
            "throughput": ParameterSpec(450, "mm³/h", 15),
            "writing_speed": ParameterSpec(1.0, "m/s", 10),
            "travel_range_xy": ParameterSpec(0.12, "m", 5),
            "travel_range_z": ParameterSpec(0.049, "m", 5),
            "wavelength": ParameterSpec(515e-9, "m", 1),
            "laser_power": ParameterSpec(0.4, "W", 10),
        },
        metadata={"url": "https://www.upnano.com/nanoone-green", "last_verified": "2026-08-15", "source": "UpNano official"}
    ),
    "Heidelberg MLA150": EquipmentSpec(
        manufacturer="Heidelberg Instruments",
        technology="Maskless",
        parameters={
            "min_feature_size": ParameterSpec(0.45e-6, "m", 10),
            "overlay_accuracy_front": ParameterSpec(250e-9, "m", 10),
            "overlay_accuracy_back": ParameterSpec(500e-9, "m", 10),
            "exposure_area_xy": ParameterSpec(0.15, "m", 5),
            "wavelength_405": ParameterSpec(405e-9, "m", 1),
            "wavelength_375": ParameterSpec(375e-9, "m", 1),
            "write_speed_405": ParameterSpec(1100, "mm²/min", 15),
            "write_speed_375": ParameterSpec(500, "mm²/min", 15),
        },
        metadata={"url": "https://heidelberg-instruments.com/mla150", "last_verified": "2026-08-15", "source": "Heidelberg official / UCSB Nanofab / Stanford SNF", "note": "2025 upgrade: min feature size 0.45 µm"}
    ),
    "Raith EBPG 5200 Plus": EquipmentSpec(
        manufacturer="Raith",
        technology="EBL",
        parameters={
            "resolution": ParameterSpec(8e-9, "m", 10),
            "spot_size": ParameterSpec(2e-9, "m", 20),
            "accelerating_voltage": ParameterSpec(100e3, "V", 5),
            "beam_current_max": ParameterSpec(350e-9, "A", 10),
            "main_field_size": ParameterSpec(1e-3, "m", 5),
            "pattern_generator": ParameterSpec(125e6, "Hz", 5),
            "line_width_min": ParameterSpec(6e-9, "m", 15),
            "overlay_accuracy": ParameterSpec(5e-9, "m", 10),
            "stitching_accuracy": ParameterSpec(8e-9, "m", 10),
        },
        metadata={"url": "https://raith.com/products/ebpg", "last_verified": "2026-08-15", "source": "Raith official / NIST / UPenn Singh Center", "note": "EBPG 5200 Plus: beam current up to 350 nA, overlay ≤ 5 nm"}
    ),
}


# ============================================================
# LÓGICA PRINCIPAL
# ============================================================

class Updater:
    def __init__(self):
        self.current_db = BASE_EQUIPMENT_DB
        self.proposed_changes: List[Tuple[str, str, Any, Any]] = []  # (equip, param, old, new)

    def check_source(self, source_name: str, url: str) -> Optional[Dict[str, ParameterSpec]]:
        """Tenta extrair dados de uma fonte."""
        logger.info(f"🔍 Verificando {source_name}: {url}")
        html = fetch_url(url)
        if html is None:
            return None
        params = SpecExtractor.extract_from_html(html, url)
        if params:
            logger.info(f"  ✓ Extraídos {len(params)} parâmetros")
        else:
            logger.info(f"  ⚠ Nenhum parâmetro extraído (página pode usar JS dinâmico)")
        return params

    def check_all_sources(self) -> Dict[str, Dict[str, ParameterSpec]]:
        """Verifica todas as fontes e retorna propostas de mudança."""
        proposals: Dict[str, Dict[str, ParameterSpec]] = {}
        for vendor, urls in SOURCES.items():
            for page_name, url in urls.items():
                params = self.check_source(f"{vendor}/{page_name}", url)
                if params:
                    # Mapear page_name para nome do equipamento
                    equip_name = self._map_page_to_equipment(page_name)
                    if equip_name:
                        proposals[equip_name] = params
        return proposals

    def _map_page_to_equipment(self, page_name: str) -> Optional[str]:
        mapping = {
            "quantum_x_shape": "Quantum X Shape",
            "quantum_x_align": "Quantum X Align",
            "nanoone_1000": "NanoOne 1000",
            "nanoone_green": "NanoOne Green",
            "mla150": "Heidelberg MLA150",
            "ebpg_5200": "Raith EBPG 5200 Plus",
        }
        return mapping.get(page_name)

    def diff(self, proposals: Dict[str, Dict[str, ParameterSpec]]) -> str:
        """Gera relatório diff entre banco atual e propostas."""
        lines = ["# Relatório de Atualização — Litho Verifier", ""]
        lines.append(f"Gerado em: {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        for equip_name, proposed_params in proposals.items():
            if equip_name not in self.current_db:
                lines.append(f"## ➕ NOVO: {equip_name}")
                lines.append("Equipamento não existe no banco atual.")
                continue

            current = self.current_db[equip_name]
            lines.append(f"## 🔄 {equip_name}")
            has_changes = False

            for param_name, proposed in proposed_params.items():
                if param_name in current.parameters:
                    old = current.parameters[param_name]
                    if abs(old.value - proposed.value) / max(abs(old.value), 1e-15) > 0.01:  # > 1% diff
                        has_changes = True
                        lines.append(f"### ⚠️ {param_name}")
                        lines.append(f"  - Atual:   {old.value} {old.unit} (±{old.tolerance_pct}%)")
                        lines.append(f"  - Proposto: {proposed.value} {proposed.unit} (±{proposed.tolerance_pct}%)")
                        lines.append(f"  - Variação: {abs(old.value - proposed.value)/max(abs(old.value),1e-15)*100:.1f}%")
                        self.proposed_changes.append((equip_name, param_name, old, proposed))
                else:
                    has_changes = True
                    lines.append(f"### ➕ {param_name} (novo)")
                    lines.append(f"  - Proposto: {proposed.value} {proposed.unit} (±{proposed.tolerance_pct}%)")
                    self.proposed_changes.append((equip_name, param_name, None, proposed))

            if not has_changes:
                lines.append("✅ Sem mudanças detectadas.")
            lines.append("")

        # Verificar parâmetros removidos
        for equip_name, current in self.current_db.items():
            if equip_name in proposals:
                for param_name in current.parameters:
                    if param_name not in proposals[equip_name]:
                        lines.append(f"## ⚠️ {equip_name}.{param_name}")
                        lines.append("Parâmetro presente no banco atual mas não encontrado na fonte.")
                        lines.append("")

        return "\n".join(lines)

    def generate_json(self, proposals: Dict[str, Dict[str, ParameterSpec]], output_path: Path) -> None:
        """Gera equipment_db.json com propostas aplicadas (requer review)."""
        db = {}
        for equip_name, spec in self.current_db.items():
            db[equip_name] = spec.to_dict()
            db[equip_name]["metadata"]["last_verified"] = datetime.now(timezone.utc).isoformat()
            db[equip_name]["metadata"]["auto_updated"] = True

        # Aplicar propostas
        for equip_name, params in proposals.items():
            if equip_name in db:
                for param_name, param_spec in params.items():
                    db[equip_name]["parameters"][param_name] = param_spec.to_dict()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        logger.info(f"Banco salvo em: {output_path}")

    def generate_changelog(self, output_path: Path) -> None:
        """Gera CHANGELOG.md com as mudanças propostas."""
        lines = ["# Changelog — Litho Verifier Equipment DB", ""]
        lines.append(f"## [{datetime.now(timezone.utc).strftime('%Y-%m-%d')}]")
        lines.append("")
        for equip, param, old, new in self.proposed_changes:
            if old is None:
                lines.append(f"- **{equip}**: Adicionado parâmetro `{param}` = {new.value} {new.unit}")
            else:
                lines.append(f"- **{equip}.{param}**: {old.value} {old.unit} → {new.value} {new.unit}")
        lines.append("")
        lines.append("---")
        lines.append("⚠️ **REQUER REVISÃO HUMANA ANTES DO MERGE**")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        logger.info(f"Changelog salvo em: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Atualizador automático do banco de equipamentos")
    parser.add_argument("--check-all", action="store_true", help="Verifica todas as fontes")
    parser.add_argument("--check", type=str, metavar="VENDOR", help="Verifica apenas um vendor (nanoscribe, upnano, heidelberg, raith)")
    parser.add_argument("--diff", action="store_true", help="Mostra diff vs banco atual")
    parser.add_argument("--generate", action="store_true", help="Gera equipment_db.json e CHANGELOG.md")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Diretório de saída")
    args = parser.parse_args()

    updater = Updater()

    if args.check_all or args.check:
        if args.check:
            sources = {args.check: SOURCES.get(args.check, {})}
        else:
            sources = SOURCES

        proposals: Dict[str, Dict[str, ParameterSpec]] = {}
        for vendor, urls in sources.items():
            for page_name, url in urls.items():
                params = updater.check_source(f"{vendor}/{page_name}", url)
                if params:
                    equip_name = updater._map_page_to_equipment(page_name)
                    if equip_name:
                        proposals[equip_name] = params

        if args.diff:
            print(updater.diff(proposals))

        if args.generate:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            updater.generate_json(proposals, args.output_dir / "equipment_db.json")
            updater.generate_changelog(args.output_dir / "CHANGELOG_EQUIPMENT.md")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
