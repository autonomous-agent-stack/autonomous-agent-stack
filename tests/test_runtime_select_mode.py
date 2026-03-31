from __future__ import annotations

from autoresearch.core.runtime.select_mode import load_mode_policy, select_mode
from autoresearch.shared.remote_run_contract import DispatchLane


def test_load_runtime_mode_policies() -> None:
    day = load_mode_policy(mode_name="day")
    night = load_mode_policy(mode_name="night")

    assert day.preferred_lane is DispatchLane.LOCAL
    assert day.allow_draft_pr is False
    assert night.preferred_lane is DispatchLane.REMOTE
    assert night.allow_exploration is True


def test_select_mode_falls_back_to_local_when_remote_is_unavailable() -> None:
    selected = select_mode(requested_mode="night", remote_available=False)

    assert selected.requested_lane is DispatchLane.REMOTE
    assert selected.lane is DispatchLane.LOCAL
    assert selected.fallback_reason is not None
