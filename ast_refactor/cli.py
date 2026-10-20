"""Command-line interface for ast-refactor-cli."""

import argparse
import sys
from typing import List, Optional

from ast_refactor import __version__
from ast_refactor.engine import RefactorEngine


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ast-refactor",
        description="Safe AST-based symbol renaming, automated function extraction, and syntax modernization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color in diff output",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. RENAME subcommand
    rename_parser = subparsers.add_parser(
        "rename",
        help="Safely rename an identifier using AST analysis",
    )
    rename_parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files or directories to process (default: current directory)",
    )
    rename_parser.add_argument(
        "--from",
        dest="old_name",
        required=True,
        help="Current symbol name to rename",
    )
    rename_parser.add_argument(
        "--to",
        dest="new_name",
        required=True,
        help="New symbol name",
    )
    rename_parser.add_argument(
        "--scope",
        default=None,
        help="Limit renaming to a specific function or class name",
    )
    rename_parser.add_argument(
        "--rename-attributes",
        action="store_true",
        help="Also rename matching object attributes and methods",
    )
    rename_parser.add_argument(
        "-w",
        "--write",
        "--in-place",
        dest="in_place",
        action="store_true",
        help="Apply changes to disk in-place",
    )
    rename_parser.add_argument(
        "--diff",
        action="store_true",
        default=True,
        help="Show unified diff of changes (default: True)",
    )
    rename_parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with returncode 1 if any occurrences are found (for CI)",
    )

    # 2. EXTRACT subcommand
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract a block of statements into a new helper function",
    )
    extract_parser.add_argument(
        "file",
        help="Target source file to extract from",
    )
    extract_parser.add_argument(
        "--lines",
        required=True,
        help="Line range to extract formatted as START-END (e.g., 10-18)",
    )
    extract_parser.add_argument(
        "--name",
        required=True,
        help="Name for the newly created helper function",
    )
    extract_parser.add_argument(
        "-w",
        "--write",
        "--in-place",
        dest="in_place",
        action="store_true",
        help="Apply changes to disk in-place",
    )
    extract_parser.add_argument(
        "--diff",
        action="store_true",
        default=True,
        help="Show unified diff of changes",
    )

    # 3. MODERNIZE subcommand
    modernize_parser = subparsers.add_parser(
        "modernize",
        help="Automated syntax modernization for legacy idioms",
    )
    modernize_parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files or directories to modernize (default: current directory)",
    )
    modernize_parser.add_argument(
        "--rules",
        default=None,
        help="Comma-separated modernization rules to apply",
    )
    modernize_parser.add_argument(
        "-w",
        "--write",
        "--in-place",
        dest="in_place",
        action="store_true",
        help="Apply changes to disk in-place",
    )
    modernize_parser.add_argument(
        "--diff",
        action="store_true",
        default=True,
        help="Show unified diff of changes",
    )
    modernize_parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with returncode 1 if any modernizations would be applied",
    )

    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    parsed = parse_args(args)
    engine = RefactorEngine(color_diff=not parsed.no_color)

    if parsed.command == "rename":
        summary = engine.rename_symbol(
            paths=parsed.paths,
            old_name=parsed.old_name,
            new_name=parsed.new_name,
            scope=parsed.scope,
            rename_attributes=parsed.rename_attributes,
            in_place=parsed.in_place,
        )

        for res in summary.results:
            if res.has_changed and parsed.diff:
                print(res.diff)
            elif res.error:
                print(f"Error in {res.file_path}: {res.error}", file=sys.stderr)

        mode_str = "Applied" if parsed.in_place else "Proposed"
        print(
            f"{mode_str} {summary.total_changes} rename(s) across {summary.modified_files}/{summary.total_files} file(s)."
        )

        if parsed.check and summary.total_changes > 0:
            return 1
        return 0

    elif parsed.command == "extract":
        try:
            start_str, end_str = parsed.lines.split("-")
            start_line = int(start_str.strip())
            end_line = int(end_str.strip())
        except ValueError:
            print("Error: --lines must be formatted as START-END (e.g. 10-18)", file=sys.stderr)
            return 1

        res = engine.extract_function(
            file_path=parsed.file,
            start_line=start_line,
            end_line=end_line,
            new_function_name=parsed.name,
            in_place=parsed.in_place,
        )

        if res.error:
            print(f"Extraction error: {res.error}", file=sys.stderr)
            return 1

        if res.has_changed and parsed.diff:
            print(res.diff)

        mode_str = "Applied" if parsed.in_place else "Proposed"
        params = ", ".join(res.input_parameters) if res.input_parameters else "none"
        returns = ", ".join(res.output_variables) if res.output_variables else "none"
        print(f"{mode_str} extraction of '{parsed.name}' (params: {params}, returns: {returns}).")
        return 0

    elif parsed.command == "modernize":
        rules_set = None
        if parsed.rules:
            rules_set = {r.strip() for r in parsed.rules.split(",") if r.strip()}

        summary = engine.modernize_syntax(
            paths=parsed.paths,
            rules=rules_set,
            in_place=parsed.in_place,
        )

        for res in summary.results:
            if res.has_changed and parsed.diff:
                print(res.diff)
            elif res.error:
                print(f"Error in {res.file_path}: {res.error}", file=sys.stderr)

        mode_str = "Applied" if parsed.in_place else "Proposed"
        print(
            f"{mode_str} {summary.total_changes} modernization(s) across {summary.modified_files}/{summary.total_files} file(s)."
        )

        if parsed.check and summary.total_changes > 0:
            return 1
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
