# telegram-youtube-autoflow-ingress-v1

## Goal

Expose the existing internal `youtube_autoflow` chain through the current Telegram gateway without duplicating YouTube or GitHub business logic in the chat layer.

## Scope

This slice includes:

- `src/autoresearch/api/routers/gateway_telegram.py`
- the existing Telegram webhook / poller bridge path
- enqueueing `task_type=youtube_autoflow` onto the existing Python control plane
- immediate Telegram acceptance / rejection / enqueue-failure feedback
- OpenClaw session event + metadata linkage for accepted and rejected ingress attempts
- focused tests for happy-path enqueue, fail-closed rejects, and non-YouTube fallback behavior

## Fixed v1 Decisions

- Telegram stays a thin ingress only:
  - extract message text
  - validate routing shape
  - enqueue the existing `youtube_autoflow`
  - return immediate receipt state
- `youtube_autoflow` remains the only source of truth for:
  - YouTube URL resolution
  - transcript / digest generation
  - GitHub publish routing
- supported ingress shape is exactly one URL in the message, and that URL must be YouTube
- multiple URLs fail closed with rejection
- malformed YouTube references fail closed with rejection
- non-YouTube messages keep the pre-existing Telegram gateway behavior
- receipt state is exposed as:
  - `accepted=true` with `metadata.status=accepted`
  - `accepted=false` with `metadata.status=rejected`
  - `accepted=false` with `metadata.status=failed` when enqueue itself fails
- accepted runs persist `run_id` plus Telegram/OpenClaw session linkage in metadata so later cancel / retract flows can target a stable control-plane id

## Non-goals

- no Telegram-specific YouTube processing chain
- no Telegram-specific GitHub publish path
- no remote real PR smoke
- no TypeScript `agent-control-plane/` changes
- no multi-agent orchestration layer
- no completion pushback or long-running Telegram status choreography
- no `/cancel` or compensating rollback workflow in this slice

## Acceptance

- a Telegram message containing one valid YouTube URL enqueues the existing `youtube_autoflow`
- the queue item keeps `task_type=youtube_autoflow`
- the existing Mac standby worker can claim and execute that run unchanged
- GitHub publish still flows through `publish_youtube`
- invalid or ambiguous ingress fails closed
- focused tests cover accept / reject / fallback behavior

## Status

- implemented:
  - thin Telegram ingress branch before generic agent fallback
  - reuse of shared YouTube URL extraction helpers
  - `run_id` / session linkage persisted in OpenClaw events and session metadata
  - immediate Telegram notifier messages for accepted / rejected / failed
- still intentionally deferred:
  - cancel / retract commands
  - downstream completion notifications back into Telegram
  - Linux/Mac failback orchestration for the Telegram poller itself

## Related Decision

- [WhatsApp vs Telegram thin ingress comparison](./whatsapp-vs-telegram-thin-ingress.md)
- [Chat platform ingress recommendation](./chat-platform-ingress-recommendation-v1.md)
