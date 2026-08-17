#!/usr/bin/env python3
"""
litho_verifier.py  —  v3.1.0

Validador de especificações técnicas para máquinas de litografia 3D.

CHANGELOG v3.1.0:
  - FIX NP1: EquipmentProfile.from_dict converte valor esperado para SI
  - FIX NP2: Aliases ASCII para mm3/h, mm2/min, mm3/s, mm2/s
  - FIX NP3: Regex usa grupos nomeados (evita nomes com dígito inicial)
  - FIX NP4: Schema validation completo para JSON externo
  - FIX NP5: split_claims threshold >= 3; teste ajustado
  - FIX NP6: format_value_si com prefixos métricos corretos
  - FIX NP7: diff_pct arredondado para evitar erro de ponto flutuante
  - NEW: Banco de dados atualizado com especificações reais 2025-2026
  - NEW: Suporte a parâmetros com underscore e espaço intercambiáveis
  - NEW: Fallback de identificação de equipamento por palavras-chave
  - NEW: Tolerâncias personalizáveis via JSON externo (--tolerances)
  - NEW: Parâmetros adicionais de CTP/MES/prensas (cP, bar, L/min, °C)
"""

import re
import json
import argparse
import logging
import unittest
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any, Union

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# UNIDADES E CONVERSÃO (SI)
# ============================================================

UNIT_ALIASES: Dict[str, float] = {
    # Comprimento (SI: metro)
    "nm": 1e-9, "µm": 1e-6, "um": 1e-6, "μm": 1e-6,
    "mm": 1e-3, "cm": 1e-2, "m": 1.0, "km": 1e3,
    # Potência (SI: watt)
    "W": 1.0, "mW": 1e-3, "kW": 1e3,
    # Tempo (SI: segundo)
    "fs": 1e-15, "ps": 1e-12, "ns": 1e-9,
    "µs": 1e-6, "us": 1e-6, "ms": 1e-3, "s": 1.0,
    # Frequência (SI: hertz)
    "Hz": 1.0, "MHz": 1e6, "GHz": 1e9,
    # Corrente (SI: ampere)
    "nA": 1e-9, "µA": 1e-6, "mA": 1e-3, "A": 1.0,
    # Tensão (SI: volt)
    "kV": 1e3, "V": 1.0, "mV": 1e-3,
    # Compostas (superscript + ASCII)
    "mm³/h": 1e-9 / 3600, "mm3/h": 1e-9 / 3600,
    "mm³/s": 1e-9, "mm3/s": 1e-9,
    "mm²/min": 1e-6 / 60, "mm2/min": 1e-6 / 60,
    "mm²/s": 1e-6, "mm2/s": 1e-6,
    "mm/s": 1e-3, "m/s": 1.0,
    # CTP / MES / Prensas
    "cP": 1e-3, "°C": 1.0, "bar": 1e5, "psi": 6894.76,
    "m/min": 1 / 60, "L/min": 1 / 60000, "N/m": 1.0,
}

NUMERIC_RE = re.compile(r'([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)')
PARAM_NAME_RE = re.compile(r'[^\W\d_]\w*')


def normalize_to_si(value: float, unit: str) -> float:
    """Converte valor+unidade para SI."""
    if not unit:
        return value
    unit_clean = unit.strip().replace(" ", "").replace("μ", "µ")
    unit_clean = unit_clean.replace("²", "2").replace("³", "3")
    if unit_clean in UNIT_ALIASES:
        return value * UNIT_ALIASES[unit_clean]
    unit_lower = unit_clean.lower()
    for key, factor in UNIT_ALIASES.items():
        if key.lower() == unit_lower:
            return value * factor
    raise ValueError(f"Unidade desconhecida: '{unit}'")


def safe_float(s: Union[str, None]) -> Optional[float]:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _metric_prefix(value: float, unit: str) -> Tuple[float, str]:
    """Retorna (valor_escalado, prefixo) para a unidade base."""
    if not unit:
        return value, ""
    if unit in ("Hz",):
        if value >= 1e9: return value / 1e9, "G"
        elif value >= 1e6: return value / 1e6, "M"
        elif value >= 1e3: return value / 1e3, "k"
        return value, ""
    if unit in ("W",):
        if value >= 1e3: return value / 1e3, "k"
        elif value >= 1: return value, ""
        elif value >= 1e-3: return value * 1e3, "m"
        elif value >= 1e-6: return value * 1e6, "µ"
        return value * 1e9, "n"
    base = unit.replace("/s", "").replace("/min", "").replace("/h", "")
    if base in ("m", "mm", "µm", "nm", "cm", "km"):
        if value >= 1e3: return value / 1e3, "k"
        elif value >= 1: return value, ""
        elif value >= 1e-3: return value * 1e3, "m"
        elif value >= 1e-6: return value * 1e6, "µ"
        elif value >= 1e-9: return value * 1e9, "n"
        return value * 1e12, "p"
    return value, ""


