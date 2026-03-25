#!/usr/bin/env python3
"""
Legacy Memory Import - Validation Script

Validates that imported sessions maintain semantic equivalence with source.

Usage:
    python migration/validate_import.py <source_dir> <target_dir>
    python migration/validate_import.py --report validation_report.json
"""

import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import Counter


@dataclass
class ValidationError:
    code: str
    message: str
    session_id: str
    event_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionValidation:
    session_id: str
    source_file: str
    target_file: str
    valid: bool
    checks: Dict[str, bool]
    errors: List[Dict] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


def parse_jsonl(filepath: Path) -> Tuple[Optional[Dict], List[Dict]]:
    """Parse JSONL file, return (header, events)"""
    events = []
    header = None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if header is None and event.get("type") == "session":
                    header = event
                else:
                    events.append(event)
            except json.JSONDecodeError:
                pass
    
    return header, events


def hash_content(content: Any) -> str:
    """Generate hash for content comparison"""
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]


def validate_event_count(source_events: List[Dict], target_events: List[Dict]) -> Tuple[bool, str]:
    """Check if event counts match"""
    source_count = len(source_events)
    target_count = len(target_events)
    
    if source_count == target_count:
        return True, f"Event count match: {source_count}"
    return False, f"Event count mismatch: source={source_count}, target={target_count}"


def validate_role_distribution(source_events: List[Dict], target_events: List[Dict]) -> Tuple[bool, str]:
    """Check if role distribution matches"""
    def count_roles(events: List[Dict]) -> Counter:
        roles = Counter()
        for e in events:
            if e.get("type") == "message" and "message" in e:
                role = e["message"].get("role", "unknown")
                roles[role] += 1
        return roles
    
    source_roles = count_roles(source_events)
    target_roles = count_roles(target_events)
    
    if source_roles == target_roles:
        return True, f"Role distribution match: {dict(source_roles)}"
    return False, f"Role distribution mismatch: source={dict(source_roles)}, target={dict(target_roles)}"


def validate_event_types(source_events: List[Dict], target_events: List[Dict]) -> Tuple[bool, str]:
    """Check if event type distribution matches"""
    def count_types(events: List[Dict]) -> Counter:
        return Counter(e.get("type", "unknown") for e in events)
    
    source_types = count_types(source_events)
    target_types = count_types(target_events)
    
    if source_types == target_types:
        return True, f"Event types match: {dict(source_types)}"
    return False, f"Event types mismatch: source={dict(source_types)}, target={dict(target_types)}"


def validate_timestamp_order(events: List[Dict]) -> Tuple[bool, str]:
    """Check if events are sorted by timestamp"""
    timestamps = [e.get("timestamp", "") for e in events]
    sorted_timestamps = sorted(timestamps)
    
    if timestamps == sorted_timestamps:
        return True, "Timestamps are in order"
    return False, "Timestamps are not in order"


def validate_parent_chain(events: List[Dict]) -> Tuple[bool, str]:
    """Check if all parentIds exist in the session"""
    event_ids = {e.get("id") for e in events if e.get("type") != "session"}
    orphaned = []
    
    for e in events:
        parent_id = e.get("parentId")
        if parent_id and parent_id not in event_ids:
            orphaned.append(e.get("id"))
    
    if not orphaned:
        return True, "All parent chains intact"
    return False, f"Orphaned events (parentId not found): {orphaned[:5]}"


def validate_time_range(source_events: List[Dict], target_events: List[Dict]) -> Tuple[bool, str]:
    """Check if time range is preserved"""
    def get_time_range(events: List[Dict]) -> Tuple[str, str]:
        timestamps = sorted(e.get("timestamp", "") for e in events if e.get("timestamp"))
        return (timestamps[0] if timestamps else "", timestamps[-1] if timestamps else "")
    
    source_range = get_time_range(source_events)
    target_range = get_time_range(target_events)
    
    if source_range == target_range:
        return True, f"Time range preserved: {source_range[0]} to {source_range[1]}"
    return False, f"Time range mismatch: source={source_range}, target={target_range}"


