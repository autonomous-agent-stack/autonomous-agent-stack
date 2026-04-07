from __future__ import annotations

import json
from types import SimpleNamespace

from autoresearch.github_assistant.cli import main
from autoresearch.github_assistant.models import DoctorCheck, DoctorStatus, GitHubAssistantDoctorRead
from tests.test_github_assistant import _repo_config, _write_template_root


def test_cli_profile_init_and_list(tmp_path, capsys) -> None:
    _write_template_root(tmp_path, repos=[_repo_config(repo="acme/root")])

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "profile",
            "init",
            "ops",
            "--display-name",
            "Ops",
        ]
    )
    init_output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert init_output["profile_id"] == "ops"
    assert (tmp_path / "profiles.yaml").exists()
    assert (tmp_path / "profiles" / "ops" / "assistant.yaml").exists()
    assert (tmp_path / "profiles" / "ops" / "repos.yaml").exists()

    exit_code = main(["--repo-root", str(tmp_path), "profile", "list"])
    list_output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert list_output["default_profile"] == "default"
    assert {item["id"] for item in list_output["profiles"]} == {"default", "ops"}


def test_cli_doctor_uses_selected_profile(monkeypatch, tmp_path, capsys) -> None:
    class FakeService:
        def __init__(self, profile_id: str) -> None:
            display_name = "Ops" if profile_id == "ops" else "Default"
            self.profile = SimpleNamespace(id=profile_id, display_name=display_name)

        def doctor_report(self) -> GitHubAssistantDoctorRead:
            return GitHubAssistantDoctorRead(
                ok=True,
                profile_id=self.profile.id,
                profile_display_name=self.profile.display_name,
                github_host="github.com",
                managed_repo_count=1,
                expected_github_login=f"{self.profile.id}-bot",
                active_login=f"{self.profile.id}-bot",
                checks=[DoctorCheck(name="gh auth", status=DoctorStatus.PASS, detail="authenticated")],
            )

    class FakeRegistry:
        def __init__(self, *, repo_root) -> None:
            self.repo_root = repo_root

        def get(self, profile_id: str | None = None) -> FakeService:
            return FakeService(profile_id or "default")

    monkeypatch.setattr("autoresearch.github_assistant.cli.GitHubAssistantServiceRegistry", FakeRegistry)

    exit_code = main(["--repo-root", str(tmp_path), "--profile", "ops", "doctor"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Profile: ops (Ops)" in output
    assert "[PASS] gh auth: authenticated" in output
