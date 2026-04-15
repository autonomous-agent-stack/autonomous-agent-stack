# GitHub Admin Execute-Prep Review Examples

## ready_to_execute

### transfer-plan JSON fragment

```json
{
  "run_type": "transfer_plan",
  "dry_run": true,
  "summary": {
    "ready_to_execute_count": 1,
    "blocked_count": 0,
    "unknown_count": 1
  },
  "preflight": {
    "target_owner_probe": {
      "target_owner": "project",
      "confirmation_profile_id": "github_project_admin",
      "readiness": "ready",
      "reason": "target owner reachable via repository listing probe"
    },
    "repository": {
      "full_name": "Lisa/client-portal",
      "readiness": "ready",
      "reason": "preflight checks passed",
      "profile_isolation": {
        "status": "ready",
        "reason": "source-owner profile isolation validated"
      },
      "target_owner_probe": {
        "status": "ready",
        "reason": "target owner reachable via repository listing probe"
      },
      "collaborator_sync": {
        "status": "ready",
        "reason": "collaborator readiness inspected"
      },
      "invitation_acceptance": {
        "status": "ready",
        "reason": "invitation acceptance profile is ready for dry-run verification"
      }
    }
  },
  "decision": {
    "full_name": "Lisa/client-portal",
    "action": "plan_transfer",
    "readiness": "ready"
  }
}
```

### `plan.md` key fragment

```md
## ready_to_execute
- `Lisa/client-portal`
  source profile: `github_lisa`
  confirmation profile: `github_project_admin`
  reason: preflight checks passed
```

### Why this lands in `ready_to_execute`

- `profile_isolation`: source `github_lisa` and target `github_project_admin` are both present, non-example, tokenized, and transfer-safe for the source.
- `target_owner_probe`: `project` is reachable through the repository-listing probe.
- `repository readiness`: the repo has no hard exclusion reason.
- `collaborator / invitation readiness`: collaborator inspection succeeded and invitation acceptance has a confirmation profile.

## blocked

### transfer-plan JSON fragment

```json
{
  "run_type": "transfer_plan",
  "dry_run": true,
  "summary": {
    "ready_to_execute_count": 0,
    "blocked_count": 1,
    "unknown_count": 0
  },
  "preflight": {
    "target_owner_probe": {
      "target_owner": "project",
      "confirmation_profile_id": "github_project_admin",
      "readiness": "ready",
      "reason": "target owner reachable via repository listing probe"
    },
    "repository": {
      "full_name": "dd/ops-scripts",
      "readiness": "blocked",
      "reason": "archived repo excluded by request",
      "profile_isolation": {
        "status": "ready",
        "reason": "source-owner profile isolation validated"
      },
      "target_owner_probe": {
        "status": "ready",
        "reason": "target owner reachable via repository listing probe"
      },
      "collaborator_sync": {
        "status": "unknown",
        "reason": "collaborator readiness unavailable with current token scope"
      },
      "invitation_acceptance": {
        "status": "ready",
        "reason": "invitation acceptance profile is ready for dry-run verification"
      }
    }
  },
  "decision": {
    "full_name": "dd/ops-scripts",
    "action": "skip",
    "readiness": "blocked"
  }
}
```

### `plan.md` key fragment

```md
## blocked
- `dd/ops-scripts`
  source profile: `github_dd`
  confirmation profile: `github_project_admin`
  reason: archived repo excluded by request
  detail: collaborator readiness unavailable with current token scope
```

### Why this lands in `blocked`

- `profile_isolation`: source and target profiles are both valid, so the block does not come from profile isolation.
- `target_owner_probe`: target owner is reachable, so the block does not come from target readiness.
- `repository readiness`: this repo is archived and the request excludes archived repos, which is treated as a hard block.
- `collaborator / invitation readiness`: collaborator readiness is only `unknown`, but the hard archived-policy reason already forces `blocked`.

## unknown

### transfer-plan JSON fragment

```json
{
  "run_type": "transfer_plan",
  "dry_run": true,
  "summary": {
    "ready_to_execute_count": 1,
    "blocked_count": 0,
    "unknown_count": 1
  },
  "preflight": {
    "target_owner_probe": {
      "target_owner": "project",
      "confirmation_profile_id": "github_project_admin",
      "readiness": "ready",
      "reason": "target owner reachable via repository listing probe"
    },
    "repository": {
      "full_name": "Lisa/demo-playground",
      "readiness": "unknown",
      "reason": "heuristic: name or description suggests demo/test/playground usage",
      "profile_isolation": {
        "status": "ready",
        "reason": "source-owner profile isolation validated"
      },
      "target_owner_probe": {
        "status": "ready",
        "reason": "target owner reachable via repository listing probe"
      },
      "collaborator_sync": {
        "status": "ready",
        "reason": "collaborator readiness inspected"
      },
      "invitation_acceptance": {
        "status": "ready",
        "reason": "invitation acceptance profile is ready for dry-run verification"
      }
    }
  },
  "decision": {
    "full_name": "Lisa/demo-playground",
    "action": "review",
    "readiness": "unknown"
  }
}
```

### `plan.md` key fragment

```md
## unknown
- `Lisa/demo-playground`
  source profile: `github_lisa`
  confirmation profile: `github_project_admin`
  reason: heuristic: name or description suggests demo/test/playground usage
```

### Why this lands in `unknown`

- `profile_isolation`: source and target profiles are both ready.
- `target_owner_probe`: target owner probe is ready.
- `repository readiness`: the repo is not hard-blocked, but the demo/playground heuristic means the system cannot confidently recommend execution.
- `collaborator / invitation readiness`: both are ready, so the uncertainty is driven by repository policy heuristics, not execution plumbing.

## Smoke

- API route registration is covered by `tests/github_admin/test_router.py`, which exercises `/api/jobs/github-admin/inventory`, `/transfer-plan`, and `/execute-transfer`.
- `execute-transfer` is still asserted as HTTP `501`.
- `transfer-plan` response is asserted to include a `preflight` block, including `target_owner_probe.readiness`.
