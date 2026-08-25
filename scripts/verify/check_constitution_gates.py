from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify.common import CheckResult, REPO_ROOT, emit_many


REQUIRED_REGISTRY_TABLES = (
    "evidence_registry",
    "mission_registry",
    "decision_registry",
    "capability_registry",
    "adr_registry",
    "technical_debt_registry",
    "platform_health_registry",
)

REQUIRED_CONSTITUTION_ENDPOINTS = (
    "/api/operator/constitution",
    "/api/operator/constitution/evidence",
    "/api/operator/constitution/evidence/backfill",
    "/api/operator/constitution/missions",
    "/api/operator/constitution/decisions",
    "/api/operator/constitution/capabilities",
    "/api/operator/constitution/seed",
    "/api/operator/constitution/adrs",
    "/api/operator/constitution/debt",
    "/api/operator/constitution/health",
    "/api/operator/constitution/health/capture-runtime-summary",
)

MUTATING_METHODS = {"post", "put", "patch", "delete"}
ROUTE_DECORATOR_RE = re.compile(r"@router\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]")
EXEMPT_PREFIX_RE = re.compile(r"_EXEMPT_PREFIXES\s*=\s*\((?P<body>.*?)\)", re.DOTALL)
STRING_RE = re.compile(r"['\"]([^'\"]+)['\"]")