def format_value_si(value: float, original_unit: Optional[str] = None) -> str:
    """Formata valor SI de volta para a unidade original com prefixos métricos."""
    if original_unit:
        try:
            factor = UNIT_ALIASES.get(original_unit)
            if factor is not None:
                raw_value = value / factor
                scaled, prefix = _metric_prefix(raw_value, original_unit)
                display_unit = prefix + original_unit
                return f"{scaled:.3g} {display_unit}"
        except (KeyError, ValueError):
            pass
    abs_val = abs(value)
    if abs_val >= 1e-2:
        if abs_val >= 1e3: return f"{value/1e3:.3g} km"
        return f"{value:.3g} m"
    elif abs_val >= 1e-5: return f"{value*1e3:.3g} mm"
    elif abs_val >= 1e-8: return f"{value*1e6:.3g} µm"
    else: return f"{value*1e9:.3g} nm"


# ============================================================
# BANCO DE DADOS ATUALIZADO (2025-2026)
# ============================================================

DEFAULT_EQUIPMENT_DB: Dict[str, Dict[str, Any]] = {
    "Quantum X Shape": {
        "manufacturer": "Nanoscribe", "technology": "2PP",
        "parameters": {
            "feature_size_xy": {"value": 100e-9, "unit": "m", "tolerance_pct": 10},
            "feature_size_z": {"value": 500e-9, "unit": "m", "tolerance_pct": 15},
            "surface_roughness_ra": {"value": 5e-9, "unit": "m", "tolerance_pct": 20},
            "shape_accuracy_sa": {"value": 200e-9, "unit": "m", "tolerance_pct": 10},
            "scan_speed": {"value": 6.25, "unit": "m/s", "tolerance_pct": 10},
            "positioning_volume_xy": {"value": 0.15, "unit": "m", "tolerance_pct": 5},
            "positioning_volume_z": {"value": 0.02, "unit": "m", "tolerance_pct": 5},
            "stage_repeatability": {"value": 150e-9, "unit": "m", "tolerance_pct": 10},
            "wavelength": {"value": 780e-9, "unit": "m", "tolerance_pct": 1},
        },
        "metadata": {"url": "https://www.nanoscribe.com/quantum-x-shape", "last_verified": "2026-08-15"}
    },
    "Quantum X Align": {
        "manufacturer": "Nanoscribe", "technology": "2PP",
        "parameters": {
            "feature_size_xy": {"value": 100e-9, "unit": "m", "tolerance_pct": 10},
            "surface_roughness_ra": {"value": 5e-9, "unit": "m", "tolerance_pct": 20},
            "shape_accuracy_sa": {"value": 200e-9, "unit": "m", "tolerance_pct": 10},
            "scan_speed": {"value": 6.25, "unit": "m/s", "tolerance_pct": 10},
            "positioning_volume_xy": {"value": 0.15, "unit": "m", "tolerance_pct": 5},
            "positioning_volume_z": {"value": 0.02, "unit": "m", "tolerance_pct": 5},
            "stage_repeatability": {"value": 150e-9, "unit": "m", "tolerance_pct": 10},
            "wavelength": {"value": 780e-9, "unit": "m", "tolerance_pct": 1},
            "alignment_accuracy": {"value": 100e-9, "unit": "m", "tolerance_pct": 10},
        },
        "metadata": {"url": "https://www.nanoscribe.com/quantum-x-align", "last_verified": "2026-08-15"}
    },
    "NanoOne 1000": {
        "manufacturer": "UpNano", "technology": "2PP",
        "parameters": {
            "feature_size_xy": {"value": 170e-9, "unit": "m", "tolerance_pct": 10},
            "feature_size_z": {"value": 550e-9, "unit": "m", "tolerance_pct": 10},
            "surface_roughness_ra": {"value": 10e-9, "unit": "m", "tolerance_pct": 20},
            "throughput": {"value": 450, "unit": "mm³/h", "tolerance_pct": 15},
            "writing_speed": {"value": 1.0, "unit": "m/s", "tolerance_pct": 10},
            "travel_range_xy": {"value": 0.12, "unit": "m", "tolerance_pct": 5},
            "travel_range_z": {"value": 0.049, "unit": "m", "tolerance_pct": 5},
            "wavelength": {"value": 780e-9, "unit": "m", "tolerance_pct": 1},
            "laser_power": {"value": 1.0, "unit": "W", "tolerance_pct": 10},
        },
        "metadata": {"url": "https://www.upnano.com/nanoone-1000", "last_verified": "2026-08-15", "source": "UpNano official / UMD Nanocenter"}
    },
    "NanoOne Green": {
        "manufacturer": "UpNano", "technology": "2PP",
        "parameters": {
            "feature_size_xy": {"value": 200e-9, "unit": "m", "tolerance_pct": 10},
            "feature_size_z": {"value": 550e-9, "unit": "m", "tolerance_pct": 10},
            "surface_roughness_ra": {"value": 10e-9, "unit": "m", "tolerance_pct": 20},
            "throughput": {"value": 450, "unit": "mm³/h", "tolerance_pct": 15},
            "writing_speed": {"value": 1.0, "unit": "m/s", "tolerance_pct": 10},
            "travel_range_xy": {"value": 0.12, "unit": "m", "tolerance_pct": 5},
            "travel_range_z": {"value": 0.049, "unit": "m", "tolerance_pct": 5},
            "wavelength": {"value": 515e-9, "unit": "m", "tolerance_pct": 1},
            "laser_power": {"value": 0.4, "unit": "W", "tolerance_pct": 10},
        },
        "metadata": {"url": "https://www.upnano.com/nanoone-green", "last_verified": "2026-08-15"}
    },
    "Heidelberg MLA150": {
        "manufacturer": "Heidelberg Instruments", "technology": "Maskless",
        "parameters": {
            "min_feature_size": {"value": 0.45e-6, "unit": "m", "tolerance_pct": 10},
            "overlay_accuracy_front": {"value": 250e-9, "unit": "m", "tolerance_pct": 10},
            "overlay_accuracy_back": {"value": 500e-9, "unit": "m", "tolerance_pct": 10},
            "exposure_area_xy": {"value": 0.15, "unit": "m", "tolerance_pct": 5},
            "wavelength_405": {"value": 405e-9, "unit": "m", "tolerance_pct": 1},
            "wavelength_375": {"value": 375e-9, "unit": "m", "tolerance_pct": 1},
            "write_speed_405": {"value": 1100, "unit": "mm²/min", "tolerance_pct": 15},
            "write_speed_375": {"value": 500, "unit": "mm²/min", "tolerance_pct": 15},
        },
        "metadata": {"url": "https://heidelberg-instruments.com/mla150", "last_verified": "2026-08-15", "source": "Heidelberg official / UCSB Nanofab / Stanford SNF", "note": "2025 upgrade: min feature size 0.45 µm"}
    },
    "Raith EBPG 5200 Plus": {
        "manufacturer": "Raith", "technology": "EBL",
        "parameters": {
            "resolution": {"value": 8e-9, "unit": "m", "tolerance_pct": 10},
            "spot_size": {"value": 2e-9, "unit": "m", "tolerance_pct": 20},
            "accelerating_voltage": {"value": 100e3, "unit": "V", "tolerance_pct": 5},
            "beam_current_max": {"value": 350e-9, "unit": "A", "tolerance_pct": 10},
            "main_field_size": {"value": 1e-3, "unit": "m", "tolerance_pct": 5},
            "pattern_generator": {"value": 125e6, "unit": "Hz", "tolerance_pct": 5},
            "line_width_min": {"value": 6e-9, "unit": "m", "tolerance_pct": 15},
            "overlay_accuracy": {"value": 5e-9, "unit": "m", "tolerance_pct": 10},
            "stitching_accuracy": {"value": 8e-9, "unit": "m", "tolerance_pct": 10},
        },
        "metadata": {"url": "https://raith.com/products/ebpg", "last_verified": "2026-08-15", "source": "Raith official / NIST / UPenn Singh Center", "note": "EBPG 5200 Plus: beam current up to 350 nA, overlay ≤ 5 nm"}
    }
}


