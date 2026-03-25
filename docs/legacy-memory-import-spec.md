# Legacy Memory Import Specification

> **Status**: Draft v0.1  
> **Author**: glm-5-2  
> **Target**: codex-2 implementation  
> **Date**: 2026-03-26

## 1. Overview

This document specifies the migration strategy for importing legacy OpenClaw session data into the current session model. The goal is to preserve semantic equivalence while enabling idempotent, safe imports.

### 1.1 Scope

- **Source**: Legacy OpenClaw session JSONL files (`~/.openclaw/agents/*/sessions/*.jsonl`)
- **Target**: Current session model (JSONL format, version 3)
- **Focus**: Field mapping, idempotency, deduplication, timestamp fidelity

### 1.2 Non-Goals

- Production implementation (codex-2 responsibility)
- Modification of `claude_agents.py` or `openclaw.py`
- Telegram channel modifications
- Real-time sync (batch import only)

---

## 2. Source Data Model (Legacy)

### 2.1 Session File Format

**Location**: `~/.openclaw/agents/{agentId}/sessions/{sessionId}.jsonl`

**Format**: JSON Lines (one JSON object per line)

**Version**: 3 (current)

### 2.2 Event Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `session` | Session metadata | `version`, `id`, `timestamp`, `cwd` |
| `message` | User/assistant/tool messages | `id`, `parentId`, `timestamp`, `message` |
| `model_change` | Model switch event | `id`, `parentId`, `timestamp`, `provider`, `modelId` |
| `thinking_level_change` | Thinking mode toggle | `id`, `parentId`, `timestamp`, `thinkingLevel` |
| `custom` | Custom event types | `id`, `parentId`, `timestamp`, `customType`, `data` |

### 2.3 Message Structure

```typescript
interface MessageEvent {
  type: "message";
  id: string;           // Short ID (8 chars)
  parentId: string | null;
  timestamp: string;    // ISO 8601
  message: {
    role: "user" | "assistant" | "toolResult";
    content: ContentBlock[];
    timestamp?: number;  // Unix ms
    api?: string;
    provider?: string;
    model?: string;
    usage?: NormalizedUsage;
    stopReason?: string;
  };
}
```

---

## 3. Field Mapping

### 3.1 Fields to PRESERVE (Must Keep)

| Source Field | Target Field | Notes |
|--------------|--------------|-------|
| `type` | `type` | Direct copy |
| `id` | `id` | Direct copy (short ID) |
| `parentId` | `parentId` | Direct copy |
| `timestamp` | `timestamp` | **Preserve original ISO 8601** |
| `message.role` | `message.role` | Direct copy |
| `message.content` | `message.content` | **Preserve full content** |
| `message.timestamp` | `message.timestamp` | **Preserve Unix ms** |
| `session.version` | `session.version` | Direct copy (3) |
| `session.id` | `session.id` | **Session UUID** |
| `session.cwd` | `session.cwd` | Working directory |

### 3.2 Fields to PRESERVE (Metadata)

| Source Field | Target Field | Notes |
|--------------|--------------|-------|
| `message.provider` | `message.provider` | Model provider |
| `message.model` | `message.model` | Model ID |
| `message.api` | `message.api` | API type |
| `message.usage` | `message.usage` | Token usage |
| `message.stopReason` | `message.stopReason` | Stop reason |
| `model_change.provider` | `model_change.provider` | Direct copy |
| `model_change.modelId` | `model_change.modelId` | Direct copy |
| `thinking_level_change.thinkingLevel` | `thinking_level_change.thinkingLevel` | Direct copy |
| `custom.customType` | `custom.customType` | Direct copy |
| `custom.data` | `custom.data` | Direct copy |

### 3.3 Fields to DOWNGRADE (Optional/Lossy)

| Source Field | Target Field | Notes |
|--------------|--------------|-------|
| `message.cost` | `message.usage.cost` | May need recalculation |
| Large text content | Truncated | Keep first 100KB per block |
| Binary attachments | Base64 or reference | Preserve if <10MB |

### 3.4 Fields to DROP

