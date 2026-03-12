#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS anvil_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  phase TEXT NOT NULL CHECK(phase IN ('baseline','after','review')),
  check_name TEXT NOT NULL,
  tool TEXT NOT NULL,
  command TEXT,
  exit_code INTEGER,
  output_snippet TEXT,
  passed INTEGER NOT NULL CHECK(passed IN (0,1)),
  ts DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

VALID_PHASES = ("baseline", "after", "review")
DEFAULT_DB_PATH = Path(".anvil/anvil.db")
DEFAULT_MAX_OUTPUT = 1200
DEFAULT_SHELL = "/bin/zsh"


def default_db_path() -> Path:
    return DEFAULT_DB_PATH


def ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA_SQL)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:64] or "task"


def compact_output(text: str, max_output: int) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if len(stripped) <= max_output:
        return stripped
    head = max_output // 3
    tail = max_output - head - 3
    return f"{stripped[:head]}...{stripped[-tail:]}"


def markdown_escape(value: str | None, limit: int = 160) -> str:
    if not value:
        return ""
    flattened = " ".join(value.split())
    if len(flattened) > limit:
        flattened = f"{flattened[: limit - 3]}..."
    return flattened.replace("|", "\\|")


def record_row(
    db_path: Path,
    task_id: str,
    phase: str,
    check_name: str,
    tool: str,
    command: str | None,
    exit_code: int | None,
    passed: int,
    output_snippet: str,
) -> None:
    ensure_db(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO anvil_checks (
              task_id,
              phase,
              check_name,
              tool,
              command,
              exit_code,
              output_snippet,
              passed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                phase,
                check_name,
                tool,
                command,
                exit_code,
                output_snippet,
                passed,
            ),
        )
        connection.commit()


def fetch_rows(db_path: Path, task_id: str, phase: str | None = None) -> list[sqlite3.Row]:
    ensure_db(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        if phase:
            cursor = connection.execute(
                """
                SELECT id, phase, check_name, tool, command, exit_code, passed, output_snippet, ts
                FROM anvil_checks
                WHERE task_id = ? AND phase = ?
                ORDER BY id
                """,
                (task_id, phase),
            )
        else:
            cursor = connection.execute(
                """
                SELECT id, phase, check_name, tool, command, exit_code, passed, output_snippet, ts
                FROM anvil_checks
                WHERE task_id = ?
                ORDER BY id
                """,
                (task_id,),
            )
        return cursor.fetchall()


def fetch_count(db_path: Path, task_id: str, phase: str | None = None, passed_only: bool = False) -> int:
    ensure_db(db_path)
    clauses = ["task_id = ?"]
    params: list[object] = [task_id]
    if phase:
        clauses.append("phase = ?")
        params.append(phase)
    if passed_only:
        clauses.append("passed = 1")
    where_clause = " AND ".join(clauses)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            f"SELECT COUNT(*) FROM anvil_checks WHERE {where_clause}",
            params,
        )
        count = cursor.fetchone()
    return int(count[0]) if count else 0


def fetch_regressions(db_path: Path, task_id: str) -> list[sqlite3.Row]:
    ensure_db(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            """
            WITH baseline_latest AS (
              SELECT check_name, passed
              FROM anvil_checks
              WHERE task_id = ? AND phase = 'baseline'
              AND id IN (
                SELECT MAX(id)
                FROM anvil_checks
                WHERE task_id = ? AND phase = 'baseline'
                GROUP BY check_name
              )
            ),
            after_latest AS (
              SELECT check_name, passed, output_snippet
              FROM anvil_checks
              WHERE task_id = ? AND phase = 'after'
              AND id IN (
                SELECT MAX(id)
                FROM anvil_checks
                WHERE task_id = ? AND phase = 'after'
                GROUP BY check_name
              )
            )
            SELECT
              after_latest.check_name,
              baseline_latest.passed AS baseline_passed,
              after_latest.passed AS after_passed,
              after_latest.output_snippet
            FROM after_latest
            JOIN baseline_latest USING (check_name)
            WHERE baseline_latest.passed = 1 AND after_latest.passed = 0
            ORDER BY after_latest.check_name
            """,
            (task_id, task_id, task_id, task_id),
        )
        return cursor.fetchall()


