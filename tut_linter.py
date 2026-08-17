#!/usr/bin/env python3
"""
AVALON TUT LINTER (tut_linter.py)
=================================
CI/CD module that validates all TUT-related claims in Avalon documents.
Blocks publication if mathematical inconsistencies are detected.

Invariant: INV-TUT-01, INV-TUT-02, INV-PHI-01, INV-DATA-01, INV-MOCK-01
"""

import numpy as np
import re
from pathlib import Path
from typing import List, Dict, Tuple


class TUTLinter:
    """
    Mathematical linter for Thermodynamic Uncertainty Theorem claims.

    Usage:
        linter = TUTLinter()
        linter.scan_file("document.md")
        if linter.violations:
            linter.report()
            raise SystemExit(1)
    """

    PHI = (1 + np.sqrt(5)) / 2
    ONE_OVER_PHI = 1.0 / PHI

    def __init__(self, tolerance: float = 1e-6):
        self.tolerance = tolerance
        self.violations: List[Dict] = []

    def validate_tut_consistency(self, sigma: float, eps_sq: float, source: str = "unknown") -> bool:
        """Check if Sigma and eps_sq are consistent with TUT."""
        if sigma <= 0:
            self.violations.append({
                'type': 'INVALID_ENTROPY',
                'source': source,
                'message': f'Sigma={sigma} must be positive'
            })
            return False

        eps_computed = 1.0 / np.tanh(sigma / 2.0) - 1.0
        if not np.isclose(eps_computed, eps_sq, rtol=self.tolerance):
            self.violations.append({
                'type': 'TUT_INCONSISTENCY',
                'source': source,
                'sigma_claimed': sigma,
                'eps_sq_claimed': eps_sq,
                'eps_sq_computed': eps_computed,
                'message': (f'Sigma={sigma:.6f} -> eps_sq={eps_computed:.6f}, '
                           f'but claimed {eps_sq:.6f}')
            })
            return False
        return True

    def check_ln3_claim(self, text: str, source: str) -> None:
        """Block S_opt = k_B ln(3) or equivalent."""
        patterns = [
            r'S[_\s]*opt\s*=\s*k[_\s]*B\s*ln\s*\(\s*3\s*\)',
            r'S_opt\s*=\s*k_B\s*ln\s*3',
            r'entropy.*optimal.*ln\s*\(\s*3\s*\)',
            r'ln\s*3.*entropy.*optimal',
        ]
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                self.violations.append({
                    'type': 'FORBIDDEN_LN3',
                    'source': source,
                    'message': 'Forbidden claim: S_opt = k_B ln(3) detected'
                })

    def check_phi_notation(self, text: str, source: str) -> None:
        """Block 1/phi - 1 = 0.618."""
        # Match "1/phi - 1" followed by "= 0.618" or similar
        if re.search(r'1/\s*phi\s*[-−]\s*1\s*=\s*0\.618', text, re.IGNORECASE):
            self.violations.append({
                'type': 'FORBIDDEN_PHI_NOTATION',
                'source': source,
                'message': (f'Forbidden: 1/phi - 1 = 0.618. '
                           f'Correct: 1/phi = {self.ONE_OVER_PHI:.6f}; '
                           f'1/phi - 1 = {self.ONE_OVER_PHI - 1:.6f}')
            })

    def check_hardcoded_arrays(self, text: str, source: str) -> None:
        """Flag suspicious hardcoded arrays that may be fabricated data."""
        # Look for arrays of floats with many decimal places in "computed" contexts
        suspicious = re.findall(
            r'(?:(?:computed|simulated|results?|data)[:]?\s*)?'
            r'\[\s*(\d+\.\d{3,}\s*,\s*){3,}\d+\.\d{3,}\s*\]',
            text, re.IGNORECASE
        )
        if suspicious:
            self.violations.append({
                'type': 'SUSPICIOUS_HARDCODED_ARRAY',
                'source': source,
                'message': f'Hardcoded array with many decimals may be fabricated: {suspicious[0][:80]}'
            })

    def check_mock_misrepresentation(self, text: str, source: str) -> None:
        """Flag mock functions presented without clear labeling."""
        # If text contains "mock" but not "placeholder" or "simulated" near results
        has_mock = re.search(r'\bmock\b', text, re.IGNORECASE)
        has_results = re.search(r'\bresults?\b|\bfinding\b|\bevidence\b', text, re.IGNORECASE)
        has_placeholder = re.search(r'\bplaceholder\b|\bsimulated\b|\bnot\s+physical\b', text, re.IGNORECASE)

        if has_mock and has_results and not has_placeholder:
            self.violations.append({
                'type': 'MOCK_MISREPRESENTATION',
                'source': source,
                'message': 'Mock function may be presented as physical result. Add explicit placeholder label.'
            })

    def scan_file(self, filepath: str) -> None:
        """Scan a single file for violations."""
        path = Path(filepath)
        if not path.exists():
            return

        text = path.read_text(encoding='utf-8')
        source = str(path)

        self.check_ln3_claim(text, source)
        self.check_phi_notation(text, source)
        self.check_hardcoded_arrays(text, source)
        self.check_mock_misrepresentation(text, source)

        # Also check for explicit Sigma/eps_sq pairs
        pairs = re.findall(
            r'Sigma\s*=\s*(\d+\.?\d*)[,:]?\s*eps(?:ilon)?[_\s]?sq\s*=\s*(\d+\.?\d*)',
            text, re.IGNORECASE
        )
        for s, e in pairs:
            self.validate_tut_consistency(float(s), float(e), source)

    def scan_directory(self, dirpath: str, pattern: str = "*.md") -> None:
        """Scan all matching files in directory."""
        for f in Path(dirpath).rglob(pattern):
            self.scan_file(str(f))

    def report(self) -> str:
        """Generate validation report."""
        if not self.violations:
            return "✅ ALL CLAIMS VALIDATED — Publication approved"

        lines = [f"❌ {len(self.violations)} VIOLATION(S) DETECTED — Publication BLOCKED", "=" * 60]
        for i, v in enumerate(self.violations, 1):
            lines.append(f"\n[{i}] {v['type']} in '{v['source']}':")
            lines.append(f"    {v['message']}")
        return "\n".join(lines)

    def exit_code(self) -> int:
        """Return 0 if clean, 1 if violations found."""
        return 1 if self.violations else 0


def main():
    """CLI entry point for CI integration."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Avalon TUT Linter")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument("--pattern", default="*.md", help="File pattern for directories")
    args = parser.parse_args()

    linter = TUTLinter()
    for p in args.paths:
        path = Path(p)
        if path.is_dir():
            linter.scan_directory(str(path), args.pattern)
        else:
            linter.scan_file(str(p))

    print(linter.report())
    sys.exit(linter.exit_code())


if __name__ == "__main__":
    main()