| Field | Reason |
|-------|--------|
| Internal caches | Regenerate on import |
| Temp files | Not transferable |
| Absolute paths (some) | May need adjustment |

---

## 4. Idempotency & Deduplication

### 4.1 Idempotency Keys

**Primary Key**: `{sessionId}#{eventId}`

```typescript
function idempotencyKey(sessionId: string, eventId: string): string {
  return `${sessionId}#${eventId}`;
}
```

**Dedup Check**: Before inserting, check if key exists in target store.

### 4.2 Session-Level Dedup

```typescript
function sessionFingerprint(session: SessionEvent): string {
  return `${session.id}:${session.timestamp}:${session.cwd}`;
}
```

### 4.3 Event-Level Dedup

```typescript
function eventFingerprint(event: Event): string {
  // Hash: type + id + parentId + timestamp + role hash
  const content = JSON.stringify({
    type: event.type,
    id: event.id,
    parentId: event.parentId,
    timestamp: event.timestamp,
    roleHash: hashRole(event.message?.role)
  });
  return sha256(content).slice(0, 16);
}
```

### 4.4 Conflict Resolution

| Conflict Type | Resolution |
|---------------|------------|
| Duplicate session ID | **Skip** (already imported) |
| Duplicate event ID in same session | **Skip** (already imported) |
| Same fingerprint, different content | **Keep both** (flag for review) |
| Missing parentId | Set to `null` (root event) |
| Orphaned events | Link to session root |

---

## 5. Timestamp Fidelity

### 5.1 Timestamp Sources

| Source | Format | Precision |
|--------|--------|-----------|
| `timestamp` (event level) | ISO 8601 | Milliseconds |
| `message.timestamp` | Unix ms | Milliseconds |
| `custom.data.timestamp` | Unix ms | Milliseconds |

### 5.2 Timestamp Preservation Rules

1. **NEVER modify original timestamps**
2. Store both ISO 8601 and Unix ms when available
3. If only one exists, derive the other:
   ```typescript
   function deriveTimestamp(event: Event): { iso: string; unixMs: number } {
     if (event.timestamp && !event.message?.timestamp) {
       return {
         iso: event.timestamp,
         unixMs: new Date(event.timestamp).getTime()
       };
     }
     if (event.message?.timestamp && !event.timestamp) {
       return {
         iso: new Date(event.message.timestamp).toISOString(),
         unixMs: event.message.timestamp
       };
     }
     return {
       iso: event.timestamp,
       unixMs: event.message.timestamp
     };
   }
   ```

### 5.3 Event Ordering

**Primary Sort**: `timestamp` (ISO 8601) ascending  
**Secondary Sort**: `id` (stable for same timestamp)

```typescript
function sortEvents(events: Event[]): Event[] {
  return events.sort((a, b) => {
    const timeCompare = a.timestamp.localeCompare(b.timestamp);
    if (timeCompare !== 0) return timeCompare;
    return a.id.localeCompare(b.id);
  });
}
```

---

## 6. External ID & Metadata Strategy

### 6.1 External ID

**Purpose**: Link imported events to original source

**Format**: `openclaw:legacy:{sessionId}:{eventId}`

```typescript
interface ImportedEvent {
  // ... original fields
  external_id: string;  // openclaw:legacy:uuid:shortid
  metadata: {
    source: "openclaw-legacy";
    imported_at: string;  // ISO 8601
    original_path: string;  // Original file path
    fingerprint: string;  // For dedup
  };
}
```

### 6.2 Metadata Fields

```typescript
interface ImportMetadata {
  source: "openclaw-legacy";
  version: 3;
  imported_at: string;
  original_session_file: string;
  original_agent_id: string;
  fingerprint: string;
  import_job_id: string;
}
```

---

## 7. Import Algorithm

### 7.1 High-Level Flow

```
1. Scan source directory for JSONL files
2. For each file:
   a. Parse session header (first line)
   b. Check idempotency key
   c. If exists: SKIP
   d. If not: Parse all events
