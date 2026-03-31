# Housekeeper Cleanup

## Active Runtime

The only active housekeeper runtime implementation is:

- `src/autoresearch/core/services/personal_housekeeper.py`

This is the control-plane-backed mainline service used by:

- `src/autoresearch/api/dependencies.py`
- `src/autoresearch/api/routers/openclaw_housekeeper.py`

## What Remains Under `src/autoresearch/housekeeper/`

The `src/autoresearch/housekeeper/` package is retained for schema-level compatibility only.

It may contain:

- request/response schema helpers
- package-level documentation

It must not contain:

- runtime dispatch logic
- active service wiring
- a second `PersonalHousekeeperService` implementation

## Deprecation Rule

If code needs the active runtime, import from:

- `autoresearch.core.services.personal_housekeeper`

Do not import runtime behavior from:

- `autoresearch.housekeeper`
- `autoresearch.housekeeper.service`

## Migration Rule

When consolidating future housekeeper changes:

1. Keep runtime behavior in the mainline service.
2. Keep API wiring pointed at the mainline service.
3. Treat `src/autoresearch/housekeeper/` as compatibility/documentation-only unless an explicit migration plan says otherwise.
