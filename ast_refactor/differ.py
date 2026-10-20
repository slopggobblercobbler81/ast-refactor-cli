"""Diff generation and syntax colorization."""

import difflib
from typing import List

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"


def generate_diff(
    original: str,
    modified: str,
    file_path: str = "file",
    color: bool = False,
) -> str:
    """Generate unified diff between original and modified text."""
    if original == modified:
        return ""

    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    )

    diff_lines: List[str] = []
    for line in diff:
        clean_line = line.rstrip("\r\n")
        if not color:
            diff_lines.append(clean_line)
            continue

        if clean_line.startswith("---") or clean_line.startswith("+++"):
            diff_lines.append(f"{BOLD}{clean_line}{RESET}")
        elif clean_line.startswith("@@"):
            diff_lines.append(f"{CYAN}{clean_line}{RESET}")
        elif clean_line.startswith("+"):
            diff_lines.append(f"{GREEN}{clean_line}{RESET}")
        elif clean_line.startswith("-"):
            diff_lines.append(f"{RED}{clean_line}{RESET}")
        else:
            diff_lines.append(clean_line)

    return "\n".join(diff_lines)