def render_phase_table(title: str, rows: list[sqlite3.Row]) -> str:
    lines = [f"### {title}"]
    if not rows:
        lines.append("None recorded.")
        return "\n".join(lines)

    lines.extend(
        [
            "| Check | Result | Command | Detail |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        result = "pass" if row["passed"] else "fail"
        exit_code = "" if row["exit_code"] is None else f"exit {row['exit_code']}"
        detail = markdown_escape(row["output_snippet"])
        if exit_code and detail:
            detail = f"{exit_code}; {detail}"
        elif exit_code:
            detail = exit_code
        lines.append(
            f"| `{row['check_name']}` | {result} | `{markdown_escape(row['command'])}` | {detail} |"
        )
    return "\n".join(lines)


def render_review_table(rows: list[sqlite3.Row]) -> str:
    lines = ["### Adversarial Review"]
    if not rows:
        lines.append("None recorded.")
        return "\n".join(lines)

    lines.extend(
        [
            "| Verdict | Findings |",
            "| --- | --- |",
        ]
    )
    for row in rows:
        verdict = "pass" if row["passed"] else "fail"
        findings = markdown_escape(row["output_snippet"], limit=240)
        lines.append(f"| `{row['check_name']}` ({verdict}) | {findings} |")
    return "\n".join(lines)


def render_regressions(rows: list[sqlite3.Row]) -> str:
    lines = ["### Regressions"]
    if not rows:
        lines.append("None detected.")
        return "\n".join(lines)

    for row in rows:
        detail = markdown_escape(row["output_snippet"], limit=180)
        suffix = f" - {detail}" if detail else ""
        lines.append(f"- `{row['check_name']}` passed at baseline and failed after changes{suffix}")
    return "\n".join(lines)


def command_init(args: argparse.Namespace) -> int:
    ensure_db(args.db)
    print(args.db)
    return 0


def command_task_id(args: argparse.Namespace) -> int:
    print(slugify(args.text))
    return 0


def command_record(args: argparse.Namespace) -> int:
    output = args.output or ""
    if args.output_file:
        output = Path(args.output_file).read_text()
    snippet = compact_output(output, args.max_output)
    record_row(
        db_path=args.db,
        task_id=args.task_id,
        phase=args.phase,
        check_name=args.check_name,
        tool=args.tool,
        command=args.command,
        exit_code=args.exit_code,
        passed=args.passed,
        output_snippet=snippet,
    )
    return 0


def command_run(args: argparse.Namespace) -> int:
    completed = subprocess.run(
        args.command,
        shell=True,
        executable=args.shell,
        cwd=args.cwd,
        text=True,
        capture_output=True,
    )

    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)

    combined_output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    record_row(
        db_path=args.db,
        task_id=args.task_id,
        phase=args.phase,
        check_name=args.check_name,
        tool=args.tool,
        command=args.command,
        exit_code=completed.returncode,
        passed=1 if completed.returncode == 0 else 0,
        output_snippet=compact_output(combined_output, args.max_output),
    )
    return completed.returncode


def command_count(args: argparse.Namespace) -> int:
    print(fetch_count(args.db, args.task_id, args.phase, args.passed_only))
    return 0


def command_bundle(args: argparse.Namespace) -> int:
    baseline_rows = fetch_rows(args.db, args.task_id, "baseline")
    after_rows = fetch_rows(args.db, args.task_id, "after")
    review_rows = fetch_rows(args.db, args.task_id, "review")
    regressions = fetch_regressions(args.db, args.task_id)

    if args.format == "json":
        payload = {
            "task_id": args.task_id,
            "baseline": [dict(row) for row in baseline_rows],
            "after": [dict(row) for row in after_rows],
            "review": [dict(row) for row in review_rows],
            "regressions": [dict(row) for row in regressions],
        }
        print(json.dumps(payload, indent=2))
        return 0

    sections = [
        render_phase_table("Baseline (before changes)", baseline_rows),
        render_phase_table("Verification (after changes)", after_rows),
        render_regressions(regressions),
        render_review_table(review_rows),
    ]
    print("\n\n".join(sections))
    return 0


def command_regressions(args: argparse.Namespace) -> int:
    regressions = fetch_regressions(args.db, args.task_id)
    if args.format == "json":
        print(json.dumps([dict(row) for row in regressions], indent=2))
        return 0

    if not regressions:
        print("None detected.")
        return 0

    for row in regressions:
        detail = markdown_escape(row["output_snippet"], limit=180)
        suffix = f": {detail}" if detail else ""
        print(f"{row['check_name']}{suffix}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Anvil SQLite ledger helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize the ledger database")
    init_parser.add_argument("--db", type=Path, default=default_db_path())
    init_parser.set_defaults(func=command_init)

    task_id_parser = subparsers.add_parser("task-id", help="Generate a task slug")
    task_id_parser.add_argument("--text", required=True)
    task_id_parser.set_defaults(func=command_task_id)

    record_parser = subparsers.add_parser("record", help="Insert a ledger row")
    record_parser.add_argument("--db", type=Path, default=default_db_path())
    record_parser.add_argument("--task-id", required=True)
    record_parser.add_argument("--phase", choices=VALID_PHASES, required=True)
    record_parser.add_argument("--check-name", required=True)
    record_parser.add_argument("--tool", required=True)
    record_parser.add_argument("--command")
    record_parser.add_argument("--exit-code", type=int)
    record_parser.add_argument("--passed", type=int, choices=(0, 1), required=True)
    record_parser.add_argument("--output")
    record_parser.add_argument("--output-file")
    record_parser.add_argument("--max-output", type=int, default=DEFAULT_MAX_OUTPUT)
    record_parser.set_defaults(func=command_record)

    run_parser = subparsers.add_parser("run", help="Run a command and record the result")
    run_parser.add_argument("--db", type=Path, default=default_db_path())
    run_parser.add_argument("--task-id", required=True)
    run_parser.add_argument("--phase", choices=VALID_PHASES, required=True)
    run_parser.add_argument("--check-name", required=True)
    run_parser.add_argument("--command", required=True)
    run_parser.add_argument("--tool", default="bash")
    run_parser.add_argument("--shell", default=DEFAULT_SHELL)
    run_parser.add_argument("--cwd", default=".")
    run_parser.add_argument("--max-output", type=int, default=DEFAULT_MAX_OUTPUT)
    run_parser.set_defaults(func=command_run)

    count_parser = subparsers.add_parser("count", help="Count rows for a task and phase")
    count_parser.add_argument("--db", type=Path, default=default_db_path())
    count_parser.add_argument("--task-id", required=True)
    count_parser.add_argument("--phase", choices=VALID_PHASES)
    count_parser.add_argument("--passed-only", action="store_true")
    count_parser.set_defaults(func=command_count)

    bundle_parser = subparsers.add_parser("bundle", help="Render the evidence bundle")
    bundle_parser.add_argument("--db", type=Path, default=default_db_path())
    bundle_parser.add_argument("--task-id", required=True)
    bundle_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    bundle_parser.set_defaults(func=command_bundle)

    regressions_parser = subparsers.add_parser("regressions", help="Show regressions")
    regressions_parser.add_argument("--db", type=Path, default=default_db_path())
    regressions_parser.add_argument("--task-id", required=True)
    regressions_parser.add_argument("--format", choices=("text", "json"), default="text")
    regressions_parser.set_defaults(func=command_regressions)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
