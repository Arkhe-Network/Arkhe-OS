# Quality Gates and ASI-Grade Verification Strategy v2.0

## Tools Required
- `cargo-llvm-cov`
- `cargo-insta`
- `cargo-deny`
- `cargo-audit`
- `cargo-semver-checks`

## Installation
```bash
cargo install cargo-llvm-cov cargo-insta cargo-deny cargo-audit cargo-semver-checks
```

## xtask Commands
- **Pre-commit**: Run `cargo xtask pre-commit` locally to run formatting, check, clippy, deny, audit, and basic coverage.
- **CI**: Run `cargo xtask ci` to run full tests, semver-checks, bench, docs with private items, and insta snapshot review.
- **Full Audit**: Run `cargo xtask full-audit` for releases (includes MSRV check, deadlinks, and SBOM generation).

## Reviewing Snapshots
Run `cargo insta review` to review and accept/reject new or changed snapshots.

## Coverage Reports
Run `cargo llvm-cov --workspace --html --output-dir target/coverage` and open `target/coverage/index.html` in your browser.
