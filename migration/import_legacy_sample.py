#!/usr/bin/env python3
"""
Legacy Memory Import - Sample Implementation

For codex-2 reference only. This is a MINIMAL prototype to demonstrate
the core import logic. Production implementation should add:

- Progress reporting
- Detailed logging
- Error recovery
- Rollback mechanism
- Dry-run mode
- Batch size limits
- Memory optimization for large sessions

Usage:
    python3 migration/import_legacy_sample.py <source_dir> <target_dir>
"""

import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set


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
    existing_keys: Set[str],
    dry_run: bool = False
) -> Dict:
    """Import a single session file"""
    
    session_header, events, parse_errors = parse_jsonl_file(source_path)
    
    if not session_header:
        return {
            "session_id": "unknown",
            "events_imported": 0,
            "events_skipped": 0,
            "success": False,
            "errors": ["No session header found"] + parse_errors
        }
    
    session_id = session_header["id"]
    result = {
        "session_id": session_id,
        "source_file": str(source_path),
        "events_imported": 0,
        "events_skipped": 0,
        "success": True,
        "errors": parse_errors
    }
    
    # Check idempotency
    session_key = f"session:{session_id}"
    if session_key in existing_keys:
        result["success"] = False
        result["errors"].append(f"Session {session_id} already imported")
        return result
    
    # Prepare target file
    target_path = target_dir / f"{session_id}.imported.jsonl"
    imported_events = []
    
    # Add session header with metadata
    header_with_meta = {
        **session_header,
        "external_id": generate_external_id(session_id, session_header["id"]),
        "metadata": {
            "source": "openclaw-legacy",
            "version": 3,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "original_session_file": str(source_path),
            "import_job_id": job_id
        }
    }
    imported_events.append(header_with_meta)
    
    # Process events
    for event in events:
        event_id = event["id"]
        idempotency_key = f"{session_id}#{event_id}"
        
        if idempotency_key in existing_keys:
            result["events_skipped"] += 1
            continue
        
        # Add metadata
        event_with_meta = {
            **event,
            "external_id": generate_external_id(session_id, event_id),
            "metadata": {
                "source": "openclaw-legacy",
                "version": 3,
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "original_session_file": str(source_path),
                "import_job_id": job_id,
                "fingerprint": generate_fingerprint(event)
            }
        }
        
        imported_events.append(event_with_meta)
        result["events_imported"] += 1
        existing_keys.add(idempotency_key)
    
    # Write target file (unless dry run)
    if not dry_run:
        with open(target_path, 'w', encoding='utf-8') as f:
            for event in imported_events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    result["target_file"] = str(target_path)
    return result


def run_import_job(
    source_dir: Path,
    target_dir: Path,
    job_id: Optional[str] = None,
    dry_run: bool = False
) -> Dict:
    """Run batch import job"""
    
    if job_id is None:
        job_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    existing_keys = set()
    
    source_files = list(source_dir.glob("**/*.jsonl"))
    total_files = len(source_files)
    
    print(f"Starting import job: {job_id}")
    print(f"Source: {source_dir}")
    print(f"Target: {target_dir}")
    print(f"Files to process: {total_files}")
    print(f"Dry run: {dry_run}")
    print()
    
    for idx, jsonl_file in enumerate(source_files, 1):
        # Skip backup/reset files
        if ".reset." in jsonl_file.name or ".deleted." in jsonl_file.name:
            continue
        
        print(f"[{idx}/{total_files}] Processing {jsonl_file.name}...", end=" ")
        
        result = import_session(jsonl_file, target_dir, job_id, existing_keys, dry_run)
        results.append(result)
        
        if result["success"]:
            print(f"✓ {result['events_imported']} events")
        else:
            print(f"✗ {result['errors'][0] if result['errors'] else 'Unknown error'}")
    
    # Generate summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    summary = {
        "job_id": job_id,
        "dry_run": dry_run,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "total_sessions": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "total_events_imported": sum(r["events_imported"] for r in successful),
        "total_events_skipped": sum(r["events_skipped"] for r in results),
        "results": results
    }
    
    print()
    print("="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Job ID: {job_id}")
    print(f"Total sessions: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Events imported: {summary['total_events_imported']}")
    print(f"Events skipped: {summary['total_events_skipped']}")
    print("="*60)
    
    if failed:
        print()
        print("Failed sessions:")
        for r in failed[:10]:
            print(f"  - {r['session_id']}: {r['errors'][0] if r['errors'] else 'Unknown'}")
    
    return summary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import legacy OpenClaw sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (no writes)
  python3 migration/import_legacy_sample.py ~/.openclaw/agents/agent/sessions ./imported --dry-run
  
  # Actual import
  python3 migration/import_legacy_sample.py ~/.openclaw/agents/agent/sessions ./imported
  
  # Custom job ID
  python3 migration/import_legacy_sample.py ~/.openclaw/agents/agent/sessions ./imported --job-id import_20260326
        """
    )
    
    parser.add_argument("source_dir", help="Source directory with JSONL session files")
    parser.add_argument("target_dir", help="Target directory for imported sessions")
    parser.add_argument("--job-id", "-j", help="Custom job ID")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Dry run (no writes)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    source_dir = Path(args.source_dir)
    target_dir = Path(args.target_dir)
    
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        sys.exit(1)
    
    summary = run_import_job(
        source_dir,
        target_dir,
        job_id=args.job_id,
        dry_run=args.dry_run
    )
    
    # Save summary report
    report_path = target_dir / f"import_report_{summary['job_id']}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\nReport saved to: {report_path}")
    
    # Exit with error code if any failures
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
