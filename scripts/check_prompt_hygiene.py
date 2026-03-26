#!/usr/bin/env python3
"""Prompt hygiene audit for ``src/``.

This is a read-only checker that looks for three kinds of issues:

1. forbidden or factory-like terms in comments, docstrings, and string literals
2. placeholder-heavy text such as TODO / TBD / placeholder
3. repeated boilerplate comment/docstring lines

It writes both a human-readable report and a JSON report so the results can
be reviewed by a person or consumed by tooling.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_EXTENSIONS = (".py",)
DEFAULT_OUTPUT_DIR = Path("logs/audit/prompt_hygiene")
DEFAULT_FORBIDDEN_TERMS = (
    "工厂化",
    "流水线",
    "批量化",
    "标准化生产",
    "代工厂",
    "平替",
    "廉价",
    "清仓",
    "甩卖",
    "批发",
    "模板化",
    "boilerplate",
)
DEFAULT_PLACEHOLDER_TERMS = (
    "TODO",
    "FIXME",
    "TBD",
    "placeholder",
    "待实现",
    "待补充",
    "待完善",
    "lorem ipsum",
)
POLICY_PATH_HINTS = (
    "brand_auditor.py",
    "business_enforcer.py",
    "prompt_builder.py",
    "malu_brand_graph.py",
    "brand_graph_tools.py",
)

TRANSLATION_TABLE = str.maketrans(
    {
        "，": " ",
        "。": " ",
        "！": " ",
        "？": " ",
        "；": " ",
        "：": " ",
        ",": " ",
        ".": " ",
        "!": " ",
        "?": " ",
        ";": " ",
        ":": " ",
        "(": " ",
        ")": " ",
        "[": " ",
        "]": " ",
        "{": " ",
        "}": " ",
        "<": " ",
        ">": " ",
        "\"": " ",
        "'": " ",
        "`": " ",
        "“": " ",
        "”": " ",
        "‘": " ",
        "’": " ",
        "|": " ",
        "、": " ",
    }
)


@dataclass(frozen=True)
class Fragment:
    path: str
    line: int
    column: int
    kind: str
    text: str


@dataclass(frozen=True)
class Finding:
    category: str
    severity: str
    path: str
    line: int
    column: int
    kind: str
    match: str
    excerpt: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "kind": self.kind,
            "match": self.match,
            "excerpt": self.excerpt,
            "message": self.message,
        }


@dataclass(frozen=True)
class RepeatedPhraseGroup:
    phrase: str
    count: int
    locations: list[Fragment] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "phrase": self.phrase,
            "count": self.count,
            "locations": [
                {
                    "path": location.path,
                    "line": location.line,
                    "column": location.column,
                    "kind": location.kind,
                }
                for location in self.locations
            ],
        }


@dataclass
class HygieneReport:
    root: str
    generated_at: str
    files_scanned: int
    comment_fragments: int
    docstring_fragments: int
    string_fragments: int
    findings: list[Finding] = field(default_factory=list)
    repeated_phrases: list[RepeatedPhraseGroup] = field(default_factory=list)
    score: int = 100

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "generated_at": self.generated_at,
            "files_scanned": self.files_scanned,
            "comment_fragments": self.comment_fragments,
            "docstring_fragments": self.docstring_fragments,
            "string_fragments": self.string_fragments,
            "findings": [finding.to_dict() for finding in self.findings],
            "repeated_phrases": [group.to_dict() for group in self.repeated_phrases],
            "score": self.score,
        }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan src/ for prompt hygiene issues.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("src"),
        help="Directory to scan (default: src)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where report.txt and report.json will be written",
    )
    parser.add_argument(
        "--min-repeat",
        type=int,
        default=3,
        help="Minimum times the same comment/docstring line must repeat to count as boilerplate",
    )
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit with code 1 if the scan finds any actionable issues",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(DEFAULT_EXTENSIONS),
        help="File extensions to scan (default: .py)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    root = (repo_root / args.root).resolve() if not args.root.is_absolute() else args.root.resolve()
    output_dir = (repo_root / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir.resolve()

    report = scan_tree(
        root=root,
        extensions=tuple(normalize_extension(ext) for ext in args.extensions),
        min_repeat=max(2, args.min_repeat),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    text_report = render_text_report(report, root=root, output_dir=output_dir)
    text_path = output_dir / "report.txt"
    json_path = output_dir / "report.json"
    text_path.write_text(text_report, encoding="utf-8")
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    actionable_findings = [finding for finding in report.findings if finding.severity != "info"]
    status = "PASS" if not actionable_findings and not report.repeated_phrases else "WARN"
    print(f"[hygiene] status={status} score={report.score}/100 files={report.files_scanned}")
    print(f"[hygiene] report.txt -> {text_path}")
    print(f"[hygiene] report.json -> {json_path}")

    if args.fail_on_findings and (actionable_findings or report.repeated_phrases):
        return 1
    return 0


def scan_tree(
    *,
    root: Path,
    extensions: tuple[str, ...],
    min_repeat: int,
) -> HygieneReport:
    generated_at = datetime.now(timezone.utc).isoformat()
    files = list(iter_source_files(root, extensions))

    findings: list[Finding] = []
    comment_fragments = 0
    docstring_fragments = 0
    string_fragments = 0

    repetition_counter: Counter[str] = Counter()
    repetition_locations: dict[str, list[Fragment]] = defaultdict(list)

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            findings.append(
                Finding(
                    category="parse_error",
                    severity="error",
                    path=relative_display_path(path, root),
                    line=1,
                    column=0,
                    kind="file",
                    match=str(exc),
                    excerpt=shorten_excerpt(str(exc)),
                    message="Unable to read file",
                )
            )
            continue

        comment_fragments_in_file = extract_comment_fragments(text, path, root)
        comment_fragments += len(comment_fragments_in_file)
        for fragment in comment_fragments_in_file:
            findings.extend(scan_fragment(fragment, policy_reference=is_policy_file(path)))
            maybe_track_repetition(fragment, repetition_counter, repetition_locations, min_repeat)

        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            findings.append(
                Finding(
                    category="parse_error",
                    severity="error",
                    path=relative_display_path(path, root),
                    line=exc.lineno or 1,
                    column=exc.offset or 0,
                    kind="syntax",
                    match=exc.msg,
                    excerpt=shorten_excerpt(exc.text or exc.msg),
                    message="Python parse failed",
                )
            )
            continue

        docstring_fragments_in_file, docstring_positions = extract_docstring_fragments(tree, path, root)
        docstring_fragments += len(docstring_fragments_in_file)
        for fragment in docstring_fragments_in_file:
            findings.extend(scan_fragment(fragment, policy_reference=is_policy_file(path)))
            maybe_track_repetition(fragment, repetition_counter, repetition_locations, min_repeat)

        string_fragments_in_file = extract_string_fragments(tree, path, root, docstring_positions)
        string_fragments += len(string_fragments_in_file)
        for fragment in string_fragments_in_file:
            findings.extend(scan_fragment(fragment, policy_reference=is_policy_file(path)))

    repeated_groups = build_repeated_groups(repetition_counter, repetition_locations, min_repeat)
    score = compute_score(findings, repeated_groups, files_scanned=len(files))

    return HygieneReport(
        root=str(root),
        generated_at=generated_at,
        files_scanned=len(files),
        comment_fragments=comment_fragments,
        docstring_fragments=docstring_fragments,
        string_fragments=string_fragments,
        findings=sort_findings(findings),
        repeated_phrases=repeated_groups,
        score=score,
    )


def iter_source_files(root: Path, extensions: tuple[str, ...]) -> list[Path]:
    if not root.exists():
        return []
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in extensions and not any(part.startswith(".") and part not in {".", ".."} for part in path.parts)
    ]
    return sorted(files)


def extract_comment_fragments(text: str, path: Path, root: Path) -> list[Fragment]:
    fragments: list[Fragment] = []
    stream = io.StringIO(text)
    try:
        for token in tokenize.generate_tokens(stream.readline):
            if token.type != tokenize.COMMENT:
                continue
            comment = token.string.lstrip("#").strip()
            if not comment:
                continue
            fragments.append(
                Fragment(
                    path=relative_display_path(path, root),
                    line=token.start[0],
                    column=token.start[1],
                    kind="comment",
                    text=comment,
                )
            )
    except tokenize.TokenError:
        return fragments
    return fragments


def extract_docstring_fragments(
    tree: ast.AST,
    path: Path,
    root: Path,
) -> tuple[list[Fragment], set[tuple[int, int]]]:
    fragments: list[Fragment] = []
    positions: set[tuple[int, int]] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body:
                first = body[0]
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    docstring = first.value.value
                    positions.add((first.value.lineno, first.value.col_offset))
                    for offset, line in enumerate(docstring.splitlines() or [docstring]):
                        cleaned = line.strip()
                        if not cleaned:
                            continue
                        fragments.append(
                            Fragment(
                                path=relative_display_path(path, root),
                                line=first.value.lineno + offset,
                                column=first.value.col_offset,
                                kind="docstring",
                                text=cleaned,
                            )
                        )
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return fragments, positions


def extract_string_fragments(
    tree: ast.AST,
    path: Path,
    root: Path,
    docstring_positions: set[tuple[int, int]],
) -> list[Fragment]:
    fragments: list[Fragment] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if (getattr(node, "lineno", -1), getattr(node, "col_offset", -1)) in docstring_positions:
            continue
        for offset, line in enumerate(node.value.splitlines() or [node.value]):
            cleaned = line.strip()
            if not cleaned:
                continue
            fragments.append(
                Fragment(
                    path=relative_display_path(path, root),
                    line=(getattr(node, "lineno", 1) + offset),
                    column=getattr(node, "col_offset", 0),
                    kind="string",
                    text=cleaned,
                )
            )
    return fragments


def scan_fragment(fragment: Fragment, *, policy_reference: bool) -> list[Finding]:
    findings: list[Finding] = []
    text = fragment.text
    lowered = text.lower()

    for term in DEFAULT_FORBIDDEN_TERMS:
        if term.lower() not in lowered:
            continue
        category = "policy_reference" if policy_reference else "forbidden_term"
        severity = "info" if policy_reference else "warning"
        findings.append(
            Finding(
                category=category,
                severity=severity,
                path=fragment.path,
                line=fragment.line,
                column=fragment.column,
                kind=fragment.kind,
                match=term,
                excerpt=shorten_excerpt(text),
                message=f"Found forbidden term: {term}",
            )
        )

    for term in DEFAULT_PLACEHOLDER_TERMS:
        if term.lower() not in lowered:
            continue
        findings.append(
            Finding(
                category="placeholder_token",
                severity="warning" if not policy_reference else "info",
                path=fragment.path,
                line=fragment.line,
                column=fragment.column,
                kind=fragment.kind,
                match=term,
                excerpt=shorten_excerpt(text),
                message=f"Found placeholder token: {term}",
            )
        )

    return findings


def maybe_track_repetition(
    fragment: Fragment,
    repetition_counter: Counter[str],
    repetition_locations: dict[str, list[Fragment]],
    min_repeat: int,
) -> None:
    if fragment.kind not in {"comment", "docstring"}:
        return
    normalized = normalize_text(fragment.text)
    if not normalized:
        return
    if len(normalized) < 10 and not contains_any(normalized, DEFAULT_PLACEHOLDER_TERMS + DEFAULT_FORBIDDEN_TERMS):
        return
    repetition_counter[normalized] += 1
    repetition_locations[normalized].append(fragment)


def build_repeated_groups(
    repetition_counter: Counter[str],
    repetition_locations: dict[str, list[Fragment]],
    min_repeat: int,
) -> list[RepeatedPhraseGroup]:
    groups: list[RepeatedPhraseGroup] = []
    for phrase, count in repetition_counter.items():
        if count < min_repeat:
            continue
        groups.append(
            RepeatedPhraseGroup(
                phrase=phrase,
                count=count,
                locations=repetition_locations.get(phrase, []),
            )
        )
    groups.sort(key=lambda group: (-group.count, group.phrase))
    return groups


def compute_score(
    findings: list[Finding],
    repeated_groups: list[RepeatedPhraseGroup],
    *,
    files_scanned: int,
) -> int:
    actionable_findings = [finding for finding in findings if finding.severity != "info"]
    parse_errors = sum(1 for finding in actionable_findings if finding.category == "parse_error")

    if files_scanned <= 0:
        return 100

    issue_density = len(actionable_findings) / files_scanned
    repetition_density = len(repeated_groups) / files_scanned

    score = 100
    score -= round(min(80.0, issue_density * 80.0))
    score -= round(min(20.0, repetition_density * 20.0))
    score -= parse_errors * 5
    return max(0, min(100, score))


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda finding: (finding.severity != "error", finding.severity != "warning", finding.path, finding.line, finding.column, finding.category, finding.match))


def normalize_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*([#/*\-]+)\s*", "", cleaned)
    cleaned = cleaned.translate(TRANSLATION_TABLE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip().lower()
    return cleaned


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def normalize_extension(ext: str) -> str:
    ext = ext.strip()
    if not ext:
        return ext
    if not ext.startswith("."):
        ext = f".{ext}"
    return ext


def is_policy_file(path: Path) -> bool:
    lowered = str(path).lower()
    return any(hint in lowered for hint in POLICY_PATH_HINTS)


def relative_display_path(path: Path, root: Path) -> str:
    display_root = root.parent if root.parent != root else root
    try:
        return str(path.relative_to(display_root))
    except Exception:
        return str(path)


def shorten_excerpt(text: str, width: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) <= width:
        return compact
    return compact[: width - 1] + "…"


def render_text_report(report: HygieneReport, *, root: Path, output_dir: Path) -> str:
    lines: list[str] = []
    lines.append("# Prompt Hygiene Report")
    lines.append("")
    lines.append(f"- root: {report.root}")
    lines.append(f"- generated_at: {report.generated_at}")
    lines.append(f"- files_scanned: {report.files_scanned}")
    lines.append(f"- comment_fragments: {report.comment_fragments}")
    lines.append(f"- docstring_fragments: {report.docstring_fragments}")
    lines.append(f"- string_fragments: {report.string_fragments}")
    lines.append(f"- findings: {len([f for f in report.findings if f.severity != 'info'])}")
    lines.append(f"- policy_references: {len([f for f in report.findings if f.category == 'policy_reference'])}")
    lines.append(f"- repeated_groups: {len(report.repeated_phrases)}")
    lines.append(f"- score: {report.score}/100")
    lines.append("")

    sections = (
        ("errors", [f for f in report.findings if f.severity == "error"]),
        ("warnings", [f for f in report.findings if f.severity == "warning"]),
        ("policy references", [f for f in report.findings if f.category == "policy_reference"]),
        ("info", [f for f in report.findings if f.severity == "info" and f.category != "policy_reference"]),
    )

    for title, items in sections:
        if not items:
            continue
        lines.append(f"## {title}")
        for finding in items[:15]:
            lines.append(
                f"- {finding.path}:{finding.line}:{finding.column} "
                f"[{finding.category}] {finding.match} | {finding.excerpt}"
            )
        if len(items) > 15:
            lines.append(f"- ... {len(items) - 15} more")
        lines.append("")

    if report.repeated_phrases:
        lines.append("## repeated comment/docstring phrases")
        for group in report.repeated_phrases[:15]:
            lines.append(f"- {group.phrase!r} x{group.count}")
            for location in group.locations[:5]:
                lines.append(f"  - {location.path}:{location.line}:{location.column} ({location.kind})")
            if len(group.locations) > 5:
                lines.append(f"  - ... {len(group.locations) - 5} more locations")
        if len(report.repeated_phrases) > 15:
            lines.append(f"- ... {len(report.repeated_phrases) - 15} more groups")
        lines.append("")

    lines.append("## notes")
    lines.append("- This audit is read-only and only scans source text under the requested root.")
    lines.append("- Policy files are downgraded to info so the report stays focused on application hygiene.")
    lines.append(f"- Text report: {output_dir / 'report.txt'}")
    lines.append(f"- JSON report: {output_dir / 'report.json'}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
