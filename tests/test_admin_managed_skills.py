from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
import pytest

from autoresearch.api.dependencies import (
    get_admin_auth_service,
    get_approval_store_service,
    get_managed_skill_registry_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.api.main import app
from autoresearch.core.services.admin_auth import AdminAuthService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.managed_skill_registry import ManagedSkillRegistryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestRead,
    ManagedSkillInstallRequest,
)
from autoresearch.shared.store import InMemoryRepository, SQLiteModelRepository


class StubTelegramNotifier:
    def __init__(self, *, send_results: list[bool] | None = None) -> None:
        self.messages: list[dict[str, object]] = []
        self._send_results = list(send_results or [])

    @property
    def enabled(self) -> bool:
        return True

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = True,
        reply_markup: dict[str, object] | None = None,
    ) -> bool:
        self.messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": disable_web_page_preview,
                "reply_markup": reply_markup,
            }
        )
        if self._send_results:
            return self._send_results.pop(0)
        return True


def _sign_manifest(payload: dict[str, object], private_key: Ed25519PrivateKey) -> str:
    signature = private_key.sign(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return base64.b64encode(signature).decode("ascii")


def _bundle_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _trusted_keys() -> tuple[Ed25519PrivateKey, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    return private_key, public_key


def _build_bundle(
    bundle_root: Path,
    *,
    private_key: Ed25519PrivateKey,
    signer_id: str = "test-signer",
    skill_id: str = "daily_brief",
    version: str = "1.0.0",
    skill_name: str = "Daily Brief",
) -> Path:
    bundle_root.mkdir(parents=True, exist_ok=True)
    skill_file = bundle_root / "SKILL.md"
    skill_file.write_text(
        "---\n"
        f"name: {skill_name}\n"
        "description: Generate a concise daily brief\n"
        "metadata:\n"
        "  openclaw:\n"
        f"    skillKey: {skill_id}\n"
        "---\n"
        "# Daily Brief\n"
        "Use this skill for daily summaries.\n",
        encoding="utf-8",
    )
    payload = {
        "schema_version": "managed-skill/v1",
        "skill_id": skill_id,
        "version": version,
        "name": skill_name,
        "description": "Generate a concise daily brief",
        "entrypoint": "SKILL.md",
        "signer_id": signer_id,
        "capabilities": ["prompt"],
        "files": [{"path": "SKILL.md", "sha256": _bundle_file_hash(skill_file)}],
        "metadata": {},
    }
    manifest = {**payload, "signature": _sign_manifest(payload, private_key)}
    (bundle_root / "managed-skill.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return bundle_root


def _build_telegram_init_data(
    *,
    bot_token: str,
    telegram_uid: str,
    auth_date: int | None = None,
) -> str:
    payload = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAEAAABBBBBCCCCCDDDD",
        "user": json.dumps(
            {"id": int(telegram_uid), "first_name": "Test", "username": f"user{telegram_uid}"},
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    }
    data_check = "\n".join(f"{key}={value}" for key, value in sorted(payload.items(), key=lambda item: item[0]))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    digest = hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    payload["hash"] = digest
    return urlencode(payload)


def _action_binding_from_url(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return {
        "approval_id": query["approvalId"][0],
        "action_nonce": query["actionNonce"][0],
        "action_hash": query["actionHash"][0],
        "action_issued_at": query["actionIssuedAt"][0],
    }


@pytest.fixture
def admin_skill_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "admin-managed-skills.sqlite3"
    auth_service = AdminAuthService(
        secret="test-admin-jwt-secret",
        bootstrap_key="bootstrap-test-key",
    )
    approval_store = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_admin_skill_it",
            model_cls=ApprovalRequestRead,
        )
    )
    private_key, public_key = _trusted_keys()
    registry = ManagedSkillRegistryService(
        repo_root=tmp_path,
        repository=InMemoryRepository(),
        quarantine_root=tmp_path / "artifacts" / "managed_skills" / "quarantine",
        active_root=tmp_path / "artifacts" / "managed_skills" / "active",
        trusted_signers={"test-signer": public_key},
        allowed_capabilities={"prompt", "filesystem_read"},
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="https://panel.example/api/v1/panel/view",
        mini_app_url="https://panel.example/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    notifier = StubTelegramNotifier()

    app.dependency_overrides[get_admin_auth_service] = lambda: auth_service
    app.dependency_overrides[get_approval_store_service] = lambda: approval_store
    app.dependency_overrides[get_managed_skill_registry_service] = lambda: registry
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    with TestClient(app) as client:
        token_response = client.post(
            "/api/v1/admin/auth/token",
            json={"subject": "test-owner", "roles": ["owner"], "ttl_seconds": 3600},
            headers={"x-admin-bootstrap-key": "bootstrap-test-key"},
        )
        assert token_response.status_code == 200
        token = token_response.json()["token"]
        client.headers.update({"authorization": f"Bearer {token}"})
        setattr(client, "_managed_skill_registry", registry)
        setattr(client, "_approval_store", approval_store)
        setattr(client, "_notifier", notifier)
        setattr(client, "_bundle_private_key", private_key)
        yield client

    app.dependency_overrides.clear()


def test_admin_view_lists_managed_skill_surface(admin_skill_client: TestClient) -> None:
    response = admin_skill_client.get("/api/v1/admin/view")

    assert response.status_code == 200
    assert "Managed Skill Queue" in response.text
    assert "/api/v1/admin/skills/status" in response.text
    assert "/api/v1/admin/skills/" in response.text


def test_admin_managed_skill_status_detail_and_validate(admin_skill_client: TestClient, tmp_path: Path) -> None:
    registry = getattr(admin_skill_client, "_managed_skill_registry")
    private_key = getattr(admin_skill_client, "_bundle_private_key")
    bundle_dir = _build_bundle(tmp_path / "bundle-validate", private_key=private_key)
    quarantined = registry.install_to_quarantine(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )

    status_response = admin_skill_client.get("/api/v1/admin/skills/status")
    assert status_response.status_code == 200
    groups = {item["status"]: item["installs"] for item in status_response.json()["groups"]}
    assert groups["quarantined"][0]["install_id"] == quarantined.install_id

    validate_response = admin_skill_client.post(f"/api/v1/admin/skills/{quarantined.install_id}/validate")
    assert validate_response.status_code == 200
    validate_payload = validate_response.json()
    assert validate_payload["status"] == "cold_validated"

    detail_response = admin_skill_client.get(f"/api/v1/admin/skills/{quarantined.install_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["install_id"] == quarantined.install_id
    assert detail_payload["status"] == "cold_validated"


def test_admin_managed_skill_promote_creates_approval_and_mini_app_link(
    admin_skill_client: TestClient,
    tmp_path: Path,
) -> None:
    registry = getattr(admin_skill_client, "_managed_skill_registry")
    notifier = getattr(admin_skill_client, "_notifier")
    private_key = getattr(admin_skill_client, "_bundle_private_key")
    bundle_dir = _build_bundle(tmp_path / "bundle-promote", private_key=private_key)
    quarantined = registry.install_to_quarantine(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )
    validated = registry.run_cold_validation(quarantined.install_id)

    response = admin_skill_client.post(
        f"/api/v1/admin/skills/{validated.install_id}/promote",
        json={"note": "review this skill", "metadata": {"source": "test"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["install"]["install_id"] == validated.install_id
    assert payload["approval"]["status"] == "pending"
    assert payload["approval"]["telegram_uid"] == "10001"
    assert payload["approval"]["source"] == "managed_skill_promotion"
    assert payload["approval"]["metadata"]["action_type"] == "managed_skill_promote"
    assert payload["approval"]["metadata"]["install_id"] == validated.install_id
    assert payload["approval"]["metadata"]["action_nonce"]
    assert payload["approval"]["metadata"]["action_hash"]
    assert payload["approval"]["metadata"]["action_issued_at"]
    assert "approvalId=" in payload["mini_app_url"]
    assert "installId=" in payload["mini_app_url"]
    assert "actionNonce=" in payload["mini_app_url"]
    assert "actionHash=" in payload["mini_app_url"]
    assert "actionIssuedAt=" in payload["mini_app_url"]
    assert "token=" in payload["mini_app_url"]
    assert payload["notification_sent"] is True
    assert notifier.messages[0]["chat_id"] == "10001"
    reply_markup = notifier.messages[0]["reply_markup"]
    assert isinstance(reply_markup, dict)
    button = reply_markup["inline_keyboard"][0][0]
    assert button["web_app"]["url"] == payload["mini_app_url"]


def test_admin_managed_skill_promote_falls_back_to_url_button_when_web_app_send_fails(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "admin-managed-skills-fallback.sqlite3"
    auth_service = AdminAuthService(
        secret="test-admin-jwt-secret",
        bootstrap_key="bootstrap-test-key",
    )
    approval_store = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_admin_skill_fallback",
            model_cls=ApprovalRequestRead,
        )
    )
    private_key, public_key = _trusted_keys()
    registry = ManagedSkillRegistryService(
        repo_root=tmp_path,
        repository=InMemoryRepository(),
        quarantine_root=tmp_path / "artifacts" / "managed_skills" / "quarantine",
        active_root=tmp_path / "artifacts" / "managed_skills" / "active",
        trusted_signers={"test-signer": public_key},
        allowed_capabilities={"prompt", "filesystem_read"},
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="https://panel.example/api/v1/panel/view",
        mini_app_url="https://panel.example/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    notifier = StubTelegramNotifier(send_results=[False, True])

    app.dependency_overrides[get_admin_auth_service] = lambda: auth_service
    app.dependency_overrides[get_approval_store_service] = lambda: approval_store
    app.dependency_overrides[get_managed_skill_registry_service] = lambda: registry
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    with TestClient(app) as client:
        token_response = client.post(
            "/api/v1/admin/auth/token",
            json={"subject": "test-owner", "roles": ["owner"], "ttl_seconds": 3600},
            headers={"x-admin-bootstrap-key": "bootstrap-test-key"},
        )
        assert token_response.status_code == 200
        client.headers.update({"authorization": f"Bearer {token_response.json()['token']}"})

        bundle_dir = _build_bundle(tmp_path / "bundle-promote-fallback", private_key=private_key)
        validated = registry.run_cold_validation(
            registry.install_to_quarantine(
                ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
            ).install_id
        )

        response = client.post(
            f"/api/v1/admin/skills/{validated.install_id}/promote",
            json={"note": "retry with url button"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["notification_sent"] is True
    assert len(notifier.messages) == 2
    assert notifier.messages[0]["reply_markup"]["inline_keyboard"][0][0]["web_app"]["url"] == payload["mini_app_url"]
    assert notifier.messages[1]["reply_markup"] == {
        "inline_keyboard": [[{"text": "打开 Panel 审批", "url": payload["mini_app_url"]}]]
    }


def test_admin_managed_skill_promote_execute_requires_approved_telegram_flow(
    admin_skill_client: TestClient,
    tmp_path: Path,
) -> None:
    registry = getattr(admin_skill_client, "_managed_skill_registry")
    approval_store = getattr(admin_skill_client, "_approval_store")
    private_key = getattr(admin_skill_client, "_bundle_private_key")
    bundle_dir = _build_bundle(tmp_path / "bundle-execute", private_key=private_key)
    validated = registry.run_cold_validation(
        registry.install_to_quarantine(
            ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
        ).install_id
    )

    approval_response = admin_skill_client.post(
        f"/api/v1/admin/skills/{validated.install_id}/promote",
        json={"metadata": {"source": "test"}},
    )
    assert approval_response.status_code == 200
    approval_payload = approval_response.json()
    action_binding = _action_binding_from_url(approval_payload["mini_app_url"])
    approval_id = approval_payload["approval"]["approval_id"]
    init_data = _build_telegram_init_data(bot_token="123456:TEST_BOT_TOKEN", telegram_uid="10001")

    pending_execute = admin_skill_client.post(
        f"/api/v1/admin/skills/{validated.install_id}/promote/execute",
        json={**action_binding},
        headers={"x-telegram-init-data": init_data},
    )
    assert pending_execute.status_code == 400
    assert "not approved" in pending_execute.text

    approval_store.resolve_request(
        approval_id,
        ApprovalDecisionRequest(
            decision="approved",
            decided_by="10001",
            note="approved in test",
            metadata={"resolved_via": "panel_api"},
        ),
    )

    execute_response = admin_skill_client.post(
        f"/api/v1/admin/skills/{validated.install_id}/promote/execute",
        json={**action_binding},
        headers={"x-telegram-init-data": init_data},
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["status"] == "promoted"
    assert Path(execute_payload["active_dir"]).exists()

    replay_response = admin_skill_client.post(
        f"/api/v1/admin/skills/{validated.install_id}/promote/execute",
        json={**action_binding},
        headers={"x-telegram-init-data": init_data},
    )
    assert replay_response.status_code == 409
    assert "consumed" in replay_response.text


def test_admin_managed_skill_promote_execute_rejects_tampered_action_hash(
    admin_skill_client: TestClient,
    tmp_path: Path,
) -> None:
    registry = getattr(admin_skill_client, "_managed_skill_registry")
    approval_store = getattr(admin_skill_client, "_approval_store")
    private_key = getattr(admin_skill_client, "_bundle_private_key")
    bundle_dir = _build_bundle(tmp_path / "bundle-tampered", private_key=private_key)
    validated = registry.run_cold_validation(
        registry.install_to_quarantine(
            ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
        ).install_id
    )

    approval_response = admin_skill_client.post(
        f"/api/v1/admin/skills/{validated.install_id}/promote",
        json={},
    )
    assert approval_response.status_code == 200
    approval_payload = approval_response.json()
    action_binding = _action_binding_from_url(approval_payload["mini_app_url"])
    approval_store.resolve_request(
        approval_payload["approval"]["approval_id"],
        ApprovalDecisionRequest(
            decision="approved",
            decided_by="10001",
            note="approved in test",
            metadata={"resolved_via": "panel_api"},
        ),
    )

    init_data = _build_telegram_init_data(bot_token="123456:TEST_BOT_TOKEN", telegram_uid="10001")
    tampered = {**action_binding, "action_hash": "0" * 64}
    response = admin_skill_client.post(
        f"/api/v1/admin/skills/{validated.install_id}/promote/execute",
        json=tampered,
        headers={"x-telegram-init-data": init_data},
    )
    assert response.status_code == 401
    assert "action hash mismatch" in response.text
