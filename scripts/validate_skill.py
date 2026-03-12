#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_SKILL_NAME_LENGTH = 64
ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata", "version"}


def extract_frontmatter(content: str) -> str:
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", content, re.DOTALL)
    if not match:
        raise ValueError("Invalid frontmatter format")
    return match.group(1)


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_top_level_properties(frontmatter: str) -> dict[str, str]:
    properties: dict[str, str] = {}
    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():
            continue
        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line: {line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not re.match(r"^[A-Za-z0-9_-]+$", key):
            raise ValueError(f"Invalid frontmatter key: {key}")
        properties[key] = strip_quotes(raw_value)
    return properties


def validate_skill(skill_path: Path) -> tuple[bool, str]:
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    try:
        frontmatter = extract_frontmatter(content)
        properties = parse_top_level_properties(frontmatter)
    except ValueError as exc:
        return False, str(exc)

    unexpected_keys = set(properties) - ALLOWED_PROPERTIES
    if unexpected_keys:
        allowed = ", ".join(sorted(ALLOWED_PROPERTIES))
        unexpected = ", ".join(sorted(unexpected_keys))
        return (
            False,
            f"Unexpected key(s) in SKILL.md frontmatter: {unexpected}. Allowed properties are: {allowed}",
        )

    if "name" not in properties:
        return False, "Missing 'name' in frontmatter"
    if "description" not in properties:
        return False, "Missing 'description' in frontmatter"

    name = properties["name"].strip()
    if not name:
        return False, "Name must not be empty"
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' should be hyphen-case (lowercase letters, digits, and hyphens only)"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > MAX_SKILL_NAME_LENGTH:
        return False, f"Name is too long ({len(name)} characters). Maximum is {MAX_SKILL_NAME_LENGTH} characters."

    description = properties["description"].strip()
    if not description:
        return False, "Description must not be empty"
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > 1024:
        return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    return True, "Skill is valid!"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Codex skill without external dependencies")
    parser.add_argument("skill_directory")
    args = parser.parse_args()

    valid, message = validate_skill(Path(args.skill_directory))
    print(message)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