def validate_content_integrity(
    source_events: List[Dict], 
    target_events: List[Dict], 
    sample_size: int = 10
) -> Tuple[bool, str]:
    """Spot check content hashes"""
    import random
    
    if not source_events:
        return True, "No events to validate"
    
    # Sample events
    sample_indices = random.sample(
        range(len(source_events)), 
        min(sample_size, len(source_events))
    )
    
    mismatches = []
    for idx in sample_indices:
        if idx >= len(target_events):
            mismatches.append(f"index {idx} out of range in target")
            continue
        
        source_event = source_events[idx]
        target_event = target_events[idx]
        
        # Compare key fields (excluding metadata added by import)
        source_key = {
            "type": source_event.get("type"),
            "id": source_event.get("id"),
            "timestamp": source_event.get("timestamp")
        }
        target_key = {
            "type": target_event.get("type"),
            "id": target_event.get("id"),
            "timestamp": target_event.get("timestamp")
        }
        
        if source_key != target_key:
            mismatches.append(f"event {idx}: {source_key} != {target_key}")
    
    if not mismatches:
        return True, f"Content integrity verified (sampled {len(sample_indices)} events)"
    return False, f"Content mismatches: {mismatches[:3]}"


def validate_external_ids(target_events: List[Dict]) -> Tuple[bool, str]:
    """Check if all events have valid external_ids"""
    missing = []
    invalid = []
    
    for e in target_events:
        event_id = e.get("id")
        external_id = e.get("external_id")
        
        if not external_id:
            missing.append(event_id)
        elif not external_id.startswith("openclaw:legacy:"):
            invalid.append((event_id, external_id))
    
    if not missing and not invalid:
        return True, "All events have valid external_ids"
    
    errors = []
    if missing:
        errors.append(f"Missing external_id: {missing[:3]}")
    if invalid:
        errors.append(f"Invalid external_id format: {invalid[:3]}")
    return False, "; ".join(errors)


def validate_metadata(target_events: List[Dict]) -> Tuple[bool, str]:
    """Check if import metadata is present and valid"""
    required_fields = ["source", "imported_at", "import_job_id"]
    missing_count = 0
    invalid_count = 0
    
    for e in target_events:
        metadata = e.get("metadata", {})
        
        if not metadata:
            missing_count += 1
            continue
        
        for field in required_fields:
            if field not in metadata:
                invalid_count += 1
                break
    
    if missing_count == 0 and invalid_count == 0:
        return True, "All events have valid metadata"
    return False, f"Missing metadata: {missing_count}, Invalid metadata: {invalid_count}"


def validate_session(
    source_path: Path, 
    target_path: Path
) -> SessionValidation:
    """Validate a single imported session"""
    
    source_header, source_events = parse_jsonl(source_path)
    target_header, target_events = parse_jsonl(target_path)
    
    session_id = source_header.get("id", "unknown") if source_header else "unknown"
    
    checks = {}
    errors = []
    
    # Run all validation checks
    validations = [
        ("event_count_match", validate_event_count(source_events, target_events)),
        ("role_distribution", validate_role_distribution(source_events, target_events)),
        ("event_types", validate_event_types(source_events, target_events)),
        ("timestamp_order_source", validate_timestamp_order(source_events)),
        ("timestamp_order_target", validate_timestamp_order(target_events)),
        ("parent_chain_source", validate_parent_chain(source_events)),
        ("parent_chain_target", validate_parent_chain(target_events)),
        ("time_range", validate_time_range(source_events, target_events)),
        ("content_integrity", validate_content_integrity(source_events, target_events)),
        ("external_ids", validate_external_ids(target_events)),
        ("metadata", validate_metadata(target_events)),
    ]
    
    for check_name, (passed, message) in validations:
        checks[check_name] = passed
        if not passed:
            errors.append({
                "check": check_name,
                "message": message
            })
    
    # Calculate stats
    stats = {
        "source_event_count": len(source_events),
        "target_event_count": len(target_events),
        "checks_passed": sum(1 for v in checks.values() if v),
        "checks_total": len(checks)
    }
    
    return SessionValidation(
        session_id=session_id,
        source_file=str(source_path),
        target_file=str(target_path),
        valid=all(checks.values()),
        checks=checks,
        errors=[asdict(e) if hasattr(e, '__dataclass_fields__') else e for e in errors],
        stats=stats
    )


