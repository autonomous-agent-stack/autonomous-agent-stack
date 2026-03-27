from __future__ import annotations

from autoresearch.agent_protocol.models import JobSpec


def test_job_spec_roundtrip() -> None:
    original = JobSpec(
        run_id="roundtrip-run",
        agent_id="openhands",
        task="create minimal patch",
    )

    payload = original.model_dump(mode="json")
    rebuilt = JobSpec.model_validate(payload)

    assert rebuilt == original
    assert rebuilt.protocol_version == "aep/v0"
