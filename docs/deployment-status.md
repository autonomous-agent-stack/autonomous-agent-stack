# Deployment Status

## As Of March 31, 2026

- Mac control plane: online
- Local AEP / OpenHands execution lane: online
- Linux remote execution lane: offline
- Real SSH / supervisor / systemd remote integration: not connected in this branch

## What This Branch Does

`feat/control-plane-hardening` hardens the control plane before Linux comes back:

- fixed remote-run contract
- JSON schemas for task and summary payloads
- fake remote adapter for offline orchestration testing
- centralized failure taxonomy
- day/night runtime mode config layer
- lifecycle / failure / deployment docs

## What This Branch Explicitly Does Not Do

- no live SSH dispatch to Linux
- no always-on Linux supervisor
- no systemd or cron remote scheduler
- no claim that remote Draft PR flow is production-ready

## Practical Reading

Right now the repository behaves like this:

- preferred lane can still be configured as `remote`
- if remote is unavailable, control-plane selection falls back to `local`
- the fallback is recorded in `dispatch_run`
- fake remote artifacts are written under the normal run root so future Linux worker wiring can reuse the same shape

When the Linux lane is restored, the next step is to replace the fake adapter with a real remote adapter, not redesign the protocol from scratch.