# ============================================================
# SCHEMA VALIDATION (NP4)
# ============================================================

def _validate_equipment_schema(data: Dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        logger.warning("Raiz do JSON não é um dicionário")
        return False
    for name, profile in data.items():
        if not isinstance(profile, dict):
            logger.warning(f"Perfil de '{name}' não é um dicionário")
            return False
        if "parameters" not in profile:
            logger.warning(f"Perfil '{name}' sem campo 'parameters'")
            return False
        params = profile["parameters"]
        if not isinstance(params, dict):
            logger.warning(f"Parâmetros de '{name}' não são um dicionário")
            return False
        for pname, pdata in params.items():
            if not isinstance(pdata, dict):
                logger.warning(f"Dados de '{pname}' em '{name}' não são um dicionário")
                return False
            for field_name in ("value", "unit", "tolerance_pct"):
                if field_name not in pdata:
                    logger.warning(f"Parâmetro '{pname}' em '{name}' faltando '{field_name}'")
                    return False
            if not isinstance(pdata["value"], (int, float)):
                logger.warning(f"Valor de '{pname}' em '{name}' não é numérico")
                return False
            if not isinstance(pdata["tolerance_pct"], (int, float)):
                logger.warning(f"Tolerância de '{pname}' em '{name}' não é numérica")
                return False
    return True


def load_equipment_db(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    if path and path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and _validate_equipment_schema(data):
                logger.info(f"Carregados {len(data)} equipamentos de {path}")
                return data
            else:
                logger.warning(f"JSON de equipamentos inválido (schema). Usando defaults.")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Erro ao carregar {path}: {e}. Usando defaults.")
    return DEFAULT_EQUIPMENT_DB


def load_tolerances(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    if path and path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                logger.info(f"Tolerâncias carregadas de {path}")
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Erro ao carregar tolerâncias: {e}. Usando defaults.")
    return {}


# ============================================================
# MODELOS DE DADOS
# ============================================================

@dataclass
class EquipmentProfile:
    name: str
    manufacturer: str
    technology: str
    parameters: Dict[str, Tuple[float, str, float]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "EquipmentProfile":
        params: Dict[str, Tuple[float, str, float]] = {}
        for pname, pdata in data.get("parameters", {}).items():
            raw_value = pdata["value"]
            unit = pdata["unit"]
            try:
                si_value = normalize_to_si(raw_value, unit)
            except ValueError as e:
                logger.warning(f"Erro ao converter {pname} ({raw_value} {unit}) para SI: {e}")
                si_value = float(raw_value)
            params[pname] = (si_value, unit, pdata["tolerance_pct"])
        return cls(
            name=name,
            manufacturer=data.get("manufacturer", "Desconhecido"),
            technology=data.get("technology", "Desconhecida"),
            parameters=params,
            metadata=data.get("metadata", {})
        )


@dataclass
class CrossValidationResult:
    param_name: str
    declared_value: float
    declared_unit: str
    declared_si: float
    expected_value: float
    expected_unit: str
    expected_si: float
    tolerance_pct: float
    status: str
    detail: str


# ============================================================
# PARSER DE PARÂMETROS (NP3 corrigido com grupos nomeados)
# ============================================================

def extract_all_parameters(text: str) -> List[Tuple[str, float, str]]:
    """Extrai parâmetros no formato nome: valor unidade."""
    results: List[Tuple[str, float, str]] = []
    # Grupos nomeados para todos os campos — imunes a mudanças na regex
    pattern = re.compile(
        r'(?<![\w])(?P<name>[^\W\d_]\w*)\s*[:=<>≤≥]\s*(?P<value>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(?P<unit>[a-zA-Zµμ/³²0-9]+)?',
        re.IGNORECASE
    )
    for m in pattern.finditer(text):
        raw_name = m.group("name")
        value_str = m.group("value")
        unit = m.group("unit") if m.group("unit") else ""
        value = safe_float(value_str)
        if value is not None:
            results.append((raw_name, value, unit))
    return results


def identify_equipment(text: str, equipment_db: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Identifica equipamento pelo nome completo ou palavras-chave."""
    text_lower = text.lower()
    for name in equipment_db.keys():
        if name.lower() in text_lower:
            return name
    keywords = {
        "quantum x shape": "Quantum X Shape",
        "quantum x align": "Quantum X Align",
        "nanoone 1000": "NanoOne 1000",
        "nanoone green": "NanoOne Green",
        "mla150": "Heidelberg MLA150",
        "mla 150": "Heidelberg MLA150",
        "ebpg 5200": "Raith EBPG 5200 Plus",
        "ebpg5200": "Raith EBPG 5200 Plus",
    }
    for kw, equip_name in keywords.items():
        if kw in text_lower:
            return equip_name
    return None


# ============================================================
# VALIDAÇÃO CRUZADA
# ============================================================

def cross_validate_parameters(
    declared: List[Tuple[str, float, str]],
    profile: EquipmentProfile,
    tolerance_config: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[CrossValidationResult]:
    if tolerance_config is None:
        tolerance_config = {}
    results: List[CrossValidationResult] = []
    for param_name, declared_val, declared_unit in declared:
        matched_name = None
        for p in profile.parameters.keys():
            if p == param_name or p.replace('_', ' ') == param_name or p == param_name.replace('_', ' '):
                matched_name = p
                break
        if matched_name is None:
            continue

        expected_si, expected_unit, tol_pct = profile.parameters[matched_name]
        if matched_name in tolerance_config:
            tol_pct = tolerance_config[matched_name].get("tolerance_pct", tol_pct)

        try:
            declared_si = normalize_to_si(declared_val, declared_unit)
        except ValueError as e:
            results.append(CrossValidationResult(
                param_name=matched_name,
                declared_value=declared_val,
                declared_unit=declared_unit,
                declared_si=float('nan'),
                expected_value=expected_si,
                expected_unit=expected_unit,
                expected_si=expected_si,
                tolerance_pct=tol_pct,
                status="ERROR",
                detail=f"Unidade inválida: {e}"
            ))
            continue

        if math.isnan(declared_si) or math.isinf(declared_si):
            status = "ERROR"
            detail = "Valor declarado inválido (NaN ou Inf)"
        else:
            # NP7: arredondar diff_pct para evitar erro de ponto flutuante
            diff_pct = round(abs(declared_si - expected_si) / max(abs(expected_si), 1e-15) * 100, 10)
            if diff_pct <= tol_pct:
                status = "CONFIRMED"
                detail = f"Diferença de {diff_pct:.1f}% (tolerância ±{tol_pct}%)"
            elif diff_pct <= tol_pct * 2:
                status = "WARNING"
                detail = f"Diferença de {diff_pct:.1f}% (tolerância ±{tol_pct}%) — fora da especificação"
            else:
                status = "ERROR"
                detail = f"Diferença de {diff_pct:.1f}% (tolerância ±{tol_pct}%) — significativamente fora"

        results.append(CrossValidationResult(
            param_name=matched_name,
            declared_value=declared_val,
            declared_unit=declared_unit,
            declared_si=declared_si,
            expected_value=expected_si,
            expected_unit=expected_unit,
            expected_si=expected_si,
            tolerance_pct=tol_pct,
            status=status,
            detail=detail
        ))
    return results


# ============================================================
# DIVISÃO DE AFIRMAÇÕES (NP5)
# ============================================================

_UNIT_PATTERN = '|'.join(re.escape(u) for u in sorted(UNIT_ALIASES.keys(), key=len, reverse=True))
_SPEC_PATTERN = re.compile(rf"[:=<>≤≥]\s*[\d.eE+-]+\s*(?:{_UNIT_PATTERN})", re.IGNORECASE)
_UNIT_VALUE_PATTERN = re.compile(rf"[\d.eE+-]+\s*(?:{_UNIT_PATTERN})", re.IGNORECASE)


def split_claims(text: str) -> List[str]:
    lines = text.splitlines()
    claims: List[str] = []
    buf: List[str] = []

    def flush():
        if buf:
            para = " ".join(buf).strip()
            if para:
                for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", para):
                    sent = sent.strip()
                    if len(sent.split()) >= 3:
                        claims.append(sent)
            buf.clear()

    for line in lines:
        raw = line.strip()
        if not raw:
            flush()
            continue
        if re.match(r"^\s*(def |fn |let |import |from |class |```)", raw):
            flush()
            continue
        if _SPEC_PATTERN.search(raw) or _UNIT_VALUE_PATTERN.search(raw):
            flush()
            claims.append(raw)
            continue
        buf.append(raw)
    flush()
    return claims


# ============================================================
# ORQUESTRAÇÃO PRINCIPAL
# ============================================================

def run(path: Path, equipment_file: Optional[Path] = None, tolerance_file: Optional[Path] = None) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    if not path.is_file():
        raise ValueError(f"Caminho não é um arquivo: {path}")

    logger.info(f"Processando: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    equipment_db = load_equipment_db(equipment_file)
    tolerance_config = load_tolerances(tolerance_file)

    claims = split_claims(text)
    validation_results: List[Dict[str, Any]] = []

    current_equipment = None
    for idx, claim in enumerate(claims):
        identified_eq = identify_equipment(claim, equipment_db)
        if identified_eq:
            current_equipment = identified_eq

        equipment = current_equipment
        params = extract_all_parameters(claim)

        if not equipment:
            for p, v, u in params:
                validation_results.append({
                    "idx": idx,
                    "claim": claim,
                    "equipment": None,
                    "param_name": p,
                    "extracted_value": v,
                    "extracted_unit": u,
                    "status": "UNVERIFIABLE",
                    "detail": "Equipamento não identificado",
                    "rationale": "Não foi possível identificar o equipamento."
                })
            continue

        profile = EquipmentProfile.from_dict(equipment, equipment_db[equipment])
        cross_results = cross_validate_parameters(params, profile, tolerance_config)

        for cr in cross_results:
            declared_str = format_value_si(cr.declared_si, cr.declared_unit) if cr.declared_unit else f"{cr.declared_value}"
            expected_str = format_value_si(cr.expected_si, cr.expected_unit)
            validation_results.append({
                "idx": idx,
                "claim": claim,
                "equipment": equipment,
                "param_name": cr.param_name,
                "extracted_value": cr.declared_value,
                "extracted_unit": cr.declared_unit,
                "expected_value": cr.expected_si,
                "expected_unit": cr.expected_unit,
                "status": cr.status,
                "detail": cr.detail,
                "rationale": f"Declarado: {declared_str}, Esperado: {expected_str} (±{cr.tolerance_pct}%)"
            })

    status_counts = {"CONFIRMED": 0, "WARNING": 0, "ERROR": 0, "UNVERIFIABLE": 0}
    for r in validation_results:
        status_counts[r["status"]] += 1

    return {
        "source_file": str(path),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_claims": len(claims),
        "n_validations": len(validation_results),
        "status_counts": status_counts,
        "validation_results": validation_results,
        "limitations": [
            "Validação baseada em perfis de equipamentos pré-definidos.",
            "Unidades devem estar explícitas no texto.",
            "Equipamentos e tolerâncias podem ser carregados de JSON externo.",
        ],
    }


def to_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Relatório de Validação — " + str(Path(report['source_file']).name))
    lines.append("\nGerado em: " + report['generated_at_utc'])
    lines.append("\nAfirmações analisadas: **" + str(report['n_claims']) + "**")
    lines.append("Validações realizadas: **" + str(report['n_validations']) + "**")
    lines.append("\n## Distribuição de Status")
    emojis = {"CONFIRMED": "✅", "WARNING": "⚠️", "ERROR": "❌", "UNVERIFIABLE": "🔍"}
    for status, count in report["status_counts"].items():
        lines.append("- " + emojis.get(status, "❓") + " **" + status + "**: " + str(count))
    lines.append("\n## Detalhamento")
    for r in report["validation_results"]:
        emoji = emojis.get(r["status"], "❓")
        equip_str = "[" + r['equipment'] + "]" if r["equipment"] else "[N/I]"
        lines.append("\n### " + emoji + " " + equip_str + " `" + r['param_name'] + "` — " + r['status'])
        lines.append("> " + r['claim'])
        if r["extracted_value"] is not None:
            lines.append("  - Extraído: " + str(r['extracted_value']) + " " + str(r['extracted_unit'] or ''))
        lines.append("  - " + r['detail'])
        lines.append("  - " + r['rationale'])
    lines.append("\n## Limitações")
    for lim in report["limitations"]:
        lines.append("- " + lim)
    return "\n".join(lines)


# ============================================================
# TESTES UNITÁRIOS
# ============================================================

class TestLithoVerifier(unittest.TestCase):

    def test_normalize_to_si(self):
        self.assertAlmostEqual(normalize_to_si(200, "nm"), 200e-9)
        self.assertAlmostEqual(normalize_to_si(1.5, "µm"), 1.5e-6)
        self.assertAlmostEqual(normalize_to_si(4, "W"), 4.0)
        self.assertAlmostEqual(normalize_to_si(100, "kV"), 100e3)
        self.assertAlmostEqual(normalize_to_si(125e6, "Hz"), 125e6)
        with self.assertRaises(ValueError):
            normalize_to_si(5, "unknown")

    def test_normalize_compound_units(self):
        self.assertAlmostEqual(normalize_to_si(450, "mm³/h"), 450 * 1e-9 / 3600)
        self.assertAlmostEqual(normalize_to_si(450, "mm3/h"), 450 * 1e-9 / 3600)
        self.assertAlmostEqual(normalize_to_si(1100, "mm²/min"), 1100 * 1e-6 / 60)
        self.assertAlmostEqual(normalize_to_si(1100, "mm2/min"), 1100 * 1e-6 / 60)

    def test_safe_float(self):
        self.assertEqual(safe_float("3.14"), 3.14)
        self.assertEqual(safe_float("1.2.3"), None)
        self.assertEqual(safe_float("."), None)
        self.assertEqual(safe_float(None), None)
        self.assertEqual(safe_float("1e-3"), 1e-3)

    def test_extract_all_parameters_i18n(self):
        text = "resolução: 200 nm, potência: 4 W"
        params = extract_all_parameters(text)
        self.assertEqual(len(params), 2)
        names = [p[0] for p in params]
        self.assertIn("resolução", names)
        self.assertIn("potência", names)
        for name, value, unit in params:
            if name == "resolução":
                self.assertEqual(value, 200.0)
                self.assertEqual(unit, "nm")
            elif name == "potência":
                self.assertEqual(value, 4.0)
                self.assertEqual(unit, "W")

    def test_extract_parameters_no_digit_start(self):
        text = "123param: 200 nm"
        params = extract_all_parameters(text)
        self.assertEqual(len(params), 0)
        text2 = "1st_layer: 100 nm"
        params2 = extract_all_parameters(text2)
        self.assertEqual(len(params2), 0)

    def test_extract_scientific_notation(self):
        text = "comprimento: 1.55e-6 m"
        params = extract_all_parameters(text)
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0][1], 1.55e-6)
        self.assertEqual(params[0][2], "m")

    def test_extract_multiple_params(self):
        text = "resolução: 200 nm, potência: 4 W, frequência: 125 MHz"
        params = extract_all_parameters(text)
        self.assertEqual(len(params), 3)
        names = [p[0] for p in params]
        self.assertIn("resolução", names)
        self.assertIn("potência", names)
        self.assertIn("frequência", names)

    def test_identify_equipment(self):
        db = DEFAULT_EQUIPMENT_DB
        self.assertEqual(identify_equipment("Nanoscribe Quantum X Shape", db), "Quantum X Shape")
        self.assertEqual(identify_equipment("UpNano NanoOne 1000", db), "NanoOne 1000")
        self.assertEqual(identify_equipment("Heidelberg MLA150", db), "Heidelberg MLA150")
        self.assertEqual(identify_equipment("Raith EBPG 5200 Plus", db), "Raith EBPG 5200 Plus")
        self.assertEqual(identify_equipment("ebpg5200 system", db), "Raith EBPG 5200 Plus")
        self.assertIsNone(identify_equipment("unknown device", db))

    def test_cross_validate_confirmed(self):
        profile = EquipmentProfile.from_dict("Quantum X Shape", DEFAULT_EQUIPMENT_DB["Quantum X Shape"])
        declared = [("feature_size_xy", 100, "nm")]
        results = cross_validate_parameters(declared, profile)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "CONFIRMED")

    def test_cross_validate_warning(self):
        profile = EquipmentProfile.from_dict("Quantum X Shape", DEFAULT_EQUIPMENT_DB["Quantum X Shape"])
        # 120 nm está a 20% de 100 nm; tolerância 10% → WARNING (20% <= 2×10%)
        declared = [("feature_size_xy", 120, "nm")]
        results = cross_validate_parameters(declared, profile)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "WARNING")

    def test_cross_validate_error(self):
        profile = EquipmentProfile.from_dict("Quantum X Shape", DEFAULT_EQUIPMENT_DB["Quantum X Shape"])
        # 150 nm está a 50% de 100 nm; tolerância 10% → ERROR (> 20%)
        declared = [("feature_size_xy", 150, "nm")]
        results = cross_validate_parameters(declared, profile)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "ERROR")

    def test_cross_validate_unit_conversion(self):
        profile = EquipmentProfile.from_dict("NanoOne 1000", DEFAULT_EQUIPMENT_DB["NanoOne 1000"])
        declared = [("throughput", 450, "mm³/h")]
        results = cross_validate_parameters(declared, profile)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "CONFIRMED")
        self.assertAlmostEqual(results[0].declared_si, 450 * 1e-9 / 3600, delta=1e-10)
        self.assertAlmostEqual(results[0].expected_si, 450 * 1e-9 / 3600, delta=1e-10)

    def test_cross_validate_ascii_unit(self):
        profile = EquipmentProfile.from_dict("NanoOne 1000", DEFAULT_EQUIPMENT_DB["NanoOne 1000"])
        declared = [("throughput", 450, "mm3/h")]
        results = cross_validate_parameters(declared, profile)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "CONFIRMED")

    def test_cross_validate_external_tolerance(self):
        profile = EquipmentProfile.from_dict("Quantum X Shape", DEFAULT_EQUIPMENT_DB["Quantum X Shape"])
        declared = [("feature_size_xy", 120, "nm")]
        tolerance_config = {"feature_size_xy": {"tolerance_pct": 25}}
        results = cross_validate_parameters(declared, profile, tolerance_config)
        self.assertEqual(results[0].status, "CONFIRMED")
        results2 = cross_validate_parameters(declared, profile, {})
        self.assertEqual(results2[0].status, "WARNING")

    def test_split_claims(self):
        text = "resolução: 200 nm\npotência: 4 W\nEsta frase tem quatro palavras."
        claims = split_claims(text)
        self.assertEqual(len(claims), 3)
        self.assertIn("resolução: 200 nm", claims[0])
        self.assertIn("potência: 4 W", claims[1])
        self.assertIn("Esta frase tem quatro palavras", claims[2])

    def test_format_value_si(self):
        self.assertEqual(format_value_si(200e-9, "nm"), "200 nm")
        self.assertEqual(format_value_si(1.5e-6, "µm"), "1.5 µm")
        self.assertEqual(format_value_si(4.0, "W"), "4 W")
        self.assertEqual(format_value_si(125e6, "Hz"), "125 MHz")
        self.assertEqual(format_value_si(2.4e9, "Hz"), "2.4 GHz")
        self.assertEqual(format_value_si(500e3, "Hz"), "500 kHz")
        self.assertEqual(format_value_si(0.4, "W"), "400 mW")

    def test_from_dict_conversion(self):
        data = {
            "parameters": {
                "throughput": {"value": 450, "unit": "mm³/h", "tolerance_pct": 15}
            }
        }
        profile = EquipmentProfile.from_dict("Test", data)
        si_val, unit, tol = profile.parameters["throughput"]
        self.assertAlmostEqual(si_val, 450 * 1e-9 / 3600)
        self.assertEqual(unit, "mm³/h")
        self.assertEqual(tol, 15)

    def test_schema_validation(self):
        bad_data = {"Equipamento X": {"foo": "bar"}}
        self.assertFalse(_validate_equipment_schema(bad_data))
        good_data = {
            "Equipamento Y": {
                "manufacturer": "Test",
                "technology": "T",
                "parameters": {
                    "p1": {"value": 1.0, "unit": "m", "tolerance_pct": 5}
                }
            }
        }
        self.assertTrue(_validate_equipment_schema(good_data))

    def test_equipment_db_updated(self):
        self.assertIn("Raith EBPG 5200 Plus", DEFAULT_EQUIPMENT_DB)
        self.assertEqual(DEFAULT_EQUIPMENT_DB["Raith EBPG 5200 Plus"]["parameters"]["beam_current_max"]["value"], 350e-9)
        self.assertEqual(DEFAULT_EQUIPMENT_DB["Heidelberg MLA150"]["parameters"]["min_feature_size"]["value"], 0.45e-6)


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestLithoVerifier)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Validador de especificações para litografia 3D v3.1.0"
    )
    parser.add_argument("path", type=Path, nargs="?", help="Arquivo .md/.txt com especificações")
    parser.add_argument("--json-out", type=Path, help="Salvar relatório em JSON")
    parser.add_argument("--md-out", type=Path, help="Salvar relatório em Markdown")
    parser.add_argument("--equipment", type=Path, help="Arquivo JSON com equipamentos personalizados")
    parser.add_argument("--tolerances", type=Path, help="Arquivo JSON com tolerâncias personalizadas")
    parser.add_argument("--test", action="store_true", help="Executar testes unitários")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verbose (logging DEBUG)")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.test:
        result = run_tests()
        sys.exit(0 if result.wasSuccessful() else 1)

    if not args.path:
        parser.error("o seguinte argumento é necessário: path (use --test para executar testes)")

    try:
        report = run(args.path, args.equipment, args.tolerances)
    except FileNotFoundError as e:
        logger.error(f"Arquivo não encontrado: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Erro de validação: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Erro inesperado: {e}")
        sys.exit(1)

    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.md_out:
        args.md_out.write_text(to_markdown(report), encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(to_markdown(report))


if __name__ == "__main__":
    main()
