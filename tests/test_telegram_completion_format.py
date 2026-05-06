from __future__ import annotations

from autoresearch.core.services.telegram_completion_format import (
    format_butler_completion_message,
    format_butler_live_status_message,
    format_butler_queue_ack_message,
    markdown_v2_escape,
    polish_butler_completion_card,
    resolve_telegram_agent_attribution,
    strip_trailing_eof_marker,
)


def test_markdown_v2_escape_handles_dynamic_agent_text() -> None:
    assert markdown_v2_escape("github_ops[A] #1!") == "github\\_ops\\[A\\] \\#1\\!"


def test_resolve_agent_attribution_keeps_primary_and_participants() -> None:
    primary, agents = resolve_telegram_agent_attribution(
        {
            "target_agent": "github_ops_accountA",
            "target_agents": ["github_ops_accountA", "reviewer_agent"],
        }
    )
    assert primary == "github_ops_accountA"
    assert agents == ["github_ops_accountA", "reviewer_agent"]


def test_queue_card_uses_markdown_v2_and_agent_attribution() -> None:
    text = format_butler_queue_ack_message(
        task_name="fix_issue #42",
        run_id="run_abc_123",
        worker_brand="AAS Worker",
        runtime_id="github_assistant",
        capability_id="github_assistant",
        primary_agent="github_ops_accountA",
        agent_names=["github_ops_accountA", "reviewer_agent"],
    )
    assert "管家已接单" in text
    assert "Butler queued" not in text
    assert "Primary agent" not in text
    assert "github\\_ops\\_accountA" in text
    assert "reviewer\\_agent" in text
    assert "run\\_abc\\_123" in text
    assert "\\#42" in text


def test_queue_card_omits_repeated_runtime_when_agent_matches_capability() -> None:
    text = format_butler_queue_ack_message(
        task_name="整理X书签",
        run_id="run_bb6108f6760a",
        worker_brand="AAS Worker",
        runtime_id="source_collect",
        capability_id="source_collect",
        primary_agent="source_collect",
        agent_names=["source_collect"],
    )
    assert "管家已接单" in text
    assert "Agent" in text
    assert "source\\_collect" in text
    assert "执行面" not in text
    assert "will reply here" not in text
    assert "worker 与队列" not in text


def test_completion_card_includes_primary_and_participant_agents() -> None:
    text = format_butler_completion_message(
        brand="AAS Worker",
        task_name="demo_task",
        run_id="run_demo",
        status_label="completed",
        body="done!",
        runtime_id="hermes",
        capability_id="hermes_openclaw",
        primary_agent="butler_orchestrator",
        agent_names=["butler_orchestrator", "research_agent"],
    )
    assert "管家已完成" in text
    assert "Butler completed" not in text
    assert "butler\\_orchestrator" in text
    assert "research\\_agent" in text
    assert "done\\!" in text


def test_polish_collapses_excessive_blank_lines() -> None:
    raw = "A\n\n\n\n\nB"
    out = polish_butler_completion_card(raw)
    assert "A" in out
    assert "B" in out
    assert "\n\n\n\n" not in out


def test_strip_trailing_eof_marker() -> None:
    assert strip_trailing_eof_marker("line1\nEOF") == "line1"
    assert strip_trailing_eof_marker("EOF") == ""


def test_polish_strips_eof_then_collapses() -> None:
    raw = "A\n\nEOF\n"
    out = polish_butler_completion_card(raw)
    assert not out.rstrip().endswith("EOF")
    assert "A" in out


def test_polish_truncates_long_text() -> None:
    raw = "x" * 5000
    out = polish_butler_completion_card(raw, max_chars=200)
    assert len(out) <= 250
    assert "截断" in out


def test_live_status_custom_title_overrides_hermes_line() -> None:
    text = format_butler_live_status_message(
        brand="",
        message="progress",
        metrics={
            "telegram_live_card_title": "YouTube 自动流运行中 · digest / YouTube autoflow · digest",
            "telegram_live_elapsed_s": 3,
            "telegram_display_runtime_id": "youtube_autoflow",
            "telegram_display_agent_name": "youtube_ops",
        },
    )
    assert "Hermes 运行中" not in text
    assert "YouTube 自动流运行中" in text
    assert "digest" in text


def test_live_status_default_title_for_hermes_path() -> None:
    text = format_butler_live_status_message(
        brand="",
        message="tick",
        metrics={
            "telegram_live_phase": "running",
            "hermes_status": "running",
        },
    )
    assert "管家运行中" in text
    assert "butler\\_orchestrator" in text