3. For each event:
   a. Validate required fields
   b. Generate fingerprint
   c. Check dedup
   d. Map fields to target schema
   e. Add external_id and metadata
   f. Write to target
4. Verify import (count check)
5. Generate import report
```

### 7.2 Batch Import (Recommended)

```typescript
interface ImportJob {
  id: string;
  started_at: string;
  source_dir: string;
  target_dir: string;
  status: "running" | "completed" | "failed";
  stats: {
    files_scanned: number;
    sessions_imported: number;
    sessions_skipped: number;
    events_imported: number;
    events_skipped: number;
    errors: ErrorReport[];
  };
}
```

---

## 8. Validation Strategy

### 8.1 Pre-Import Validation

| Check | Action |
|-------|--------|
| Valid JSONL | Skip malformed lines |
| Required fields present | Skip invalid events |
| Valid timestamp format | Skip if unparseable |
| Valid session ID format | Skip if not UUID |

### 8.2 Post-Import Validation

```typescript
interface ValidationResult {
  session_id: string;
  checks: {
    event_count_match: boolean;  // Source == Target
    parent_chain_intact: boolean;  // All parentIds exist
    timestamp_order_preserved: boolean;  // Events sorted
    content_integrity: boolean;  // Spot check hashes
  };
  errors: ValidationError[];
}
```

### 8.3 Semantic Equivalence Tests

| Test | Method |
|------|--------|
| Event count | Source count == Target count |
| Message roles | Same role distribution |
| Tool call names | Same tool set |
| Time range | Same first/last timestamp |
| Content hash | Spot check 10 random events |

---

## 9. Sample Migration Script

```python
#!/usr/bin/env python3
"""
Legacy Memory Import - Sample Script
For codex-2 implementation reference only
"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ImportMetadata:
    source: str = "openclaw-legacy"
    version: int = 3
    imported_at: str = ""
    original_session_file: str = ""
    original_agent_id: str = ""
    fingerprint: str = ""
    import_job_id: str = ""


@dataclass
class ImportResult:
    session_id: str
    events_imported: int
    events_skipped: int
    errors: List[str] = field(default_factory=list)


def generate_fingerprint(event: Dict) -> str:
    """Generate dedup fingerprint for event"""
    content = json.dumps({
        "type": event.get("type"),
        "id": event.get("id"),
        "parentId": event.get("parentId"),
        "timestamp": event.get("timestamp"),
        "role": event.get("message", {}).get("role", "")
    }, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def generate_external_id(session_id: str, event_id: str) -> str:
    """Generate external ID for imported event"""
    return f"openclaw:legacy:{session_id}:{event_id}"


def validate_event(event: Dict) -> Optional[str]:
    """Validate event has required fields. Returns error or None."""
    required = ["type", "id", "timestamp"]
    for field in required:
        if field not in event:
            return f"Missing required field: {field}"
    
    if event["type"] == "message":
        if "message" not in event:
            return "Missing message field for message event"
        if "role" not in event["message"]:
            return "Missing role in message"
    
    return None


def parse_jsonl_file(filepath: Path) -> tuple[Optional[Dict], List[Dict], List[str]]:
    """Parse JSONL file. Returns (session_header, events, errors)"""
    session_header = None
    events = []
    errors = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: JSON parse error: {e}")
                continue
            
            # First valid event should be session header
            if session_header is None and event.get("type") == "session":
                session_header = event
            else:
                validation_error = validate_event(event)
                if validation_error:
                    errors.append(f"Line {line_num}: {validation_error}")
                else:
                    events.append(event)
    
    return session_header, events, errors


def import_session(
    source_path: Path,
    target_dir: Path,
    job_id: str,
    existing_keys: set
) -> ImportResult:
    """Import a single session file"""
    
    session_header, events, parse_errors = parse_jsonl_file(source_path)
    
    if not session_header:
        return ImportResult(
            session_id="unknown",
            events_imported=0,
            events_skipped=0,
            errors=["No session header found"]
        )
    
    session_id = session_header["id"]
    result = ImportResult(
        session_id=session_id,
        events_imported=0,
        events_skipped=0,
        errors=parse_errors
    )
    
    # Check idempotency
    session_key = f"session:{session_id}"
    if session_key in existing_keys:
        result.errors.append(f"Session {session_id} already imported")
        return result
    
    # Prepare target file
    target_path = target_dir / f"{session_id}.imported.jsonl"
    imported_events = []
    
    # Add session header with metadata
    header_with_meta = {
        **session_header,
        "external_id": generate_external_id(session_id, session_header["id"]),
        "metadata": asdict(ImportMetadata(
            imported_at=datetime.utcnow().isoformat() + "Z",
            original_session_file=str(source_path),
            import_job_id=job_id
        ))
    }
    imported_events.append(header_with_meta)
    
    # Process events
    for event in events:
        event_id = event["id"]
        idempotency_key = f"{session_id}#{event_id}"
        
        if idempotency_key in existing_keys:
            result.events_skipped += 1
            continue
        
        # Add metadata
        event_with_meta = {
            **event,
            "external_id": generate_external_id(session_id, event_id),
            "metadata": asdict(ImportMetadata(
                imported_at=datetime.utcnow().isoformat() + "Z",
                original_session_file=str(source_path),
                import_job_id=job_id,
                fingerprint=generate_fingerprint(event)
            ))
        }
        
        imported_events.append(event_with_meta)
        result.events_imported += 1
        existing_keys.add(idempotency_key)
    
    # Write target file
    with open(target_path, 'w', encoding='utf-8') as f:
        for event in imported_events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    return result


def validate_import(source_path: Path, target_path: Path) -> Dict:
    """Validate imported session matches source"""
    _, source_events, _ = parse_jsonl_file(source_path)
    
    with open(target_path, 'r', encoding='utf-8') as f:
        target_events = [json.loads(line) for line in f if line.strip()]
    
    # Check counts (accounting for header)
    source_count = len(source_events)
    target_count = len(target_events) - 1  # Minus header
    
    return {
        "source_event_count": source_count,
        "target_event_count": target_count,
        "count_match": source_count == target_count,
        "valid": source_count == target_count
    }


# Main entry point for batch import
def run_import_job(
    source_dir: Path,
    target_dir: Path,
    job_id: str
) -> Dict:
    """Run batch import job"""
    results = []
    existing_keys = set()
    
    for jsonl_file in source_dir.glob("**/*.jsonl"):
        if ".reset." in jsonl_file.name or ".deleted." in jsonl_file.name:
            continue
        
        result = import_session(jsonl_file, target_dir, job_id, existing_keys)
        results.append(asdict(result))
    
    return {
        "job_id": job_id,
        "total_sessions": len(results),
        "total_events_imported": sum(r["events_imported"] for r in results),
        "total_errors": sum(len(r["errors"]) for r in results),
        "results": results
    }


if __name__ == "__main__":
    import sys
    
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".openclaw" / "agents" / "agent" / "sessions"
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./imported_sessions")
    job_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    target.mkdir(parents=True, exist_ok=True)
    
    report = run_import_job(source, target, job_id)
    print(json.dumps(report, indent=2, ensure_ascii=False))
```

---

## 10. Answers to Required Questions

### 10.1 Which fields MUST be preserved?

**Core Fields (Lossless)**:
- `type`, `id`, `parentId`, `timestamp`
- `session.id`, `session.version`, `session.cwd`
- `message.role`, `message.content`, `message.timestamp`
- `model_change.provider`, `model_change.modelId`
- `thinking_level_change.thinkingLevel`
- `custom.customType`, `custom.data`

**Metadata Fields (Lossless)**:
- `message.provider`, `message.model`, `message.api`
- `message.usage`, `message.stopReason`

### 10.2 Which fields can be downgraded?

- Large text content (>100KB): Truncate with marker
- Binary attachments: Convert to references if >10MB
- Cost calculations: May need recalculation if provider rates changed

### 10.3 How to handle import conflicts?

| Conflict | Resolution |
|----------|------------|
| Duplicate session | SKIP (already imported) |
| Duplicate event | SKIP (already imported) |
| Missing parentId | Set to `null` |
| Invalid JSON | SKIP line, log error |
| Missing required field | SKIP event, log error |

### 10.4 How to ensure idempotency?

1. **Idempotency Key**: `{sessionId}#{eventId}`
2. **Pre-check**: Query existing keys before insert
3. **Fingerprint**: SHA256 hash for content verification
4. **External ID**: `openclaw:legacy:{sessionId}:{eventId}`
5. **Import metadata**: Track import job, timestamp, source path

### 10.5 How to verify semantic equivalence?

**Automated Checks**:
1. Event count match (source == target)
2. Role distribution match (user/assistant/toolResult counts)
3. Timestamp order preserved (sorted by timestamp)
4. Parent chain intact (all parentIds exist in session)
5. Content hash spot-check (10 random events)

**Manual Review**:
- Import report with error summary
- Flag sessions with >5% skip rate
- Human review of conflict cases

---

## 11. Implementation Notes for codex-2

### 11.1 DO NOT

- Modify `claude_agents.py` or `openclaw.py`
- Touch Telegram channel code
- Implement real-time sync (batch only)
- Block production imports on errors (log and continue)

### 11.2 DO

- Use the sample script as reference
- Add comprehensive logging
- Generate detailed import reports
- Support dry-run mode
- Allow selective session import
- Provide rollback mechanism

### 11.3 Testing

```bash
# Dry run
python migration/import_legacy.py --dry-run ~/.openclaw/agents/agent/sessions ./test_import

# Full import
python migration/import_legacy.py ~/.openclaw/agents/agent/sessions ./imported_sessions

# Validate
python migration/validate_import.py ./imported_sessions
```

---

## 12. Appendix: Event Type Reference

### 12.1 Session Event

```json
{
  "type": "session",
  "version": 3,
  "id": "uuid-v4",
  "timestamp": "2026-03-20T02:38:31.706Z",
  "cwd": "/path/to/workspace"
}
```

### 12.2 Message Event (User)

```json
{
  "type": "message",
  "id": "shortid8",
  "parentId": "previous_id",
  "timestamp": "2026-03-20T02:38:31.734Z",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "..."}],
    "timestamp": 1773974311733
  }
}
```

### 12.3 Message Event (Assistant)

```json
{
  "type": "message",
  "id": "shortid8",
  "parentId": "previous_id",
  "timestamp": "2026-03-20T02:38:36.661Z",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "..."},
      {"type": "toolCall", "id": "call_xxx", "name": "read", "arguments": {...}}
    ],
    "api": "anthropic-messages",
    "provider": "custom-customd2",
    "model": "glm-4.6",
    "usage": {...},
    "stopReason": "toolUse",
    "timestamp": 1773974311734
  }
}
```

### 12.4 Message Event (ToolResult)

```json
{
  "type": "message",
  "id": "shortid8",
  "parentId": "previous_id",
  "timestamp": "2026-03-20T02:38:36.668Z",
  "message": {
    "role": "toolResult",
    "toolCallId": "call_xxx",
    "toolName": "read",
    "content": [{"type": "text", "text": "..."}],
    "isError": false,
    "timestamp": 1773974316667
  }
}
```

### 12.5 Model Change Event

```json
{
  "type": "model_change",
  "id": "shortid8",
  "parentId": null,
  "timestamp": "2026-03-20T02:38:31.728Z",
  "provider": "custom-customd2",
  "modelId": "glm-4.6"
}
```

### 12.6 Thinking Level Change Event

```json
{
  "type": "thinking_level_change",
  "id": "shortid8",
  "parentId": "previous_id",
  "timestamp": "2026-03-20T02:38:31.728Z",
  "thinkingLevel": "off"
}
```

### 12.7 Custom Event

```json
{
  "type": "custom",
  "customType": "model-snapshot",
  "data": {...},
  "id": "shortid8",
  "parentId": "previous_id",
  "timestamp": "2026-03-20T02:38:31.730Z"
}
```

---

## 13. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-03-26 | glm-5-2 | Initial draft |

---

**End of Specification**
