from __future__ import annotations

from autoresearch.core.services.youtube_digest import YouTubeDigestService
from autoresearch.shared.models import (
    JobStatus,
    YouTubeTranscriptRead,
    YouTubeTranscriptSource,
    YouTubeVideoRead,
    utc_now,
)


def _build_digest(transcript_content: str, *, description: str | None = None) -> str:
    now = utc_now()
    service = YouTubeDigestService()
    video = YouTubeVideoRead(
        video_id="video-001",
        source_url="https://www.youtube.com/watch?v=video-001",
        channel_title="Demo Channel",
        title="Demo Video",
        description=description,
        status=JobStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    transcript = YouTubeTranscriptRead(
        transcript_id="yttranscript-001",
        video_id="video-001",
        language="en",
        source=YouTubeTranscriptSource.MANUAL,
        status=JobStatus.COMPLETED,
        content=transcript_content,
        created_at=now,
        updated_at=now,
    )
    return service.generate_digest(video=video, transcript=transcript, output_format="markdown")


def test_digest_filters_sponsor_intro_and_keeps_meaningful_content() -> None:
    digest = _build_digest(
        (
            "This video is sponsored by ExampleCorp and you can use code DEMO for 20 percent off.\n"
            "Hey everyone, welcome back to the channel.\n"
            "Today we compare deterministic polling with event-driven ingestion for YouTube monitoring.\n"
            "The key tradeoff is simpler idempotency versus lower notification latency."
        )
    )

    assert "sponsored by" not in digest.lower()
    assert "welcome back to the channel" not in digest.lower()
    assert "deterministic polling with event-driven ingestion" in digest
    assert "simpler idempotency versus lower notification latency" in digest


def test_digest_strips_long_self_intro_but_preserves_topic_sentence() -> None:
    digest = _build_digest(
        (
            "If you're new here, I'm Jane and on this channel I break down backend systems every week.\n"
            "In this video I show how to persist transcript, digest, and run state without duplicating work.\n"
            "The example focuses on stable dedupe by normalized URL and video id."
        )
    )

    assert "i'm jane" not in digest.lower()
    assert "persist transcript, digest, and run state" in digest
    assert "stable dedupe by normalized url and video id" in digest.lower()


def test_digest_filters_background_intro_and_rhetorical_hook() -> None:
    digest = _build_digest(
        (
            "Before Google, I was an independent game developer best known for a puzzle game.\n"
            "Have you ever imagined building an AI-powered educational game?\n"
            "The walkthrough focuses on agentic NPCs, vibe-coding puzzles, and deterministic state transitions."
        )
    )

    assert "before google" not in digest.lower()
    assert "have you ever imagined" not in digest.lower()
    assert "agentic npcs, vibe-coding puzzles, and deterministic state transitions" in digest.lower()


def test_digest_drops_outro_cta_lines() -> None:
    digest = _build_digest(
        (
            "The rollout uses a dedicated repository layer so service code does not rescan full lists.\n"
            "This keeps idempotency logic explicit and testable.\n"
            "Thanks for watching, like and subscribe, and hit the bell for more updates."
        )
    )

    assert "thanks for watching" not in digest.lower()
    assert "like and subscribe" not in digest.lower()
    assert "dedicated repository layer" in digest


def test_digest_filters_mixed_description_noise() -> None:
    digest = _build_digest(
        "We explain how transcript failures should persist stable error kinds and reasons.",
        description=(
            "Resources: https://example.com/demo\n"
            "Speaker: Jane Doe\n"
            "We also walk through how live smoke should report failed stage and retryability."
        ),
    )

    assert "resources:" not in digest.lower()
    assert "speaker:" not in digest.lower()
    assert "failed stage and retryability" in digest.lower()


def test_normalize_lines_drops_generic_opening_framing() -> None:
    lines = YouTubeDigestService()._normalize_lines(
        (
            "In this video, we'll take a tour of an experience my colleague and I built.\n"
            "It's an offline-capable, AI-powered educational game built with Angular, PhaserJS, and Gemma 4."
        )
    )

    assert all("take a tour" not in line.lower() for line in lines)
    assert any("offline-capable, ai-powered educational game built with angular" in line.lower() for line in lines)


def test_normalize_lines_rewrites_generic_project_intro() -> None:
    lines = YouTubeDigestService()._normalize_lines(
        (
            'So meet "AIventure," an open source educational game in which the user explores a retro dungeon.\n'
            'So that\'s "AIventure," a web-based educational game that teaches GenAI principles.'
        )
    )

    assert '"AIventure" is an open source educational game in which the user explores a retro dungeon' in lines
    assert '"AIventure" is a web-based educational game that teaches GenAI principles' in lines


def test_normalize_lines_preserves_setup_with_real_claim() -> None:
    lines = YouTubeDigestService()._normalize_lines(
        "In this video, we'll take a look at how transcript runs persist failed_stage and reason across retries."
    )

    assert lines == ["We'll take a look at how transcript runs persist failed_stage and reason across retries"]


def test_digest_filters_generic_description_framing() -> None:
    digest = _build_digest(
        "Deterministic reruns depend on stable video ids and explicit failure states.",
        description=(
            "In this video, we'll take a tour of the updated workflow.\n"
            "Resources: https://example.com/demo"
        ),
    )

    assert "take a tour" not in digest.lower()
    assert "deterministic reruns depend on stable video ids and explicit failure states" in digest.lower()


def test_digest_drops_low_value_preference_and_closing_bridge_lines() -> None:
    digest = _build_digest(
        (
            "The workflow can route prompts to a local Gemma 4 runtime or a Gemini API backend.\n"
            "Or if you prefer, you can use Gemini.\n"
            "Explore our solution.\n"
            "And we can't wait to see what AI-powered experiences you build."
        )
    )

    assert "or if you prefer" not in digest.lower()
    assert "explore our solution" not in digest.lower()
    assert "we can't wait to see" not in digest.lower()
    assert "route prompts to a local gemma 4 runtime or a gemini api backend" in digest.lower()