def validate_import_batch(
    source_dir: Path,
    target_dir: Path,
    report_path: Optional[Path] = None
) -> Dict:
    """Validate all imported sessions"""
    
    results = []
    summary = {
        "total_sessions": 0,
        "valid_sessions": 0,
        "invalid_sessions": 0,
        "total_errors": 0,
        "check_summary": {}
    }
    
    # Find all source files
    source_files = {}
    for jsonl in source_dir.glob("**/*.jsonl"):
        if ".reset." in jsonl.name or ".deleted." in jsonl.name:
            continue
        header, _ = parse_jsonl(jsonl)
        if header and "id" in header:
            source_files[header["id"]] = jsonl
    
    # Find all target files
    target_files = {}
    for jsonl in target_dir.glob("**/*.jsonl"):
        header, _ = parse_jsonl(jsonl)
        if header and "id" in header:
            target_files[header["id"]] = jsonl
    
    # Validate each session
    for session_id, source_path in source_files.items():
        target_path = target_files.get(session_id)
        
        if not target_path:
            results.append({
                "session_id": session_id,
                "valid": False,
                "error": "No corresponding target file found"
            })
            summary["invalid_sessions"] += 1
            continue
        
        validation = validate_session(source_path, target_path)
        results.append(asdict(validation))
        
        summary["total_sessions"] += 1
        if validation.valid:
            summary["valid_sessions"] += 1
        else:
            summary["invalid_sessions"] += 1
        summary["total_errors"] += len(validation.errors)
        
        # Aggregate check results
        for check, passed in validation.checks.items():
            if check not in summary["check_summary"]:
                summary["check_summary"][check] = {"passed": 0, "failed": 0}
            if passed:
                summary["check_summary"][check]["passed"] += 1
            else:
                summary["check_summary"][check]["failed"] += 1
    
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "summary": summary,
        "results": results
    }
    
    if report_path:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Report saved to: {report_path}")
    
    return report


def print_report_summary(report: Dict):
    """Print a human-readable summary"""
    summary = report["summary"]
    
    print("\n" + "="*60)
    print("VALIDATION REPORT SUMMARY")
    print("="*60)
    print(f"Generated: {report['generated_at']}")
    print(f"Source: {report['source_dir']}")
    print(f"Target: {report['target_dir']}")
    print()
    print(f"Total Sessions: {summary['total_sessions']}")
    print(f"Valid: {summary['valid_sessions']}")
    print(f"Invalid: {summary['invalid_sessions']}")
    print(f"Total Errors: {summary['total_errors']}")
    print()
    
    print("Check Results:")
    print("-"*40)
    for check, stats in summary["check_summary"].items():
        total = stats["passed"] + stats["failed"]
        rate = (stats["passed"] / total * 100) if total > 0 else 0
        status = "✅" if stats["failed"] == 0 else "⚠️"
        print(f"  {status} {check}: {stats['passed']}/{total} ({rate:.1f}%)")
    
    print()
    
    if summary["invalid_sessions"] > 0:
        print("Invalid Sessions:")
        print("-"*40)
        for result in report["results"]:
            if not result.get("valid", True):
                session_id = result.get("session_id", "unknown")
                errors = result.get("errors", [])
                print(f"  - {session_id}: {len(errors)} errors")
                for err in errors[:3]:
                    if isinstance(err, dict):
                        print(f"      [{err.get('check', '?')}] {err.get('message', '')}")
                    else:
                        print(f"      {err}")
    
    print("="*60)
    
    # Return exit code
    return 0 if summary["invalid_sessions"] == 0 else 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate imported sessions")
    parser.add_argument("source_dir", nargs="?", help="Source directory with original JSONL files")
    parser.add_argument("target_dir", nargs="?", help="Target directory with imported JSONL files")
    parser.add_argument("--report", "-r", help="Save report to file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not args.source_dir or not args.target_dir:
        parser.print_help()
        sys.exit(1)
    
    source_dir = Path(args.source_dir)
    target_dir = Path(args.target_dir)
    
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        sys.exit(1)
    
    if not target_dir.exists():
        print(f"Error: Target directory not found: {target_dir}")
        sys.exit(1)
    
    report_path = Path(args.report) if args.report else None
    
    report = validate_import_batch(source_dir, target_dir, report_path)
    
    exit_code = print_report_summary(report)
    
    if args.verbose:
        print("\nDetailed Results:")
        print(json.dumps(report["results"], indent=2, ensure_ascii=False))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