# These mutating routes are intentionally reachable before the normal operator
# bearer/session check. New entries here should be rare and accompanied by
# source-specific auth such as signed webhooks.
ALLOWED_MUTATING_EXEMPTIONS = {
    "/api/desktop/bootstrap",
    "/api/desktop/bootstrap-code",
    "/api/webhooks/github/workflow-run",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _route_paths() -> list[tuple[str, str, Path]]:
    rows: list[tuple[str, str, Path]] = []
    routes_dir = REPO_ROOT / "services" / "control-plane" / "app" / "routes"
    for path in sorted(routes_dir.glob("*.py")):
        text = _read(path)
        for match in ROUTE_DECORATOR_RE.finditer(text):
            rows.append((match.group(1).lower(), match.group(2), path))
    return rows


def _exempt_prefixes() -> list[str]:
    middleware = REPO_ROOT / "services" / "control-plane" / "app" / "auth" / "middleware.py"
    text = _read(middleware)
    match = EXEMPT_PREFIX_RE.search(text)
    if not match:
        return []
    return [item for item in STRING_RE.findall(match.group("body"))]


def _is_exempt(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


def _check_registry_spine() -> list[CheckResult]:
    store = REPO_ROOT / "services" / "control-plane" / "app" / "persistence" / "constitution_registry_store.py"
    adapter = REPO_ROOT / "services" / "control-plane" / "app" / "persistence" / "evidence_ref_adapters.py"
    seed = REPO_ROOT / "services" / "control-plane" / "app" / "constitution_seed.py"
    results: list[CheckResult] = []
    if not store.exists():
        return [
            CheckResult(
                name="constitution_registry_store",
                status="fail",
                message="missing constitution registry store",
            )
        ]
    store_text = _read(store)
    missing_tables = [table for table in REQUIRED_REGISTRY_TABLES if table not in store_text]
    results.append(
        CheckResult(
            name="constitution_registry_tables",
            status="pass" if not missing_tables else "fail",
            message=(
                "all required registry tables are declared"
                if not missing_tables
                else "required registry tables are missing"
            ),
            details=missing_tables,
        )
    )
    if not adapter.exists():
        results.append(
            CheckResult(
                name="constitution_evidence_adapters",
                status="fail",
                message="missing evidence-ref adapters",
            )
        )
    else:
        adapter_text = _read(adapter)
        has_history_shape = all(token in adapter_text for token in ("history_ref", "sequence", "transition_json"))
        results.append(
            CheckResult(
                name="constitution_run_history_adapter",
                status="pass" if has_history_shape else "fail",
                message=(
                    "run_history adapter uses history_ref/sequence/transition_json"
                    if has_history_shape
                    else "run_history adapter does not reflect the actual schema"
                ),
            )
        )
    if seed.exists():
        seed_text = _read(seed)
        has_seed_ids = all(token in seed_text for token in ("CAP-007", "CAP-034", "CAP-070"))
        results.append(
            CheckResult(
                name="constitution_seed_capabilities",
                status="pass" if has_seed_ids else "fail",
                message=(
                    "constitution seed includes evidence, autonomy, and verification capabilities"
                    if has_seed_ids
                    else "constitution seed is missing required capability anchors"
                ),
            )
        )
    else:
        results.append(
            CheckResult(
                name="constitution_seed_capabilities",
                status="fail",
                message="missing constitution seed module",
            )
        )
    return results


def _check_routes() -> list[CheckResult]:
    route_file = REPO_ROOT / "services" / "control-plane" / "app" / "routes" / "constitution.py"
    routes_init = REPO_ROOT / "services" / "control-plane" / "app" / "routes" / "__init__.py"
    if not route_file.exists():
        return [
            CheckResult(
                name="constitution_routes",
                status="fail",
                message="missing constitution routes module",
            )
        ]
    route_text = _read(route_file)
    init_text = _read(routes_init)
    missing_endpoints = [
        endpoint for endpoint in REQUIRED_CONSTITUTION_ENDPOINTS if endpoint not in route_text
    ]
    return [
        CheckResult(
            name="constitution_route_registration",
            status="pass" if "constitution" in init_text and "constitution.router" in init_text else "fail",
            message=(
                "constitution router is registered"
                if "constitution" in init_text and "constitution.router" in init_text
                else "constitution router is not registered"
            ),
        ),
        CheckResult(
            name="constitution_registry_endpoints",
            status="pass" if not missing_endpoints else "fail",
            message=(
                "all first-slice constitution endpoints are present"
                if not missing_endpoints
                else "constitution endpoints are missing"
            ),
            details=missing_endpoints,
        ),
    ]


def _check_mutating_route_auth() -> list[CheckResult]:
    main_text = _read(REPO_ROOT / "services" / "control-plane" / "app" / "main.py")
    middleware_text = _read(
        REPO_ROOT / "services" / "control-plane" / "app" / "auth" / "middleware.py"
    )
    routes = _route_paths()
    mutating = [(method, path, file) for method, path, file in routes if method in MUTATING_METHODS]
    exempt_prefixes = _exempt_prefixes()
    exempt_mutating = [
        path for _method, path, _file in mutating if _is_exempt(path, exempt_prefixes)
    ]
    unexpected_exempt = sorted(
        path for path in exempt_mutating if path not in ALLOWED_MUTATING_EXEMPTIONS
    )
    return [
        CheckResult(
            name="mutating_auth_middleware_registered",
            status="pass" if "MutatingAuthMiddleware" in main_text and "add_middleware(MutatingAuthMiddleware)" in main_text else "fail",
            message=(
                "FastAPI app installs MutatingAuthMiddleware"
                if "MutatingAuthMiddleware" in main_text and "add_middleware(MutatingAuthMiddleware)" in main_text
                else "FastAPI app does not visibly install MutatingAuthMiddleware"
            ),
        ),
        CheckResult(
            name="mutating_methods_guarded",
            status="pass" if "_MUTATING" in middleware_text and not unexpected_exempt else "fail",
            message=(
                f"{len(mutating) - len(exempt_mutating)} mutating routes covered by middleware; "
                f"{len(exempt_mutating)} intentional exemptions"
                if "_MUTATING" in middleware_text and not unexpected_exempt
                else "unexpected mutating route exemption detected"
            ),
            details=unexpected_exempt,
        ),
    ]


def _check_tests_and_handoff() -> list[CheckResult]:
    test_file = REPO_ROOT / "tests" / "test_constitution_registry.py"
    handoff = (
        REPO_ROOT
        / "docs"
        / "ops"
        / "agent-reports"
        / "axon-x-constitution-gap-audit-2026-08-09.md"
    )
    test_text = _read(test_file) if test_file.exists() else ""
    handoff_text = _read(handoff) if handoff.exists() else ""
    return [
        CheckResult(
            name="constitution_registry_tests",
            status="pass" if test_file.exists() and "backfill_run_history" in test_text else "fail",
            message=(
                "focused constitution registry tests are present"
                if test_file.exists() and "backfill_run_history" in test_text
                else "missing focused constitution registry tests"
            ),
        ),
        CheckResult(
            name="constitution_handoff_ledger",
            status="pass" if handoff.exists() and "Implementation progress ledger" in handoff_text else "fail",
            message=(
                "handoff ledger is present and updated"
                if handoff.exists() and "Implementation progress ledger" in handoff_text
                else "handoff ledger missing progress section"
            ),
        ),
    ]


def run_check() -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(_check_registry_spine())
    results.extend(_check_routes())
    results.extend(_check_mutating_route_auth())
    results.extend(_check_tests_and_handoff())
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check AXON-X constitution implementation gates.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(argv or sys.argv[1:])
    return emit_many(run_check())


if __name__ == "__main__":
    raise SystemExit(main())
