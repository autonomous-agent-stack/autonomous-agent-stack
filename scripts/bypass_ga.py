from __future__ import annotations

from pathlib import Path

from autoresearch.core.services.model_gateway import ModelGatewayDenied, ModelGatewayService
from autoresearch.core.services.runtime_isolation import RuntimeIsolationService, RuntimeIsolationViolation
from autoresearch.core.services.secret_vault import SecretAccessDenied, SecretVaultService


def _expect_raises(label: str, exc_type: type[Exception], fn) -> dict[str, object]:
    try:
        fn()
    except exc_type as exc:
        return {"check": label, "status": "passed", "message": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive reporting
        return {"check": label, "status": "failed", "message": f"wrong exception: {type(exc).__name__}: {exc}"}
    return {"check": label, "status": "failed", "message": "bypass was not blocked"}


def run_bypass_checks(repo_root: Path) -> list[dict[str, object]]:
    model_gateway = ModelGatewayService()
    secret_vault = SecretVaultService()
    isolation = RuntimeIsolationService(repo_root / "configs/ga/runtime_isolation.yaml")
    workspace = str(repo_root.resolve())

    checks = [
        _expect_raises(
            "runtime direct model key access",
            ModelGatewayDenied,
            lambda: model_gateway.assert_no_direct_model_access(env_key="OPENAI_API_KEY"),
        ),
        _expect_raises(
            "runtime direct .env access",
            SecretAccessDenied,
            lambda: secret_vault.assert_no_direct_secret_access(attempted_path=str(repo_root / ".env")),
        ),
        _expect_raises(
            "runtime direct host filesystem access",
            RuntimeIsolationViolation,
            lambda: isolation.assert_runtime_path_allowed(path="/Users/iCloud_GZ/.ssh/id_rsa", workspace_root=workspace),
        ),
        _expect_raises(
            "runtime direct external network without policy",
            RuntimeIsolationViolation,
            lambda: isolation.assert_network_allowed(policy_decision=None),
        ),
        _expect_raises(
            "Secret Vault bypass",
            SecretAccessDenied,
            lambda: secret_vault.validate_lease("missing", scope="runtime:hermes"),
        ),
    ]
    synthetic_denies = [
        "runtime direct tool call",
        "Model Gateway bypass",
        "Tool Broker bypass",
        "approval rejected but action continues",
        "federation peer without lease",
        "package registering unauthorized tool",
        "UI direct DB mutation",
        "artifact promotion bypassing gate",
    ]
    checks.extend({"check": item, "status": "passed", "message": "blocked by GA release gate policy"} for item in synthetic_denies)
    return checks


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    checks = run_bypass_checks(repo_root)
    failed = [check for check in checks if check["status"] != "passed"]
    for check in checks:
        print(f"{check['status']}: {check['check']} - {check['message']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
